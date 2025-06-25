"""
GetCommentsLatest関数
最新コメント取得エンドポイント
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
    """最新コメント取得エンドポイント"""
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": "https://audio-sales-analyzer.vercel.app",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                }
            )

        # クエリパラメータの取得とバリデーション
        user_id = req.params.get('userId')
        is_manager = req.params.get('isManager', 'false').lower() == 'true'
        limit = int(req.params.get('limit', 5))

        if not user_id or not user_id.isdigit():
            return func.HttpResponse(
                json.dumps({"error": "userId パラメータが必要です"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400,
                headers={
                    "Access-Control-Allow-Origin": "https://audio-sales-analyzer.vercel.app",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                }
            )

        # コメント取得クエリ
        if is_manager:
            # マネージャーの場合：部下のコメントも含めて取得
            query = """
                SELECT TOP (?) 
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
                FROM Comments c
                INNER JOIN Users u ON c.user_id = u.user_id
                INNER JOIN Meetings m ON c.meeting_id = m.meeting_id
                WHERE (c.user_id = ? OR u.manager_id = ?)
                ORDER BY c.inserted_datetime DESC
            """
            comments = execute_query(query, (limit, int(user_id), int(user_id)))
        else:
            # 一般ユーザーの場合：自分のコメントのみ取得
            query = """
                SELECT TOP (?) 
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
                FROM Comments c
                INNER JOIN Users u ON c.user_id = u.user_id
                INNER JOIN Meetings m ON c.meeting_id = m.meeting_id
                WHERE c.user_id = ?
                ORDER BY c.inserted_datetime DESC
            """
            comments = execute_query(query, (limit, int(user_id)))

        return func.HttpResponse(
            json.dumps({
                "success": True,
                "comments": comments
            }, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "https://audio-sales-analyzer.vercel.app",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )

    except Exception as e:
        logger.error(f"Get comments latest error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        return func.HttpResponse(
            json.dumps({
                "success": False,
                "message": f"Internal server error: {str(e)}"
            }, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers={
                "Access-Control-Allow-Origin": "https://audio-sales-analyzer.vercel.app",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )
