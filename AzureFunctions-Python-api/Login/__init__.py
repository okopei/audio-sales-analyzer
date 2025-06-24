"""
Login関数
ログインエンドポイント
"""

import azure.functions as func
import logging
import json
import traceback
import sys
import os

# パスを追加してutilsモジュールとsrcモジュールをインポート可能にする
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.db_utils import execute_query
from src.models.user import User

# ロガーの設定
logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """ログインエンドポイント"""
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                }
            )

        data = req.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return func.HttpResponse(
                json.dumps({"error": "Email and password are required"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                }
            )

        # データベースからユーザー情報を取得
        query = "SELECT * FROM dbo.Users WHERE email = ?"
        users = execute_query(query, (email,))

        if not users:
            return func.HttpResponse(
                json.dumps({"error": "Invalid email or password"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=401,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                }
            )

        user = User.from_dict(users[0])
        if not user.verify_password(password):
            return func.HttpResponse(
                json.dumps({"error": "Invalid email or password"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=401,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                }
            )

        response = {
            "user_id": user.user_id,
            "user_name": user.user_name,
            "email": user.email,
            "is_manager": user.is_manager,
            "manager_name": user.manager_name,
            "is_active": user.is_active,
            "account_status": user.account_status
        }

        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        ) 