"""
GetMeetings関数
会議一覧取得エンドポイント
"""

import azure.functions as func
import logging
import json
import traceback
import sys
import os
from datetime import datetime

# パスを追加してutilsモジュールをインポート可能にする
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.db_utils import execute_query

# ロガーの設定
logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """会議一覧取得エンドポイント"""
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

        logger.info("=== 会議検索開始 ===")
        
        # クエリパラメータの取得
        user_id = req.params.get("userId")
        from_date_str = req.params.get("fromDate")
        to_date_str = req.params.get("toDate")

        logger.info(f"[会議検索] リクエストパラメータ:")
        logger.info(f"[会議検索] - userId: {user_id}")
        logger.info(f"[会議検索] - fromDate: {from_date_str}")
        logger.info(f"[会議検索] - toDate: {to_date_str}")

        # クエリの構築
        query = """
            SELECT m.meeting_id, m.user_id, m.client_contact_name, m.client_company_name, 
                   m.meeting_datetime, m.duration_seconds, m.status, m.transcript_text, 
                   m.file_name, m.file_size, m.error_message, u.user_name
            FROM dbo.Meetings m
            JOIN dbo.Users u ON m.user_id = u.user_id
            WHERE 1=1
        """
        params = []

        # 営業担当でフィルター
        if user_id:
            try:
                user_id_int = int(user_id)
                query += " AND m.user_id = ?"
                params.append(user_id_int)
                logger.info(f"[会議検索] ユーザーIDフィルター適用: {user_id_int}")
            except ValueError:
                logger.error(f"[会議検索] 無効なユーザーID形式: {user_id}")
                return func.HttpResponse(
                    json.dumps({"error": "Invalid userId format"}, ensure_ascii=False),
                    mimetype="application/json",
                    status_code=400,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type"
                    }
                )

        # 開催日付フィルター（from）
        if from_date_str:
            try:
                from_date = datetime.fromisoformat(from_date_str)
                query += " AND CAST(m.meeting_datetime AS DATE) >= ?"
                params.append(from_date.date())
                logger.info(f"[会議検索] 開始日フィルター適用: {from_date.date()}")
            except ValueError:
                logger.error(f"[会議検索] 無効な開始日形式: {from_date_str}")
                return func.HttpResponse(
                    json.dumps({"error": "Invalid fromDate format. Use YYYY-MM-DD"}, ensure_ascii=False),
                    mimetype="application/json",
                    status_code=400,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type"
                    }
                )

        # 開催日付フィルター（to）
        if to_date_str:
            try:
                to_date = datetime.fromisoformat(to_date_str)
                query += " AND CAST(m.meeting_datetime AS DATE) <= ?"
                params.append(to_date.date())
                logger.info(f"[会議検索] 終了日フィルター適用: {to_date.date()}")
            except ValueError:
                logger.error(f"[会議検索] 無効な終了日形式: {to_date_str}")
                return func.HttpResponse(
                    json.dumps({"error": "Invalid toDate format. Use YYYY-MM-DD"}, ensure_ascii=False),
                    mimetype="application/json",
                    status_code=400,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type"
                    }
                )

        # 日付の降順でソート
        query += " ORDER BY m.meeting_datetime DESC"

        logger.info(f"[会議検索] 実行クエリ: {query}")
        logger.info(f"[会議検索] パラメータ: {params}")

        # クエリの実行
        meetings = execute_query(query, params)
        logger.info(f"[会議検索] 取得件数: {len(meetings)}")

        # フィルター適用状況のサマリー
        logger.info("[会議検索] フィルター適用状況:")
        if user_id:
            logger.info(f"[会議検索] - ユーザーID: {user_id}")
        if from_date_str:
            logger.info(f"[会議検索] - 開始日: {from_date_str}")
        if to_date_str:
            logger.info(f"[会議検索] - 終了日: {to_date_str}")
        if not any([user_id, from_date_str, to_date_str]):
            logger.info("[会議検索] - フィルターなし（全件取得）")

        logger.info("=== 会議検索終了 ===")

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
        logger.error(f"[会議検索] エラー発生: {str(e)}")
        logger.error(f"[会議検索] エラー詳細: {traceback.format_exc()}")
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