import logging
import json
import hashlib
import jwt
import datetime
import bcrypt
import azure.functions as func
from ..common.http import add_cors_headers, handle_options_request

# JWT設定 - ローカルテスト用
JWT_SECRET = "your-local-test-secret-key"  # 本番環境では環境変数から取得すべき
JWT_EXPIRATION = 24 * 60 * 60  # 24時間（秒）

def login_handler(req, users_query):
    """ユーザーログイン処理"""
    logging.info('Login function processed a request.')
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    headers = add_cors_headers()
    
    try:
        # JSONデータを取得
        req_body = req.get_json()
        email = req_body.get('email')
        password = req_body.get('password')
        
        logging.info(f"Login attempt for email: {email}")
        
    except ValueError as e:
        logging.error(f"JSON parsing error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON data"}),
            status_code=400,
            mimetype="application/json",
            headers=headers
        )

    if not all([email, password]):
        logging.warning("Missing email or password")
        return func.HttpResponse(
            json.dumps({"error": "Email and password are required"}),
            status_code=400,
            mimetype="application/json",
            headers=headers
        )
    
    # ユーザー検索
    user = None
    for row in users_query:
        if row["email"] == email:
            user = row
            break
    
    if not user:
        logging.warning(f"User not found for email: {email}")
        return func.HttpResponse(
            json.dumps({"error": "Invalid email or password"}),
            status_code=401,
            mimetype="application/json",
            headers=headers
        )
    
    # パスワード検証
    try:
        # bcryptを使用してパスワードを検証
        stored_hash = user["password_hash"].encode('utf-8')
        password_bytes = password.encode('utf-8')
        
        password_valid = bcrypt.checkpw(password_bytes, stored_hash)
        
        if not password_valid:
            logging.warning(f"Invalid password for user: {email}")
            return func.HttpResponse(
                json.dumps({"error": "Invalid email or password"}),
                status_code=401,
                mimetype="application/json",
                headers=headers
            )
    except Exception as e:
        logging.error(f"Password verification error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Authentication error"}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )
    
    # JWTトークン生成
    payload = {
        "user_id": user["user_id"],
        "email": user["email"],
        "user_name": user["user_name"],
        "is_manager": user["is_manager"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXPIRATION)
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
    # レスポンス
    response_data = {
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "user_name": user["user_name"],
            "is_manager": user["is_manager"]
        }
    }
    
    logging.info(f"User {email} logged in successfully")
    
    return func.HttpResponse(
        json.dumps(response_data),
        status_code=200,
        mimetype="application/json",
        headers=headers
    )