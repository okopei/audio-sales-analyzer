import azure.functions as func
import logging
import uuid
import json
import pyodbc
import os
import bcrypt
from datetime import datetime, UTC
import traceback
from azure.functions import AuthLevel, FunctionApp
import time

app = FunctionApp(http_auth_level=AuthLevel.ANONYMOUS)

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