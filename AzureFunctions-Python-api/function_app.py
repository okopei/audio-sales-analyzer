import azure.functions as func
import logging
import uuid
import json
import os
import bcrypt
from datetime import datetime, UTC
import traceback
from azure.functions import AuthLevel, FunctionApp
import time
from azure.identity import DefaultAzureCredential
from azure.data.tables import TableServiceClient

# save_meeting_handlerをインポート
from src.meetings.handlers import save_meeting_handler

app = FunctionApp(http_auth_level=AuthLevel.ANONYMOUS)

# データベース接続文字列を環境変数から取得
def get_db_connection():
    connection_string = os.environ.get('SqlConnectionString')
    if not connection_string:
        raise ValueError("SqlConnectionString environment variable is not set")
    return pyodbc.connect(connection_string)

@app.function_name(name="HttpTrigger1")
@app.route(route="http_trigger")
@app.generic_output_binding(arg_name="toDoItems", type="sql", CommandText="dbo.ToDo", ConnectionStringSetting="SqlConnectionString")
def http_trigger(req: func.HttpRequest, toDoItems: func.Out[func.SqlRow]) -> func.HttpResponse:
    logging.info('HTTP trigger function processed a request.')

    try:
        # JSONデータを取得
        req_body = req.get_json()
        title = req_body.get('title')
        url = req_body.get('url')
    except ValueError:
        return func.HttpResponse(
            "Invalid JSON data",
            status_code=400
        )

    if title and url:
        # SQLバインディングを使用してデータを挿入
        toDoItems.set(func.SqlRow({
            "Id": str(uuid.uuid4()),
            "order": None,
            "title": title,
            "url": url,
            "completed": False
        }))
        return func.HttpResponse(
            f"ToDo item '{title}' created successfully.",
            status_code=201
        )
    else:
        return func.HttpResponse(
            "Please provide 'title' and 'url' in the JSON body",
            status_code=400
        )

# マネージャー確認用のヘルパー関数
def check_manager(manager_name: str) -> bool:
    return True  # 一時的に常にTrueを返す

# 新しいテスト用エンドポイント
@app.function_name(name="RegisterTest")
@app.route(route="register/test", methods=["GET", "POST", "OPTIONS"])
@app.generic_output_binding(
    arg_name="users",
    type="sql",
    CommandText="[dbo].[Users]",
    ConnectionStringSetting="SqlConnectionString"
)
def register_test(req: func.HttpRequest, users: func.Out[func.SqlRow]) -> func.HttpResponse:
    logging.info('Register test function started')
    
    # CORS headers
    headers = {
        # TODO: 本番環境デプロイ時に環境変数に変更
        # "Access-Control-Allow-Origin": os.environ["ALLOWED_ORIGINS"],
        "Access-Control-Allow-Origin": "http://localhost:3000",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    try:
        req_body = req.get_json()
        logging.info(f'Received registration data')

        # メールアドレスの重複チェック
        @app.generic_output_binding(
            arg_name="email_check",
            type="sql",
            CommandText="SELECT COUNT(*) as count FROM [dbo].[Users] WHERE email = @email",
            Parameters="@email={email}",
            ConnectionStringSetting="SqlConnectionString"
        )
        def check_email_exists(email: str) -> bool:
            result = email_check.get()
            return result[0]['count'] > 0

        if check_email_exists(req_body['email']):
            return func.HttpResponse(
                body=json.dumps({
                    "error": "このメールアドレスは既に登録されています"
                }),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )

        # 現在時刻
        now = datetime.now(UTC)

        # パスワードのハッシュ化
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(
            req_body['password'].encode('utf-8'), 
            salt
        )

        # 基本パラメータ
        params = {
            "user_name": req_body['user_name'],
            "email": req_body['email'],
            "password_hash": password_hash.decode('utf-8'),
            "salt": salt.decode('utf-8'),
            "is_active": True,
            "account_status": 'active',
            "inserted_datetime": now.strftime('%Y-%m-%d %H:%M:%S'),
            "updated_datetime": now.strftime('%Y-%m-%d %H:%M:%S'),
            "login_attempt_count": 0
        }

        # マネージャー/メンバー固有の設定
        if req_body['role'] == 'member':
            manager_name = req_body.get('manager_name')
            if not manager_name:
                return func.HttpResponse(
                    body=json.dumps({
                        "error": "メンバー登録にはマネージャー名が必要です"
                    }),
                    status_code=400,
                    mimetype="application/json",
                    headers=headers
                )

            # マネージャーの存在確認
            manager_exists = check_manager(manager_name)
            if not manager_exists:
                return func.HttpResponse(
                    body=json.dumps({
                        "error": "指定されたマネージャーが存在しません。有効なマネージャーを指定してください。"
                    }),
                    status_code=400,
                    mimetype="application/json",
                    headers=headers
                )
            # メンバー用パラメータを追加
            params.update({
                "is_manager": False,
                "manager_name": manager_name
            })
        else:
            # マネージャー用パラメータを追加
            params.update({
                "is_manager": True,
                "manager_name": None
            })

        # SQLクエリにパラメータを渡す
        users.set(func.SqlRow(params))
        
        logging.info(f"User {req_body['email']} registered successfully")

        return func.HttpResponse(
            body=json.dumps({
                "message": "ユーザー登録が完了しました",
                "user": {
                    "user_name": req_body['user_name'],
                    "email": req_body['email']
                }
            }),
            mimetype="application/json",
            headers=headers
        )

    except Exception as e:
        error_message = str(e)
        logging.error(f'Error in register test: {error_message}\n{traceback.format_exc()}')
        return func.HttpResponse(
            body=json.dumps({"error": error_message}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )

# save_meeting関数に必要なデコレータを追加
@app.function_name(name="SaveMeeting")
@app.route(route="meetings/save", methods=["POST", "OPTIONS"])
@app.generic_input_binding(
    arg_name="lastMeeting", 
    type="sql", 
    CommandText="SELECT TOP 1 meeting_id FROM dbo.Meetings ORDER BY meeting_id DESC", 
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_output_binding(
    arg_name="meetings", 
    type="sql", 
    CommandText="dbo.Meetings", 
    ConnectionStringSetting="SqlConnectionString"
)
def save_meeting(req: func.HttpRequest, meetings: func.Out[func.SqlRow], lastMeeting: func.SqlRowList) -> func.HttpResponse:
    return save_meeting_handler(req, meetings, lastMeeting)

# ユーザーハンドラーをインポート
from src.users.handlers import login_handler

# ログインエンドポイント
@app.function_name(name="Login")
@app.route(route="users/login", methods=["POST", "OPTIONS"])
@app.generic_input_binding(
    arg_name="usersQuery", 
    type="sql", 
    CommandText="SELECT * FROM dbo.Users", 
    ConnectionStringSetting="SqlConnectionString"
)
def login(req: func.HttpRequest, usersQuery: func.SqlRowList) -> func.HttpResponse:
    return login_handler(req, usersQuery)

@app.function_name(name="GetMeetings")
@app.route(route="meetings", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="meetingsQuery", 
    type="sql", 
    CommandText="SELECT meeting_id, user_id, title, meeting_datetime, duration_seconds, status, transcript_text, file_name, file_size, error_message FROM dbo.Meetings", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_meetings(req: func.HttpRequest, meetingsQuery: func.SqlRowList) -> func.HttpResponse:
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    try:
        user_id = req.params.get('user_id')
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )
        
        # デバッグ用に、全てのミーティングデータをログに出力
        meetings_list = list(meetingsQuery)
        logging.info(f"Total meetings retrieved from DB: {len(meetings_list)}")
        
        # ユーザーIDフィルタリング
        meetings = []
        for row in meetings_list:
            row_dict = dict(row)
            row_user_id = row_dict.get("user_id")
            
            # int型に変換して比較
            try:
                if int(row_user_id) == int(user_id):
                    meeting_datetime = row_dict.get("meeting_datetime")
                    
                    # meeting_datetimeの処理を修正
                    datetime_str = None
                    if meeting_datetime:
                        # datetimeオブジェクトかどうかを確認
                        if hasattr(meeting_datetime, 'isoformat'):
                            datetime_str = meeting_datetime.isoformat()
                        else:
                            # 既に文字列の場合はそのまま使用
                            datetime_str = str(meeting_datetime)
                    
                    meetings.append({
                        "meeting_id": row_dict.get("meeting_id"),
                        "user_id": row_user_id,
                        "title": row_dict.get("title"),
                        "meeting_datetime": datetime_str,
                        "duration_seconds": row_dict.get("duration_seconds"),
                        "status": row_dict.get("status"),
                        "transcript_text": row_dict.get("transcript_text"),
                        "file_name": row_dict.get("file_name"),
                        "file_size": row_dict.get("file_size"),
                        "error_message": row_dict.get("error_message")
                    })
            except (ValueError, TypeError) as ve:
                logging.error(f"Error converting user_id: {str(ve)}")
        
        # 最終的なミーティング数をログに出力
        logging.info(f"Filtered meetings count: {len(meetings)}")
        
        if meetings:
            return func.HttpResponse(
                json.dumps({"meetings": meetings}),
                mimetype="application/json",
                headers=headers
            )
        else:
            return func.HttpResponse(
                json.dumps({
                    "message": "No meetings found for the specified user",
                    "debug": {
                        "user_id_requested": user_id,
                        "total_records": len(meetings_list)
                    }
                }),
                mimetype="application/json",
                headers=headers
            )
    except Exception as e:
        logging.error(f"Error retrieving meetings: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )

@app.function_name(name="GetMembersMeetings")
@app.route(route="members-meetings", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="usersQuery", 
    type="sql", 
    CommandText="SELECT user_id, user_name, manager_name FROM dbo.Users", 
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_input_binding(
    arg_name="meetingsQuery", 
    type="sql", 
    CommandText="SELECT m.meeting_id, m.user_id, m.title, m.meeting_datetime, m.duration_seconds, m.status, m.transcript_text, m.file_name, m.file_size, m.error_message, u.user_name FROM dbo.Meetings m JOIN dbo.Users u ON m.user_id = u.user_id", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_members_meetings(req: func.HttpRequest, usersQuery: func.SqlRowList, meetingsQuery: func.SqlRowList) -> func.HttpResponse:
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=headers)

    try:
        manager_id = req.params.get('manager_id')
        logging.info(f"[DEBUG] Received manager_id: {manager_id}")
        
        if not manager_id:
            return func.HttpResponse(
                json.dumps({"error": "manager_id is required"}),
                status_code=400,
                mimetype="application/json",
                headers=headers
            )
        
        # マネージャー名を取得
        manager_name = None
        for user in usersQuery:
            if str(user.get("user_id")) == manager_id:
                manager_name = user.get("user_name")
                break
        
        logging.info(f"[DEBUG] Found manager_name: {manager_name}")
        
        if not manager_name:
            return func.HttpResponse(
                json.dumps({"error": "Manager not found"}),
                status_code=404,
                mimetype="application/json",
                headers=headers
            )
        
        # マネージャーが管理するチームメンバーのIDを取得
        team_member_ids = []
        for user in usersQuery:
            user_dict = dict(user)
            if user_dict.get("manager_name") == manager_name:
                user_id = str(user_dict.get("user_id"))
                team_member_ids.append(user_id)
                logging.info(f"[DEBUG] Found team member - user_id: {user_id}, user_name: {user_dict.get('user_name')}, manager_name: {user_dict.get('manager_name')}")
        
        logging.info(f"[DEBUG] Team member IDs: {team_member_ids}")
        
        # すべてのユーザーのmanager_name情報をログに出力
        logging.info("[DEBUG] All users manager_name info:")
        for user in usersQuery:
            user_dict = dict(user)
            logging.info(f"[DEBUG] user_id: {user_dict.get('user_id')}, user_name: {user_dict.get('user_name')}, manager_name: {user_dict.get('manager_name')}")
        
        # チームメンバーのミーティングを取得
        meetings = []
        meeting_count = 0
        for row in meetingsQuery:
            try:
                row_dict = dict(row)
                row_user_id = str(row_dict.get("user_id"))
                
                if row_user_id in team_member_ids:
                    meeting_datetime = row_dict.get("meeting_datetime")
                    
                    # meeting_datetimeの処理を修正
                    datetime_str = None
                    if meeting_datetime:
                        # datetimeオブジェクトかどうかを確認
                        if hasattr(meeting_datetime, 'isoformat'):
                            datetime_str = meeting_datetime.isoformat()
                        else:
                            # 既に文字列の場合はそのまま使用
                            datetime_str = str(meeting_datetime)
                    
                    meetings.append({
                        "meeting_id": row_dict.get("meeting_id"),
                        "user_id": row_dict.get("user_id"),
                        "user_name": row_dict.get("user_name"),
                        "title": row_dict.get("title"),
                        "meeting_datetime": datetime_str,
                        "duration_seconds": row_dict.get("duration_seconds"),
                        "status": row_dict.get("status"),
                        "transcript_text": row_dict.get("transcript_text"),
                        "file_name": row_dict.get("file_name"),
                        "file_size": row_dict.get("file_size"),
                        "error_message": row_dict.get("error_message")
                    })
                    meeting_count += 1
                    logging.info(f"[DEBUG] Found meeting for team member - meeting_id: {row_dict.get('meeting_id')}, user_id: {row_user_id}, title: {row_dict.get('title')}")
            except Exception as row_error:
                logging.error(f"Error processing row: {str(row_error)}")
        
        logging.info(f"[DEBUG] Total meetings found: {meeting_count}")
        
        if meetings:
            return func.HttpResponse(
                json.dumps({"meetings": meetings}),
                mimetype="application/json",
                headers=headers
            )
        else:
            logging.info(f"[DEBUG] No meetings found for team members with IDs: {team_member_ids}")
            return func.HttpResponse(
                json.dumps({"message": "No meetings found for the team members"}),
                mimetype="application/json",
                headers=headers
            )
    except Exception as e:
        logging.error(f"Error retrieving team meetings: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )
