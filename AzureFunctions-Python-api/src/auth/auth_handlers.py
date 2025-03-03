import logging
import json
import bcrypt
import jwt
import os
import traceback
import azure.functions as func
from datetime import datetime, UTC, timedelta

from ..utils.http import get_cors_headers, handle_options_request, create_json_response, create_error_response, parse_json_request, log_request
from ..utils.db import get_db_connection, execute_query, get_current_time
from ..models.user import User

# JWT設定
JWT_SECRET = os.environ.get("JWT_SECRET", "your-local-test-secret-key")  # 本番環境では環境変数から取得
JWT_EXPIRATION = 24 * 60 * 60  # 24時間（秒）

def login(req: func.HttpRequest, users_query: func.SqlRowList) -> func.HttpResponse:
    """
    ユーザーログイン処理
    """
    log_request(req, "Login")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    # リクエストデータの取得
    req_body = parse_json_request(req)
    if not req_body:
        return create_error_response("Invalid JSON data", 400)
    
    email = req_body.get('email')
    password = req_body.get('password')
    
    if not all([email, password]):
        logging.warning("Missing email or password")
        return create_error_response("Email and password are required", 400)
    
    # ユーザー検索
    user = None
    for row in users_query:
        if row["email"] == email:
            user = row
            break
    
    if not user:
        logging.warning(f"User not found for email: {email}")
        return create_error_response("Invalid email or password", 401)
    
    # パスワード検証
    try:
        # bcryptを使用してパスワードを検証
        stored_hash = user["password_hash"].encode('utf-8')
        password_bytes = password.encode('utf-8')
        
        password_valid = bcrypt.checkpw(password_bytes, stored_hash)
        
        if not password_valid:
            logging.warning(f"Invalid password for user: {email}")
            return create_error_response("Invalid email or password", 401)
    except Exception as e:
        logging.error(f"Password verification error: {str(e)}")
        return create_error_response("Authentication error", 500)
    
    # JWTトークン生成
    payload = {
        "user_id": user["user_id"],
        "email": user["email"],
        "user_name": user["user_name"],
        "role": "manager" if user["is_manager"] else "member",
        "exp": datetime.now(UTC) + timedelta(seconds=JWT_EXPIRATION)
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
    # レスポンス
    response_data = {
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "user_name": user["user_name"],
            "role": "manager" if user["is_manager"] else "member"
        }
    }
    
    logging.info(f"User {email} logged in successfully")
    
    return create_json_response(response_data, 200)

def register(req: func.HttpRequest, users: func.Out[func.SqlRow]) -> func.HttpResponse:
    """
    ユーザー登録処理
    """
    log_request(req, "Register")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    try:
        # リクエストデータの取得
        req_body = parse_json_request(req)
        if not req_body:
            return create_error_response("Invalid JSON data", 400)
        
        # 必須フィールドの確認
        required_fields = ["user_name", "email", "password", "role"]
        for field in required_fields:
            if field not in req_body:
                return create_error_response(f"Missing required field: {field}", 400)
        
        # メールアドレスの重複チェック
        query = "SELECT COUNT(*) as count FROM [dbo].[Users] WHERE email = ?"
        result = execute_query(query, [req_body['email']])
        
        if result and result[0]['count'] > 0:
            return create_error_response("このメールアドレスは既に登録されています", 400)
        
        # 現在時刻
        now = get_current_time()
        
        # パスワードのハッシュ化
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(
            req_body['password'].encode('utf-8'), 
            salt
        )
        
        # ユーザーオブジェクトの作成
        user = User(
            user_name=req_body['user_name'],
            email=req_body['email'],
            password_hash=password_hash.decode('utf-8'),
            salt=salt.decode('utf-8'),
            role=req_body['role'],
            is_active=True,
            account_status='active',
            inserted_datetime=now,
            updated_datetime=now,
            login_attempt_count=0
        )
        
        # マネージャー/メンバー固有の設定
        if req_body['role'] == 'member':
            manager_name = req_body.get('manager_name')
            if not manager_name:
                return create_error_response("メンバー登録にはマネージャー名が必要です", 400)
            
            # マネージャーの存在確認
            if not check_manager(manager_name):
                return create_error_response("指定されたマネージャーが存在しません。有効なマネージャーを指定してください。", 400)
            
            # メンバー用パラメータを設定
            user.manager_name = manager_name
        
        # SQLクエリにパラメータを渡す
        users.set(func.SqlRow(user.to_sql_row()))
        
        logging.info(f"User {req_body['email']} registered successfully")
        
        return create_json_response({
            "message": "ユーザー登録が完了しました",
            "user": {
                "user_name": user.user_name,
                "email": user.email,
                "role": user.role
            }
        }, 201)
        
    except Exception as e:
        error_message = str(e)
        logging.error(f'Error in register: {error_message}\n{traceback.format_exc()}')
        return create_error_response(error_message, 500)

def check_manager(manager_name: str) -> bool:
    """
    マネージャーの存在確認
    """
    try:
        query = "SELECT COUNT(*) as count FROM [dbo].[Users] WHERE user_name = ? AND is_manager = 1"
        result = execute_query(query, [manager_name])
        
        return result and result[0]['count'] > 0
    except Exception as e:
        logging.error(f"Error checking manager: {str(e)}")
        return False 