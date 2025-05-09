import logging
import json
import bcrypt
import jwt
import os
import traceback
import azure.functions as func
from datetime import datetime, UTC, timedelta

from ..utils.http import get_cors_headers, handle_options_request, create_json_response, create_error_response, parse_json_request, log_request
from ..models.user import User
from ..utils.db import execute_query, get_current_time

# JWT設定
JWT_SECRET = os.environ.get("JWT_SECRET", "your-local-test-secret-key")  # 本番環境では環境変数から取得
JWT_EXPIRATION = 24 * 60 * 60  # 24時間（秒）

def login(req: func.HttpRequest) -> func.HttpResponse:
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
    
    try:
        # ユーザー検索
        query = "SELECT * FROM dbo.Users WHERE email = ?"
        users = execute_query(query, [email])
        
        if not users:
            logging.warning(f"User not found for email: {email}")
            return create_error_response("Invalid email or password", 401)
        
        user = users[0]
        
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
        
    except Exception as e:
        logging.error(f"Login error: {str(e)}")
        logging.error(f"Error details: {traceback.format_exc()}")
        return create_error_response(f"Internal server error: {str(e)}", 500)

def register(req: func.HttpRequest) -> func.HttpResponse:
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
        
        # 新しいユーザーIDを生成
        query = "SELECT TOP 1 user_id FROM dbo.Users ORDER BY user_id DESC"
        last_user = execute_query(query)
        new_user_id = 1
        if last_user:
            new_user_id = int(last_user[0]['user_id']) + 1
        
        # ユーザーをデータベースに挿入
        insert_query = """
            INSERT INTO dbo.Users (
                user_id, user_name, email, password_hash, salt, role, 
                manager_name, is_active, account_status, 
                inserted_datetime, updated_datetime, login_attempt_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        execute_query(insert_query, {
            'user_id': new_user_id,
            'user_name': user.user_name,
            'email': user.email,
            'password_hash': user.password_hash,
            'salt': user.salt,
            'role': user.role,
            'manager_name': user.manager_name,
            'is_active': user.is_active,
            'account_status': user.account_status,
            'inserted_datetime': user.inserted_datetime,
            'updated_datetime': user.updated_datetime,
            'login_attempt_count': user.login_attempt_count
        })
        
        logging.info(f"User {req_body['email']} registered successfully")
        
        return create_json_response({
            "message": "ユーザー登録が完了しました",
            "user": {
                "user_id": new_user_id,
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

def get_user_by_id(req: func.HttpRequest) -> func.HttpResponse:
    """
    ユーザーIDに基づいて単一ユーザー情報を取得する
    """
    log_request(req, "GetUserById")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    try:
        # ルートパラメータからuser_idを取得
        user_id = req.route_params.get('user_id')
        if not user_id:
            return create_error_response("user_id is required", 400)
        
        logging.info(f"Looking for user with ID: {user_id}")
        
        # ユーザーIDに基づいてユーザーを検索
        query = "SELECT * FROM dbo.Users WHERE user_id = ?"
        users = execute_query(query, [user_id])
        
        if not users:
            return create_error_response("User not found", 404)
        
        user_data = users[0]
        
        # User モデルを使用してデータを整形
        user = User(
            user_id=user_data.get("user_id"),
            user_name=user_data.get("user_name"),
            email=user_data.get("email"),
            role="manager" if user_data.get("is_manager") else "member",
            is_active=user_data.get("is_active", True),
            account_status=user_data.get("account_status", "active"),
            manager_name=user_data.get("manager_name")
        )
        
        # 機密情報を含まない形でユーザーデータを返す
        return create_json_response({"user": user.to_dict()})
    except Exception as e:
        logging.error(f"Error retrieving user: {str(e)}")
        return create_error_response(f"Internal server error: {str(e)}", 500) 