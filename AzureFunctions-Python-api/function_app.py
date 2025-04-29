"""
Audio Sales Analyzer API
Azure Functions アプリケーションのエントリーポイント
"""

import azure.functions as func
import logging
import json
from typing import Optional
from datetime import datetime
from azure.functions import AuthLevel, FunctionApp

# モジュール構造からのインポート
from src.auth import login, register, get_user_by_id
from src.meetings import get_meetings, get_members_meetings, save_basic_info, get_basic_info
# 削除する関数のインポートをコメントアウト: save_meeting, update_recording_from_blob

# Azure Functions アプリケーションの初期化
app = FunctionApp(http_auth_level=AuthLevel.ANONYMOUS)

# ヘルスチェックエンドポイント
@app.function_name(name="HealthCheck")
@app.route(route="health", methods=["GET", "OPTIONS"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """APIサーバーの稼働状態を確認するためのヘルスチェックエンドポイント"""
    logging.info("Health check endpoint called")
    
    if req.method == "OPTIONS":
        # CORS プリフライトリクエスト処理
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        return func.HttpResponse(status_code=204, headers=headers)
    
    # ヘルスチェックレスポンス
    headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
    return func.HttpResponse(
        body='{"status":"ok","message":"API server is running"}',
        status_code=200,
        headers=headers
    )

#
# 認証関連のエンドポイント
#

# テスト用ユーザー登録エンドポイント
@app.function_name(name="RegisterTest")
@app.route(route="register/test", methods=["GET", "POST", "OPTIONS"])
@app.generic_output_binding(
    arg_name="users",
    type="sql",
    CommandText="[dbo].[Users]",
    ConnectionStringSetting="SqlConnectionString"
)
def register_test(req: func.HttpRequest, users: func.Out[func.SqlRow]) -> func.HttpResponse:
    return register(req, users)

# ログインエンドポイント
@app.function_name(name="Login")
@app.route(route="users/login", methods=["POST", "OPTIONS"])
@app.generic_input_binding(
    arg_name="usersQuery", 
    type="sql",
    CommandText="SELECT * FROM dbo.Users",
    ConnectionStringSetting="SqlConnectionString"
)
def login_func(req: func.HttpRequest, usersQuery: func.SqlRowList) -> func.HttpResponse:
    return login(req, usersQuery)

# ユーザー情報取得エンドポイント
@app.function_name(name="GetUserById")
@app.route(route="users/{user_id}", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="usersQuery", 
    type="sql",
    CommandText="SELECT user_id, user_name, email, is_manager, manager_name, is_active, account_status FROM dbo.Users",
    ConnectionStringSetting="SqlConnectionString"
)
def get_user_by_id_func(req: func.HttpRequest, usersQuery: func.SqlRowList) -> func.HttpResponse:
    return get_user_by_id(req, usersQuery)

#
# 会議関連のエンドポイント
#

# save_meeting_funcエンドポイントを削除（Meetingsテーブルへの挿入機能）

# 基本情報保存エンドポイント
@app.function_name(name="SaveBasicInfo")
@app.route(route="basicinfo", methods=["POST", "OPTIONS"])
@app.generic_input_binding(
    arg_name="lastBasicInfo", 
    type="sql", 
    CommandText="SELECT TOP 1 meeting_id FROM dbo.BasicInfo ORDER BY meeting_id DESC", 
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_output_binding(
    arg_name="basicInfo", 
    type="sql", 
    CommandText="dbo.BasicInfo", 
    ConnectionStringSetting="SqlConnectionString"
)
def save_basic_info_func(req: func.HttpRequest, basicInfo: func.Out[func.SqlRow], lastBasicInfo: func.SqlRowList) -> func.HttpResponse:
    return save_basic_info(req, basicInfo, lastBasicInfo)

# 会議一覧取得エンドポイント
@app.function_name(name="GetMeetings")
@app.route(route="meetings", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="meetingsQuery", 
    type="sql", 
    CommandText="SELECT meeting_id, user_id, client_contact_name, client_company_name, meeting_datetime, duration_seconds, status, transcript_text, file_name, file_size, error_message FROM dbo.Meetings", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_meetings_func(req: func.HttpRequest, meetingsQuery: func.SqlRowList) -> func.HttpResponse:
    return get_meetings(req, meetingsQuery)

# 録音情報更新エンドポイント
@app.function_name(name="UpdateRecording")
@app.route(route="meetings/update-recording", methods=["POST", "OPTIONS"])
@app.generic_input_binding(
    arg_name="meetingQuery", 
    type="sql", 
    CommandText="SELECT meeting_id, user_id, client_contact_name, client_company_name, meeting_datetime, duration_seconds, status, transcript_text, file_name, file_size, error_message FROM dbo.Meetings", 
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_output_binding(
    arg_name="meetingOut", 
    type="sql", 
    CommandText="dbo.Meetings", 
    ConnectionStringSetting="SqlConnectionString"
)
def update_recording_func(req: func.HttpRequest, meetingOut: func.Out[func.SqlRow], meetingQuery: func.SqlRowList) -> func.HttpResponse:
    from src.meetings.meeting_handlers import update_recording
    return update_recording(req, meetingOut, meetingQuery)

# メンバー会議一覧取得エンドポイント
@app.function_name(name="GetMembersMeetings")
@app.route(route="members-meetings", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="usersQuery", 
    type="sql", 
    CommandText="SELECT user_id, user_name, manager_name, account_status FROM dbo.Users", 
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_input_binding(
    arg_name="meetingsQuery", 
    type="sql", 
    CommandText="SELECT m.meeting_id, m.user_id, m.client_contact_name, m.client_company_name, m.meeting_datetime, m.duration_seconds, m.status, m.transcript_text, m.file_name, m.file_size, m.error_message, u.user_name, u.account_status FROM dbo.Meetings m JOIN dbo.Users u ON m.user_id = u.user_id", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_members_meetings_func(req: func.HttpRequest, usersQuery: func.SqlRowList, meetingsQuery: func.SqlRowList) -> func.HttpResponse:
    return get_members_meetings(req, usersQuery, meetingsQuery)

# update_meeting_with_recording_funcエンドポイントを削除（録音情報更新機能）

# 基本情報取得エンドポイント
@app.function_name(name="GetBasicInfo")
@app.route(route="basicinfo/{meeting_id}", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="basicInfoQuery", 
    type="sql", 
    CommandText="SELECT * FROM dbo.BasicInfo", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_basic_info_func(req: func.HttpRequest, basicInfoQuery: func.SqlRowList) -> func.HttpResponse:
    return get_basic_info(req, basicInfoQuery)

# 基本情報検索エンドポイント
@app.function_name(name="SearchBasicInfo")
@app.route(route="basicinfo/search", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="basicInfoQuery", 
    type="sql", 
    CommandText="SELECT * FROM dbo.BasicInfo", 
    ConnectionStringSetting="SqlConnectionString"
)
def search_basic_info_func(req: func.HttpRequest, basicInfoQuery: func.SqlRowList) -> func.HttpResponse:
    return get_basic_info(req, basicInfoQuery, search_mode=True)

#
# フィードバック関連のエンドポイント（AzureFunctions-Python-Feedbackから移行）
#

# 会話セグメント取得API
@app.function_name(name="GetConversationSegments")
@app.route(route="api/conversation/segments/{meeting_id}", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="segmentsQuery", 
    type="sql", 
    CommandText="SELECT s.segment_id, s.user_id, s.speaker_id, s.meeting_id, s.content, s.file_name, s.file_path, s.file_size, s.duration_seconds, s.status, s.inserted_datetime, s.updated_datetime, s.start_time, s.end_time, sp.speaker_name, sp.speaker_role FROM dbo.ConversationSegments s LEFT JOIN dbo.Speakers sp ON s.speaker_id = sp.speaker_id WHERE s.deleted_datetime IS NULL", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_conversation_segments(req: func.HttpRequest, segmentsQuery: func.SqlRowList) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            # CORS プリフライトリクエスト処理
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
            
        meeting_id = req.route_params.get('meeting_id')
        
        # データベースから会話セグメントを取得
        segments = []
        for row in segmentsQuery:
            if int(row['meeting_id']) == int(meeting_id):
                # 日付時刻の適切な変換
                inserted_datetime = row['inserted_datetime']
                updated_datetime = row['updated_datetime']
                
                # datetime型の場合のみisoformat()を適用
                if hasattr(inserted_datetime, 'isoformat'):
                    inserted_datetime = inserted_datetime.isoformat()
                elif inserted_datetime is not None and not isinstance(inserted_datetime, str):
                    inserted_datetime = str(inserted_datetime)
                
                if hasattr(updated_datetime, 'isoformat'):
                    updated_datetime = updated_datetime.isoformat()
                elif updated_datetime is not None and not isinstance(updated_datetime, str):
                    updated_datetime = str(updated_datetime)
                
                segments.append({
                    "segment_id": row['segment_id'],
                    "user_id": row['user_id'],
                    "speaker_id": row['speaker_id'],
                    "meeting_id": row['meeting_id'],
                    "content": row['content'],
                    "file_name": row['file_name'],
                    "file_path": row['file_path'],
                    "file_size": row['file_size'],
                    "duration_seconds": row['duration_seconds'],
                    "status": row['status'],
                    "inserted_datetime": inserted_datetime,
                    "updated_datetime": updated_datetime,
                    "start_time": row['start_time'],
                    "end_time": row['end_time'],
                    "speaker_name": row['speaker_name'],
                    "speaker_role": row['speaker_role']
                })
        
        response = {
            "success": True,
            "message": f"会話セグメントを取得しました（meeting_id: {meeting_id}）",
            "segments": segments
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )
    except Exception as e:
        logging.error(f"セグメント取得中にエラーが発生しました: {str(e)}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"success": False, "message": f"エラー: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# コメント取得API
@app.function_name(name="GetComments")
@app.route(route="api/comments/{segment_id}", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="commentsQuery", 
    type="sql", 
    CommandText="SELECT c.comment_id, c.segment_id, c.meeting_id, c.user_id, c.content, c.inserted_datetime, c.updated_datetime, u.user_name FROM dbo.Comments c JOIN dbo.Users u ON c.user_id = u.user_id WHERE c.deleted_datetime IS NULL", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_segment_comments(req: func.HttpRequest, commentsQuery: func.SqlRowList) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            # CORS プリフライトリクエスト処理
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
            
        segment_id = req.route_params.get('segment_id')
        
        # データベースからコメントを取得
        comments = []
        for row in commentsQuery:
            if int(row['segment_id']) == int(segment_id):
                # 既読情報（一時的に空配列を返す）
                readers = []
                
                # 日付時刻の適切な変換
                inserted_datetime = row['inserted_datetime']
                updated_datetime = row['updated_datetime']
                
                # datetime型の場合のみisoformat()を適用
                if hasattr(inserted_datetime, 'isoformat'):
                    inserted_datetime = inserted_datetime.isoformat()
                elif inserted_datetime is not None and not isinstance(inserted_datetime, str):
                    inserted_datetime = str(inserted_datetime)
                
                if hasattr(updated_datetime, 'isoformat'):
                    updated_datetime = updated_datetime.isoformat()
                elif updated_datetime is not None and not isinstance(updated_datetime, str):
                    updated_datetime = str(updated_datetime)
                
                comments.append({
                    "comment_id": row['comment_id'],
                    "segment_id": row['segment_id'],
                    "meeting_id": row['meeting_id'],
                    "user_id": row['user_id'],
                    "user_name": row['user_name'],
                    "content": row['content'],
                    "inserted_datetime": inserted_datetime,
                    "updated_datetime": updated_datetime,
                    "readers": readers
                })
        
        response = {
            "success": True,
            "message": f"コメントを取得しました（segment_id: {segment_id}）",
            "comments": comments
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False), 
            mimetype="application/json",
            status_code=200,
            headers=headers
        )
    except Exception as e:
        logging.error(f"コメント取得中にエラーが発生しました: {str(e)}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"success": False, "message": f"エラー: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# コメント追加API
@app.function_name(name="AddComment")
@app.route(route="api/comments", methods=["POST", "OPTIONS"])
@app.generic_input_binding(
    arg_name="lastCommentId", 
    type="sql", 
    CommandText="SELECT TOP 1 comment_id FROM dbo.Comments ORDER BY comment_id DESC", 
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_output_binding(
    arg_name="commentOut", 
    type="sql", 
    CommandText="dbo.Comments", 
    ConnectionStringSetting="SqlConnectionString"
)
def create_comment(req: func.HttpRequest, commentOut: func.Out[func.SqlRow], lastCommentId: func.SqlRowList) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            # CORS プリフライトリクエスト処理
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
            
        req_body = req.get_json()
        
        # リクエストのバリデーション
        segment_id = req_body.get('segment_id')
        meeting_id = req_body.get('meeting_id')
        user_id = req_body.get('user_id')
        content = req_body.get('content')
        
        if not all([segment_id, meeting_id, user_id, content]):
            headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
            return func.HttpResponse(
                json.dumps({"success": False, "message": "必須パラメータが不足しています"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400,
                headers=headers
            )
        
        # 新しいコメントIDを生成
        new_comment_id = 1
        for row in lastCommentId:
            new_comment_id = int(row['comment_id']) + 1
            break
        
        # 現在の日時をSQL Serverに適した形式で文字列化
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # コメントをデータベースに挿入
        comment_row = func.SqlRow()
        comment_row["comment_id"] = new_comment_id
        comment_row["segment_id"] = segment_id
        comment_row["meeting_id"] = meeting_id
        comment_row["user_id"] = user_id
        comment_row["content"] = content
        comment_row["inserted_datetime"] = now
        comment_row["updated_datetime"] = now
        
        commentOut.set(comment_row)
        
        response = {
            "success": True,
            "message": "コメントが追加されました",
            "comment_id": new_comment_id
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=201,
            headers=headers
        )
    except Exception as e:
        logging.error(f"コメント追加中にエラーが発生しました: {str(e)}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"success": False, "message": f"エラー: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# コメント既読状態更新API - 一時的に空レスポンスを返すように修正
@app.function_name(name="MarkCommentAsRead")
@app.route(route="api/comments/read", methods=["POST", "OPTIONS"])
def mark_comment_as_read(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            # CORS プリフライトリクエスト処理
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
        
        # 正常なレスポンスを返す（実際の処理は行わない）
        response = {
            "success": True,
            "message": "既読機能は一時的に無効化されています"
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )
    except Exception as e:
        logging.error(f"コメント既読更新中にエラーが発生しました: {str(e)}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"success": False, "message": f"エラー: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# 最新コメント取得API
@app.function_name(name="GetLatestComments")
@app.route(route="api/comments-latest", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="commentsQuery", 
    type="sql", 
    CommandText="SELECT TOP 20 c.comment_id, c.segment_id, c.meeting_id, c.user_id, c.content, c.inserted_datetime, c.updated_datetime, u.user_name, m.client_company_name, m.client_contact_name FROM dbo.Comments c JOIN dbo.Users u ON c.user_id = u.user_id JOIN dbo.Meetings m ON c.meeting_id = m.meeting_id WHERE c.deleted_datetime IS NULL ORDER BY c.inserted_datetime DESC", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_latest_comments(req: func.HttpRequest, commentsQuery: func.SqlRowList) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            # CORS プリフライトリクエスト処理
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
            
        # クエリパラメータからユーザーIDを取得
        user_id = 1  # デフォルト値
        limit = 5    # デフォルト値
        
        try:
            # userId パラメータのチェック
            if 'userId' in req.params:
                user_id_str = req.params.get('userId')
                logging.info(f"受信したuserIdパラメータ: {user_id_str}")
                # 数値であることを確認
                if user_id_str and user_id_str.isdigit():
                    user_id = int(user_id_str)
            
            # limit パラメータのチェック
            if 'limit' in req.params:
                limit_str = req.params.get('limit')
                if limit_str and limit_str.isdigit():
                    limit = int(limit_str)
            
            logging.info(f"処理するパラメータ: userId={user_id}, limit={limit}")
        
        except Exception as e:
            logging.warning(f"パラメータ処理中にエラーが発生しました: {e}")
            logging.warning(f"受信したパラメータ: userId={req.params.get('userId')}, limit={req.params.get('limit')}")
            logging.warning("デフォルト値を使用します: userId=1, limit=5")
        
        # データベースから最新コメントを取得
        comments = []
        count = 0
        
        for row in commentsQuery:
            if count >= limit:
                break
                
            # 既読情報（一時的にすべて既読とする）
            is_read = True
            
            # 日付時刻の適切な変換
            inserted_datetime = row['inserted_datetime']
            updated_datetime = row['updated_datetime']
            
            # datetime型の場合のみisoformat()を適用
            if hasattr(inserted_datetime, 'isoformat'):
                inserted_datetime = inserted_datetime.isoformat()
            elif inserted_datetime is not None and not isinstance(inserted_datetime, str):
                inserted_datetime = str(inserted_datetime)
            
            if hasattr(updated_datetime, 'isoformat'):
                updated_datetime = updated_datetime.isoformat()
            elif updated_datetime is not None and not isinstance(updated_datetime, str):
                updated_datetime = str(updated_datetime)
            
            comments.append({
                "comment_id": row['comment_id'],
                "segment_id": row['segment_id'],
                "meeting_id": row['meeting_id'],
                "user_id": row['user_id'],
                "user_name": row['user_name'],
                "content": row['content'],
                "inserted_datetime": inserted_datetime,
                "updated_datetime": updated_datetime,
                "client_company_name": row['client_company_name'],
                "client_contact_name": row['client_contact_name'],
                "isRead": is_read
            })
            count += 1
        
        response = {
            "success": True,
            "message": f"最新コメントを取得しました（userId: {user_id}, limit: {limit}）",
            "comments": comments
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False), 
            mimetype="application/json",
            status_code=200,
            headers=headers
        )
    except Exception as e:
        logging.error(f"最新コメント取得中にエラーが発生しました: {str(e)}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"success": False, "message": f"エラー: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )
