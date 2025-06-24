"""
GetMembersMeetings関数
メンバー会議一覧取得エンドポイント
"""

import azure.functions as func
import logging
import json
import traceback
import sys
import os

# パスを追加してutilsモジュールをインポート可能にする
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.db_utils import execute_query

# ロガーの設定
logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """メンバー会議一覧取得エンドポイント"""
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

        # manager_idパラメータの取得とバリデーション
        manager_id = req.params.get('manager_id')
        if not manager_id or not manager_id.isdigit():
            return func.HttpResponse(
                json.dumps({"error": "manager_id パラメータが必要です"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                }
            )

        query = """
            SELECT m.meeting_id, m.user_id, m.client_contact_name, m.client_company_name, 
                   m.meeting_datetime, m.duration_seconds, m.status, m.transcript_text, 
                   m.file_name, m.file_size, m.error_message, u.user_name 
            FROM dbo.Meetings m 
            JOIN dbo.Users u ON m.user_id = u.user_id
            WHERE u.manager_id = ?
            ORDER BY m.meeting_datetime DESC
        """
        meetings = execute_query(query, (int(manager_id),))

        return func.HttpResponse(
            json.dumps(meetings, ensure_ascii=False),
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
        logger.error(f"Get members meetings error: {str(e)}")
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