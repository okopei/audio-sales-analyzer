import logging
import os  
import pyodbc
import traceback
import azure.functions as func
from azure.functions import FunctionApp
import json
from typing import Optional, Dict, List, Any
from azure.identity import DefaultAzureCredential, ClientSecretCredential
import struct
from urllib.parse import urlparse, parse_qs
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
import bcrypt
import uuid
import smtplib
from email.mime.text import MIMEText 


app = FunctionApp()

def build_cors_headers(methods: str = "GET, OPTIONS") -> dict:
    return {
        "Access-Control-Allow-Origin": "https://audio-sales-analyzer.vercel.app",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": methods,
        "Access-Control-Allow-Headers": "Content-Type",
    }

def get_db_connection():
    """
    ローカル：ClientSecretCredential（pyodbc）
    本番環境：Microsoft Entra ID（Managed Identity）を使用して Azure SQL Database に接続する。
    ODBC Driver 17 for SQL Server + Authentication=ActiveDirectoryMsi を使用。
    """
    try:
        logging.info("[DB接続] 開始")

        server = os.getenv("SQL_SERVER")
        database = os.getenv("SQL_DATABASE")

        if not server or not database:
            raise ValueError("SQL_SERVER または SQL_DATABASE の環境変数が設定されていません")

        env = os.getenv("AZURE_ENVIRONMENT", "local")  # "local" or "production"
        is_local = env.lower() != "production"

        if is_local:
            # 🔐 ローカル用：ClientSecretCredential + pyodbc + アクセストークン
            logging.info("[DB接続] ローカル環境（pyodbc + Entra認証トークン）")

            tenant_id = os.getenv("TENANT_ID")
            client_id = os.getenv("CLIENT_ID")
            client_secret = os.getenv("CLIENT_SECRET")

            if not all([tenant_id, client_id, client_secret]):
                raise ValueError("TENANT_ID, CLIENT_ID, CLIENT_SECRET が未設定です")

            credential = ClientSecretCredential(tenant_id, client_id, client_secret)
            token = credential.get_token("https://database.windows.net/.default")

            token_bytes = bytes(token.token, "utf-8")
            exptoken = b''.join(bytes((b, 0)) for b in token_bytes)
            access_token = struct.pack("=i", len(exptoken)) + exptoken

            conn_str = (
                f"Driver={{ODBC Driver 17 for SQL Server}};"
                f"Server=tcp:{server},1433;"
                f"Database={database};"
                "Encrypt=yes;TrustServerCertificate=no;"
                "Connection Timeout=30;"
            )

            conn = pyodbc.connect(conn_str, attrs_before={1256: access_token})
        else:
            # ☁️ 本番用：Managed Identity + pypyodbc + MSI認証
            logging.info("[DB接続] Azure 環境（pypyodbc + MSI）")

            conn_str = (
                f"Driver={{ODBC Driver 17 for SQL Server}};"
                f"Server=tcp:{server},1433;"
                f"Database={database};"
                "Authentication=ActiveDirectoryMsi;"
                "Encrypt=yes;TrustServerCertificate=no;"
            )
            conn = pyodbc.connect(conn_str, timeout=10)
        logging.info("[DB接続] 成功")
        return conn
    except Exception as e:
        logging.error("[DB接続] エラー発生")
        logging.exception("詳細:")
        raise

def log_trigger_error(event_type: str, table_name: str, record_id: int, additional_info: str):
    """
    TriggerLog テーブルにエラー情報を記録します。
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            insert_log_query = """
                INSERT INTO dbo.TriggerLog (
                    event_type, table_name, record_id, event_time, additional_info
                ) VALUES (?, ?, ?, GETDATE(), ?)
            """
            cursor.execute(insert_log_query, (
                event_type,
                table_name,
                record_id,
                additional_info[:1000]  # 長すぎる場合は切り捨て
            ))
            conn.commit()
            logging.info("⚠️ TriggerLog にエラー記録を挿入しました")
    except Exception as log_error:
        logging.error(f"🚨 TriggerLog への挿入に失敗: {log_error}")

def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    SQLクエリを実行し、結果を返します。
    
    Args:
        query (str): 実行するSQLクエリ
        params (Optional[Dict[str, Any]]): クエリパラメータ
        
    Returns:
        List[Dict[str, Any]]: クエリ結果のリスト
    """
    try:
        with get_db_connection() as conn:
            logging.info(f"クエリを実行: {query}")
            if params:
                logging.info(f"パラメータ: {params}")
            
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith("SELECT"):
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                results = [dict(zip(columns, row)) for row in rows]

                # datetime → 文字列化
                for row in results:
                    for key, value in row.items():
                        if hasattr(value, 'isoformat'):
                            row[key] = value.isoformat()

                return results
            else:
                conn.commit()
                return []
                
    except Exception as e:
        logging.error(f"クエリ実行エラー: {str(e)}")
        raise


@app.function_name(name="TestDbConnection")
@app.route(route="testdb", auth_level=func.AuthLevel.ANONYMOUS)
def test_db_connection(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logging.info("A: DB接続開始前")
        
        query = "SELECT * FROM [dbo].[Users] WHERE [user_id] = ?"
        result = execute_query(query, (27,))
        
        if result:
            result_str = "\n".join(str(row) for row in result)
            return func.HttpResponse(f"ユーザーデータ取得成功:\n{result_str}", status_code=200)
        else:
            return func.HttpResponse("ユーザーデータが見つかりません", status_code=404)

    except Exception as e:
        logging.error("C: DB接続失敗")
        logging.exception("接続エラー詳細:")
        log_trigger_error(
            event_type="error",
            table_name="System",
            record_id=-1,
            additional_info=f"[test_db_connection] {str(e)}"
        )
        return func.HttpResponse(
            f"接続失敗: {str(e)}\n{traceback.format_exc()}",
            status_code=500
        )
    
@app.function_name(name="Register")
@app.route(route="register", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def register_user(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=build_cors_headers("POST, OPTIONS"))

    try:
        logging.info("=== Register START ===")
        data = req.get_json()
        logging.info(f"Request data: {data}")
        
        email = data.get("email")
        user_name = data.get("user_name")
        password = data.get("password")
        is_manager = data.get("is_manager", False)
        logging.info(f"Email: {email}, UserName: {user_name}, IsManager: {is_manager}")

        # 入力チェック
        if not email or not user_name or not password:
            logging.warning("Missing required fields")
            return func.HttpResponse(
                json.dumps({"success": False, "message": "email, user_name, password はすべて必須です"}, ensure_ascii=False),
                status_code=400,
                headers=build_cors_headers("POST, OPTIONS")
            )

        # メールアドレス重複チェック
        check_query = "SELECT user_id FROM dbo.Users WHERE email = ?"
        existing_user = execute_query(check_query, (email,))
        
        if existing_user:
            logging.warning(f"Email already exists: {email}")
            return func.HttpResponse(
                json.dumps({"success": False, "message": "このメールアドレスはすでに登録されています"}, ensure_ascii=False),
                status_code=409,
                headers=build_cors_headers("POST, OPTIONS")
            )

        # パスワードハッシュ化
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode(), salt)
        
        # 認証トークン生成
        activation_token = str(uuid.uuid4())
        
        # 現在時刻取得
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        # 新規ユーザー作成（is_active=Falseで仮登録）
        insert_query = """
            INSERT INTO dbo.Users (
                user_name, email, password_hash, salt, 
                is_active, account_status, inserted_datetime, updated_datetime, 
                is_manager, activation_token
            ) VALUES (?, ?, ?, ?, 0, 'ACTIVE', ?, ?, ?, ?)
        """
        
        execute_query(insert_query, (
            user_name,
            email,
            password_hash.decode(),
            salt.decode(),
            current_time,
            current_time,
            is_manager,
            activation_token
        ))
        
        # 作成されたユーザーのIDを取得
        user_query = "SELECT user_id FROM dbo.Users WHERE email = ?"
        new_user = execute_query(user_query, (email,))
        
        if new_user:
            user_id = new_user[0]["user_id"]
            logging.info(f"=== Register SUCCESS - User ID: {user_id} ===")
            
            # 認証メール送信（エラーはログのみ、ユーザーには返さない）
            try:
                send_email_smtp(email, activation_token)
            except Exception as email_error:
                logging.error(f"❌ 認証メール送信エラー: {email_error}")
            
            return func.HttpResponse(
                json.dumps({
                    "success": True,
                    "message": "ユーザー登録が完了しました。メールをご確認ください。",
                    "user_id": user_id
                }, ensure_ascii=False),
                status_code=201,
                headers=build_cors_headers("POST, OPTIONS")
            )
        else:
            raise Exception("ユーザー作成後にID取得に失敗しました")

    except Exception as e:
        logging.error("=== Register ERROR ===")
        logging.exception("登録エラー詳細:")
        log_trigger_error(
            event_type="error",
            table_name="Users",
            record_id=-1,
            additional_info=f"[register_user] {str(e)}"
        )
        return func.HttpResponse(
            json.dumps({"success": False, "message": "登録処理中にエラーが発生しました"}, ensure_ascii=False),
            status_code=500,
            headers=build_cors_headers("POST, OPTIONS")
        )

@app.function_name(name="ActivateUser")
@app.route(route="activate", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def activate_user(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logging.info("=== ActivateUser START ===")
        
        # クエリパラメータからトークンを取得
        token = req.params.get("token")
        logging.info(f"Token: {token}")
        
        if not token:
            logging.warning("Token not provided")
            return func.HttpResponse(
                json.dumps({"success": False, "message": "トークンが指定されていません"}, ensure_ascii=False),
                status_code=400,
                mimetype="application/json"
            )

        # トークン検証
        user_check = execute_query("SELECT user_id FROM dbo.Users WHERE activation_token = ?", (token,))
        if not user_check:
            logging.warning(f"Invalid or used token: {token}")
            return func.HttpResponse(
                json.dumps({"success": False, "message": "トークンが無効または既に使用されています"}, ensure_ascii=False),
                status_code=404,
                mimetype="application/json"
            )

        user_id = user_check[0]["user_id"]
        logging.info(f"Valid token found for user_id: {user_id}")
        
        # ユーザーを有効化
        update_query = """
            UPDATE dbo.Users
            SET is_active = 1, activation_token = NULL, updated_datetime = GETDATE()
            WHERE user_id = ?
        """
        execute_query(update_query, (user_id,))
        
        logging.info(f"=== ActivateUser SUCCESS - User ID: {user_id} ===")
        
        # 成功時：HTMLページを直接返す
        success_html = f"""
<!DOCTYPE html>
<html lang="ja">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>認証完了</title>
    <style>
      body {{
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
        background-color: #f5f5f5;
        color: #333;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
      }}
      .container {{
        text-align: center;
        background: #fff;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        max-width: 90%;
        width: 400px;
      }}
      h2 {{
        font-size: 1.8rem;
        margin-bottom: 1rem;
      }}
      p {{
        font-size: 1rem;
        margin-bottom: 1.5rem;
      }}
      .button {{
        background-color: #4CAF50;
        color: white;
        padding: 12px 24px;
        border: none;
        border-radius: 6px;
        font-size: 1rem;
        text-decoration: none;
        display: inline-block;
        transition: background-color 0.3s ease;
      }}
      .button:hover {{
        background-color: #45a049;
      }}
    </style>
  </head>
  <body>
    <div class="container">
      <h2>✅ 認証完了</h2>
      <p>ご登録ありがとうございます。</p>
      <a href="https://audio-sales-analyzer.vercel.app/" class="button">ログイン画面へ</a>
    </div>
  </body>
</html>
"""
        return func.HttpResponse(success_html, status_code=200, mimetype="text/html")

    except Exception as e:
        logging.error("=== ActivateUser ERROR ===")
        logging.exception("アクティベート処理失敗:")
        log_trigger_error(
            event_type="error",
            table_name="Users",
            record_id=-1,
            additional_info=f"[activate_user] {str(e)}"
        )
        return func.HttpResponse(
            json.dumps({"success": False, "message": "アクティベート処理中にエラーが発生しました"}, ensure_ascii=False),
            status_code=500,
            mimetype="application/json"
        )

@app.function_name(name="Login")
@app.route(route="users/login", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def login_user(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=build_cors_headers("POST, OPTIONS"))

    try:
        print("=== Login START ===")
        data = req.get_json()
        print(f"Request data: {data}")
        
        email = data.get("email")
        password = data.get("password")
        print(f"Email: {email}, Password: {password}")

        if not email or not password:
            print("Missing email or password")
            return func.HttpResponse("email と password は必須です", status_code=400)

        query = """
            SELECT user_id, user_name, email, password_hash, is_active, account_status, is_manager, manager_id
            FROM dbo.Users
            WHERE email = ? AND is_active = 1
        """
        print(f"Query: {query}")
        print(f"Query params: ({email},)")
        
        result = execute_query(query, (email,))
        print(f"Query result: {result}")

        if not result:
            print("User not found")
            return func.HttpResponse(
                json.dumps({"success": False, "message": "ユーザーが見つかりません"}, ensure_ascii=False), 
                status_code=401,
                headers=build_cors_headers("POST, OPTIONS")
            )

        user = result[0]
        stored_hash = user.get("password_hash")
        print(f"User found: {user.get('user_name')}")
        print(f"Stored hash: {stored_hash}")
        print(f"Input password: {password}")
        print(f"Input password encoded: {password.encode()}")

        try:
            password_check = bcrypt.checkpw(password.encode(), stored_hash.encode())
            print(f"Password check result: {password_check}")
        except Exception as bcrypt_error:
            print(f"Bcrypt error: {bcrypt_error}")
            raise

        if not password_check:
            print("Password mismatch")
            return func.HttpResponse(
                json.dumps({"success": False, "message": "パスワードが正しくありません"}, ensure_ascii=False), 
                status_code=401,
                headers=build_cors_headers("POST, OPTIONS")
            )

        # 認証成功時のレスポンス
        user.pop("password_hash", None)  # セキュリティのため返さない
        print("=== Login SUCCESS ===")
        return func.HttpResponse(
            json.dumps({"success": True, "user": user}, ensure_ascii=False), 
            status_code=200,
            headers=build_cors_headers("POST, OPTIONS")
        )

    except Exception as e:
        print(f"=== Login ERROR: {e} ===")
        logging.exception("ログイン処理でエラーが発生しました")
        log_trigger_error(
            event_type="error",
            table_name="Users",
            record_id=-1,
            additional_info=f"[login_user] {str(e)}"
        )
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False), 
            status_code=500,
            headers=build_cors_headers("POST, OPTIONS")
        )
    
@app.function_name(name="GetUserById")
@app.route(route="users/id/{user_id}", auth_level=func.AuthLevel.ANONYMOUS)
def get_user_by_id_func(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=build_cors_headers("GET, OPTIONS"))

    try:
        user_id = req.route_params.get("user_id")
        if not user_id:
            return func.HttpResponse("user_id is required", status_code=400)

        query = "SELECT * FROM [dbo].[Users] WHERE [user_id] = ?"
        result = execute_query(query, (user_id,))

        if result:
            return func.HttpResponse(
                json.dumps(result[0], ensure_ascii=False, default=str),
                mimetype="application/json",
                status_code=200,
                headers=build_cors_headers("GET, OPTIONS")
            )
        else:
            return func.HttpResponse(
                json.dumps({"error": "ユーザーが見つかりません"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=404,
                headers=build_cors_headers("GET, OPTIONS")
            )

    except Exception as e:
        logging.exception("ユーザー取得エラー:")
        log_trigger_error(
            event_type="error",
            table_name="Users",
            record_id=user_id if user_id else -1,
            additional_info=f"[get_user_by_id_func] {str(e)}"
        )
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=build_cors_headers("GET, OPTIONS")
        )


@app.function_name(name="GetLatestComments")
@app.route(route="comments-latest", auth_level=func.AuthLevel.ANONYMOUS)
def get_latest_comments(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=build_cors_headers("GET, OPTIONS"))

    try:
        query_params = parse_qs(urlparse(req.url).query)
        user_id = query_params.get("userId", [None])[0]
        
        if not user_id:
            return func.HttpResponse("userId is required", status_code=400)

        query = """
            SELECT 
            c.comment_id,
            c.segment_id,
            c.meeting_id,
            c.user_id,
            c.content,
            c.inserted_datetime,
            c.updated_datetime,
            u.user_name,
            m.client_company_name,
            m.client_contact_name
            FROM dbo.Comments c
            JOIN dbo.BasicInfo b ON c.meeting_id = b.meeting_id
            JOIN dbo.Users u ON c.user_id = u.user_id
            JOIN dbo.Meetings m ON c.meeting_id = m.meeting_id
            WHERE b.user_id = ?
            AND c.deleted_datetime IS NULL
            ORDER BY c.inserted_datetime DESC
        """

        result = execute_query(query, (user_id,))

        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, default=str), 
            status_code=200, 
            mimetype="application/json",
            headers=build_cors_headers("GET, OPTIONS")
        )

    except Exception as e:
        logging.exception("コメント取得エラー:")
        log_trigger_error(
            event_type="error",
            table_name="Comments",
            record_id=-1,
            additional_info=f"[get_latest_comments] {str(e)}"
        )
        return func.HttpResponse(f"エラー: {str(e)}", status_code=500)
    
@app.function_name(name="GetMembersMeetings")
@app.route(route="members-meetings", auth_level=func.AuthLevel.ANONYMOUS)
def get_members_meetings(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=build_cors_headers("GET, OPTIONS"))

    try:
        query_params = parse_qs(urlparse(req.url).query)
        manager_id = query_params.get("manager_id", [None])[0]
        
        if not manager_id:
            return func.HttpResponse("manager_id is required", status_code=400)

        query = """
            SELECT m.*, u.user_name
            FROM Meetings m
            JOIN Users u ON m.user_id = u.user_id
            WHERE u.manager_id = ?
            ORDER BY m.meeting_datetime DESC
        """

        result = execute_query(query, (manager_id,))

        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, default=str),
            status_code=200,
            mimetype="application/json",
            headers=build_cors_headers("GET, OPTIONS")
        )

    except Exception as e:
        logging.exception("メンバー会議取得エラー:")
        log_trigger_error(
            event_type="error",
            table_name="Meetings",
            record_id=-1,
            additional_info=f"[get_members_meetings] {str(e)}"
        )
        return func.HttpResponse(f"エラー: {str(e)}", status_code=500)

@app.function_name(name="SaveBasicInfo")
@app.route(route="basicinfo", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def save_basic_info_func(req: func.HttpRequest) -> func.HttpResponse:
    """会議の基本情報を保存する（datetime変換を使わない版）"""
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers=build_cors_headers("POST, OPTIONS"))

        req_body = req.get_json()
        logging.info(f"リクエストボディ: {req_body}")

        required_fields = ['user_id', 'client_contact_name', 'client_company_name', 'meeting_datetime']
        for field in required_fields:
            if field not in req_body:
                return func.HttpResponse(
                    f"Missing required field: {field}",
                    status_code=400
                )

        # フィールド取得（datetime変換しない）
        user_id = req_body["user_id"]
        contact_name = req_body["client_contact_name"]
        company_name = req_body["client_company_name"]
        meeting_datetime = req_body["meeting_datetime"]
        industry_type = req_body.get("industry", "")
        company_scale = req_body.get("scale", "")
        sales_goal = req_body.get("meeting_goal", "")

        insert_query = """
            INSERT INTO dbo.BasicInfo (
                user_id,
                client_contact_name,
                client_company_name,
                meeting_datetime,
                industry_type,
                company_scale,
                sales_goal,
                inserted_datetime,
                updated_datetime
            )
            OUTPUT INSERTED.meeting_id
            VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())
        """

        # execute_queryはSELECTクエリの結果を返すため、INSERTの場合は直接DB接続を使用
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(insert_query, (
                user_id,
                contact_name,
                company_name,
                meeting_datetime,
                industry_type,
                company_scale,
                sales_goal
            ))

            row = cursor.fetchone()
            if not row or row[0] is None:
                raise Exception("会議IDの取得に失敗しました")

            conn.commit()
            return func.HttpResponse(
                json.dumps({
                    "message": "会議の基本情報が保存されました",
                    "meeting_id": int(row[0])
                }, ensure_ascii=False, default=str),
                mimetype="application/json",
                status_code=201,
                headers=build_cors_headers("POST, OPTIONS")
            )

    except Exception as e:
        logging.exception("SaveBasicInfo エラー:")
        log_trigger_error(
            event_type="error",
            table_name="BasicInfo",
            record_id=-1,  
            additional_info=f"[save_basic_info_func] {str(e)}"
        )
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False, default=str),
            mimetype="application/json",
            status_code=500,
            headers=build_cors_headers("POST, OPTIONS")
        )

def send_email_smtp(to_email: str, token: str):
    """
    SMTPを使用して認証メールを送信する
    """
    # 🔹 ① 開始時ログ
    logging.info(f"📧 send_email_smtp() 呼び出し開始 → 宛先: {to_email}")
    
    from_email = os.getenv("GMAIL_ADDRESS")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not from_email or not app_password:
        logging.error("GMAIL_ADDRESS または GMAIL_APP_PASSWORD が未設定です")
        return

    activation_link = f"https://saa-api-func.azurewebsites.net/api/activate?token={token}"
    body = f"""
Audio Sales Analyzer にご登録いただきありがとうございます。

以下のリンクをクリックして、アカウントを有効化してください：

{activation_link}

このリンクは一度限り有効です。
"""

    msg = MIMEText(body)
    msg["Subject"] = "【AudioSales】アカウント認証のご案内"
    msg["From"] = from_email
    msg["To"] = to_email

    # 🔹 1. 宛先ログの強化
    logging.info(f"📤 認証メール送信先: {to_email}")
    
    # 🔹 2. メール本文ログ（本番環境ならコメントアウトOK）
    logging.debug(f"📨 メール本文:\n{body}")

    try:
        # 🔹 ② サーバ接続直後ログ
        logging.info("🔄 SMTPサーバ接続開始（smtp.gmail.com:587）")
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(from_email, app_password)
            # 🔹 ③ ログイン成功後ログ
            logging.info(f"🔐 SMTPログイン成功: {from_email}")
            
            # 🔹 ④ メール送信直後のステータス
            response = server.send_message(msg)
            logging.info(f"📤 メール送信処理完了 → response: {response}")
            logging.info(f"✅ 認証メール送信完了: {to_email}")
    except Exception as e:
        # 🔹 ⑤ エラー時の詳細（既にある場合は補強）
        logging.exception(f"🚨 SMTP送信エラー: {str(e)}")

def generate_sas_url(container_name: str, blob_name: str) -> str:
    account_name = os.getenv("ALT_STORAGE_ACCOUNT_NAME")  # ← passrgmoc83cf
    account_key = os.getenv("ALT_STORAGE_ACCOUNT_KEY")    # ← 対応するアクセスキー

    if not account_name or not account_key:
        raise Exception("ALT_STORAGE_ACCOUNT_NAME または ALT_STORAGE_ACCOUNT_KEY が未設定です")

    print('=== generate_sas_url START ===')
    print('account_name:', account_name)
    print('container_name:', container_name)
    print('blob_name:', blob_name)

    # "meeting-audio/xxx.wav" のようなパスからコンテナ名とファイル名を抽出
    if "/" in blob_name:
        parts = blob_name.split("/", 1)
        actual_container = parts[0]
        actual_blob_name = parts[1]
        print(f'Extracted container: {actual_container}, blob: {actual_blob_name}')
    else:
        actual_container = container_name
        actual_blob_name = blob_name
        print(f'Using provided container: {actual_container}, blob: {actual_blob_name}')

    try:
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=actual_container,
            blob_name=actual_blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )
        print('sas_token generated successfully')
    except Exception as e:
        print('generate_blob_sas error:', e)
        raise

    return f"https://{account_name}.blob.core.windows.net/{actual_container}/{actual_blob_name}?{sas_token}"

# 会話セグメント取得エンドポイント
@app.function_name(name="GetConversationSegmentsByMeetingId")
@app.route(route="conversation/segments/{meeting_id}", methods=["GET", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def get_conversation_segments_by_meeting_id(req: func.HttpRequest) -> func.HttpResponse:
    print("=== GetConversationSegmentsByMeetingId START ===")
    try:
        if req.method == "OPTIONS":
            print("OPTIONS request - returning 204")
            return func.HttpResponse(status_code=204, headers=build_cors_headers("GET, OPTIONS"))

        meeting_id_str = req.route_params.get('meeting_id')
        print(f"meeting_id_str: {meeting_id_str}")
        try:
            meeting_id = int(meeting_id_str)
        except (TypeError, ValueError):
            print(f"Invalid meeting_id: {meeting_id_str}")
            return func.HttpResponse(
                json.dumps({"error": "invalid meeting_id"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400,
                headers=build_cors_headers("GET, OPTIONS")
            )

        print(f"[GetConversationSegments] meeting_id = {meeting_id}")

        query = """
            SELECT s.segment_id, s.user_id, s.speaker_id, s.meeting_id, s.content, 
                   s.file_name, s.file_path, s.file_size, s.duration_seconds, s.status, 
                   s.inserted_datetime, s.updated_datetime, s.start_time, s.end_time, 
                   sp.speaker_name, sp.speaker_role 
            FROM dbo.ConversationSegments s 
            LEFT JOIN dbo.Speakers sp ON s.speaker_id = sp.speaker_id 
            WHERE s.deleted_datetime IS NULL AND s.meeting_id = ?
        """
        print("Executing query...")
        segments = execute_query(query, (meeting_id,))
        print(f"Query result: {len(segments)} segments found")

        # 各セグメントに対して SAS付きURLを生成して追加
        for segment in segments:
            file_name = segment.get("file_name")
            if file_name:
                blob_path = f"meeting-audio/{file_name}"
                segment["audio_path"] = generate_sas_url("", blob_path)
            else:
                segment["audio_path"] = ""

        print("=== GetConversationSegmentsByMeetingId SUCCESS ===")
        return func.HttpResponse(
            json.dumps({"success": True, "segments": segments}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=build_cors_headers("GET, OPTIONS")
        )
    except Exception as e:
        print(f"=== GetConversationSegmentsByMeetingId ERROR: {e} ===")
        logging.exception("GetConversationSegments エラー:")
        log_trigger_error(
            event_type="error",
            table_name="ConversationSegments",
            record_id=meeting_id if 'meeting_id' in locals() else -1,
            additional_info=f"[get_conversation_segments_by_meeting_id] {str(e)}"
        )
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=build_cors_headers("GET, OPTIONS")
        )
    

# コメント一覧取得
@app.function_name(name="GetCommentsBySegmentId")
@app.route(route="comments/{segment_id}", methods=["GET", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def get_comments_by_segment_id(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers=build_cors_headers("GET, OPTIONS"))

        segment_id = req.route_params.get('segment_id')
        query = """
            SELECT c.comment_id, c.segment_id, c.meeting_id, c.user_id, c.content, 
                   c.inserted_datetime, c.updated_datetime, u.user_name
            FROM dbo.Comments c 
            JOIN dbo.Users u ON c.user_id = u.user_id 
            WHERE c.deleted_datetime IS NULL AND c.segment_id = ?
        """
        comments = execute_query(query, (segment_id,))

        for comment in comments:
            comment['readers'] = []

        return func.HttpResponse(
            json.dumps({"success": True, "comments": comments}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=build_cors_headers("GET, OPTIONS")
        )
    except Exception as e:
        log_trigger_error(
            event_type="error",
            table_name="Comments",
            record_id=segment_id if 'segment_id' in locals() else -1,
            additional_info=f"[get_comments_by_segment_id] {str(e)}"
        )
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=build_cors_headers("GET, OPTIONS")
        )

# コメント追加
@app.function_name(name="AddComment")
@app.route(route="comments", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def create_comment(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers=build_cors_headers("POST, OPTIONS"))

        data = req.get_json()
        required = ['segment_id', 'meeting_id', 'user_id', 'content']
        if not all(k in data for k in required):
            return func.HttpResponse(json.dumps({"success": False, "message": "Missing fields"}, ensure_ascii=False), status_code=400)

        insert_query = """
            INSERT INTO dbo.Comments (segment_id, meeting_id, user_id, content, inserted_datetime, updated_datetime)
            VALUES (?, ?, ?, ?, GETDATE(), GETDATE())
        """
        execute_query(insert_query, (
            data['segment_id'], data['meeting_id'], data['user_id'], data['content']
        ))

        comment_id = execute_query("SELECT TOP 1 comment_id FROM dbo.Comments ORDER BY comment_id DESC")[0]['comment_id']
        return func.HttpResponse(json.dumps({"success": True, "comment_id": comment_id}, ensure_ascii=False), status_code=201)

    except Exception as e:
        log_trigger_error(
            event_type="error",
            table_name="Comments",
            record_id=comment_id if 'comment_id' in locals() else -1,
            additional_info=f"[create_comment] {str(e)}"
        )
        return func.HttpResponse(json.dumps({"error": str(e)}, ensure_ascii=False), status_code=500)

# コメント既読
@app.function_name(name="MarkCommentAsRead")
@app.route(route="comments/read", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def mark_comment_as_read(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers=build_cors_headers("POST, OPTIONS"))

        data = req.get_json()
        comment_id = data.get('comment_id')
        user_id = data.get('user_id')

        insert_query = """
            IF NOT EXISTS (SELECT 1 FROM dbo.CommentReads WHERE comment_id = ? AND reader_id = ?)
            INSERT INTO dbo.CommentReads (comment_id, reader_id, read_datetime)
            VALUES (?, ?, GETDATE())
        """
        execute_query(insert_query, (comment_id, user_id, comment_id, user_id))

        return func.HttpResponse(json.dumps({"success": True, "message": "Marked as read"}, ensure_ascii=False), status_code=200)

    except Exception as e:
        log_trigger_error(
            event_type="error",
            table_name="Comments",
            record_id=comment_id if 'comment_id' in locals() else -1,
            additional_info=f"[mark_comment_as_read] {str(e)}"
        )
        return func.HttpResponse(json.dumps({"error": str(e)}, ensure_ascii=False), status_code=500)

# コメント削除（論理）
@app.function_name(name="DeleteComment")
@app.route(route="comments/{comment_id}", methods=["DELETE", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def delete_comment(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers=build_cors_headers("DELETE, OPTIONS"))

        comment_id = req.route_params.get('comment_id')
        update_query = "UPDATE dbo.Comments SET deleted_datetime = GETDATE() WHERE comment_id = ?"
        execute_query(update_query, (comment_id,))

        return func.HttpResponse(json.dumps({"success": True, "message": "コメントを削除しました"}, ensure_ascii=False), status_code=200)

    except Exception as e:
        log_trigger_error(
            event_type="error",
            table_name="Comments",
            record_id=comment_id if 'comment_id' in locals() else -1,
            additional_info=f"[delete_comment] {str(e)}"
        )
        return func.HttpResponse(json.dumps({"error": str(e)}, ensure_ascii=False), status_code=500)


# GetAllMeetings（会議一覧取得）
@app.function_name(name="SearchMeetings")
@app.route(route="meetings", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_all_meetings(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=build_cors_headers("GET, OPTIONS"))

    try:
        query_params = parse_qs(urlparse(req.url).query)
        from_date = query_params.get("fromDate", [None])[0]
        to_date = query_params.get("toDate", [None])[0]
        user_id = query_params.get("userId", [None])[0]

        base_query = """
            SELECT m.*, u.user_name
            FROM dbo.Meetings m
            LEFT JOIN dbo.Users u ON m.user_id = u.user_id
            WHERE m.deleted_datetime IS NULL
        """

        conditions = []
        params = []

        if from_date:
            conditions.append("m.meeting_datetime >= ?")
            params.append(from_date)
        if to_date:
            conditions.append("m.meeting_datetime <= ?")
            params.append(to_date)
        if user_id and user_id.isdigit():
            conditions.append("m.user_id = ?")
            params.append(int(user_id))

        if conditions:
            base_query += " AND " + " AND ".join(conditions)

        base_query += " ORDER BY m.meeting_datetime DESC"

        result = execute_query(base_query, tuple(params))
        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, default=str),
            mimetype="application/json",
            status_code=200,
            headers=build_cors_headers("GET, OPTIONS")
        )

    except Exception as e:

        logging.exception("会議一覧取得エラー:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            status_code=500,
            headers=build_cors_headers("GET, OPTIONS")
        )    
    # GetCommentsByMeetingId（会議単位のコメント一覧取得）
@app.function_name(name="GetCommentsByMeetingId")
@app.route(route="comments/by-meeting/{meeting_id}", methods=["GET", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def get_comments_by_meeting_id(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers=build_cors_headers("GET, OPTIONS"))

        meeting_id = req.route_params.get('meeting_id')
        if not meeting_id:
            return func.HttpResponse(json.dumps({"error": "meeting_id is required"}, ensure_ascii=False), status_code=400)

        query = """
            SELECT c.comment_id, c.segment_id, c.meeting_id, c.user_id, c.content,
                   c.inserted_datetime, c.updated_datetime, u.user_name
            FROM dbo.Comments c
            JOIN dbo.Users u ON c.user_id = u.user_id
            WHERE c.deleted_datetime IS NULL AND c.meeting_id = ?
            ORDER BY c.inserted_datetime ASC
        """
        comments = execute_query(query, (meeting_id,))

        for comment in comments:
            comment['readers'] = []

        return func.HttpResponse(
            json.dumps({"success": True, "comments": comments}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=build_cors_headers("GET, OPTIONS")
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=build_cors_headers("GET, OPTIONS")
        )

@app.function_name(name="GetAllUsers")
@app.route(route="users", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_all_users(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=build_cors_headers("GET, OPTIONS"))

    try:
        query = """
            SELECT user_id,user_name
            FROM dbo.Users
            WHERE deleted_datetime IS NULL
            ORDER BY user_name ASC
        """

        result = execute_query(query)

        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, default=str),
            mimetype="application/json",
            status_code=200,
            headers=build_cors_headers("GET, OPTIONS")
        )
        
    except Exception as e:
        logging.exception("ユーザー一覧取得エラー:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=build_cors_headers("GET, OPTIONS")
        )

# 会議基本情報取得Add commentMore actions
@app.function_name(name="GetBasicInfoByMeetingId")
@app.route(route="basicinfo/{meeting_id}", methods=["GET", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def get_basic_info_by_meeting_id(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers=build_cors_headers("GET, OPTIONS"))

        meeting_id = req.route_params.get('meeting_id')
        query = """
            SELECT meeting_id, user_id, client_contact_name, client_company_name,
                   meeting_datetime, duration_seconds, status, transcript_text,
                   file_name, file_size, error_message
            FROM dbo.Meetings
            WHERE meeting_id = ?
        """
        results = execute_query(query, (meeting_id,))

        if not results:
            return func.HttpResponse(json.dumps({"error": "Not found"}, ensure_ascii=False), status_code=404)

        return func.HttpResponse(json.dumps({"success": True, "basicInfo": results[0]}, ensure_ascii=False), status_code=200)

    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}, ensure_ascii=False), status_code=500)
    
@app.function_name(name="GetCommentReadStatus")
@app.route(route="comment-read-status", methods=["GET", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def get_comment_read_status(req: func.HttpRequest) -> func.HttpResponse:
    logging.warning("🚨 GetCommentReadStatus IS RUNNING NOW")
    logging.info("🚀 GetCommentReadStatus 開始")
    logging.info(f"🔍 リクエストクエリ: {req.url}")
    
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=build_cors_headers("GET, OPTIONS"))

    try:
        query_params = parse_qs(urlparse(req.url).query)
        user_id = query_params.get("userId", [None])[0]
        comment_id = query_params.get("commentId", [None])[0]
        
        logging.info(f"👤 user_id: {user_id}, 💬 comment_id: {comment_id}")

        if not user_id or not comment_id:
            logging.warning(f"❌ パラメータ不足: user_id={user_id}, comment_id={comment_id}")
            return func.HttpResponse(
                json.dumps({"error": "userId and commentId are required", "debug": f"user_id: {user_id}, comment_id: {comment_id}"}, ensure_ascii=False),
                status_code=400,
                mimetype="application/json",
                headers=build_cors_headers("GET, OPTIONS")
            )

        query = """
            SELECT read_datetime 
            FROM dbo.CommentReads 
            WHERE reader_id = ? AND comment_id = ? 
        """
        
        logging.info(f"🧾 クエリを実行: {query} with params {(user_id, comment_id)}")
        result = execute_query(query, (user_id, comment_id))
        
        logging.info(f"✅ クエリ結果: {result}")

        if result:
            response = {
                "isRead": True,
                "read_at": result[0]['read_datetime'],
                "debug": f"user_id: {user_id}, comment_id: {comment_id}"
            }
        else:
            response = {
                "isRead": False,
                "debug": f"user_id: {user_id}, comment_id: {comment_id}"
            }

        logging.info(f"📤 レスポンス送信: {response}")
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            status_code=200,
            mimetype="application/json",
            headers=build_cors_headers("GET, OPTIONS")
        )

    except Exception as e:
        logging.exception("❌ GetCommentReadStatus 処理中に例外発生:")
        return func.HttpResponse(
            json.dumps({"error": str(e), "debug": f"userId={user_id}, commentId={comment_id}"}, ensure_ascii=False),
            status_code=200,  # ← 本番調査用に一時的に200返す
            headers=build_cors_headers("GET, OPTIONS"),
            mimetype="application/json"
        )