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

from utils.db_utils import execute_query, get_db_connection

# ロガーの設定
logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    logger.error("[DEBUG] ✅ GetMembersMeetings 呼び出し開始")

    try:
        manager_id = req.params.get('manager_id')
        logger.error(f"[DEBUG] manager_id: {manager_id}")

        logger.info("🟡 DB接続開始（pyodbc.connect）")
        try:
            conn = get_db_connection()
            logger.error("[DEBUG] ✅ get_db_connection 実行OK")
        except Exception as e:
            logger.exception("❌ DB接続エラーが発生しました")
            raise

        query = "SELECT * FROM meetings WHERE manager_id = ?"
        params = (manager_id,)
        rows = execute_query(query, params)
        logger.error(f"[DEBUG] ✅ クエリ実行結果: {rows}")

        return func.HttpResponse(json.dumps(rows, default=str), mimetype="application/json")

    except Exception as e:
        logger.error(f"[ERROR] 例外発生: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return func.HttpResponse("Error", status_code=500)

# def main(req: func.HttpRequest) -> func.HttpResponse:
#     """メンバー会議一覧取得エンドポイント"""
#     logger.error("[DEBUG] ✅ GetMembersMeetings 関数が呼び出されました（強制ERRORログ）")
#     try:
#         if req.method == "OPTIONS":
#             return func.HttpResponse(
#                 status_code=204,
#                 headers={
#                     "Access-Control-Allow-Origin": "https://audio-sales-analyzer.vercel.app",
#                     "Access-Control-Allow-Credentials": "true",
#                     "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
#                     "Access-Control-Allow-Headers": "Content-Type"
#                 }
#             )

#         # manager_idパラメータの取得とバリデーション
#         logger.info("[DEBUG] リクエストパラメータ取得開始")
#         manager_id = req.params.get('manager_id')
#         logger.info(f"[DEBUG] 受信した manager_id: {manager_id}")
#         if not manager_id or not manager_id.isdigit():
#             return func.HttpResponse(
#                 json.dumps({"error": "manager_id パラメータが必要です"}, ensure_ascii=False),
#                 mimetype="application/json",
#                 status_code=400,
#                 headers={
#                     "Access-Control-Allow-Origin": "https://audio-sales-analyzer.vercel.app",
#                     "Access-Control-Allow-Credentials": "true",
#                     "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
#                     "Access-Control-Allow-Headers": "Content-Type"
#                 }
#             )

#         # --- デバッグログを追加 ---
#         logger.info(f"[DEBUG] GetMembersMeetings で接続中のDB情報:")
        
#         # 動的にDB接続情報を取得
#         try:
#             conn = get_db_connection()
#             logger.info(f"[DEBUG] 接続文字列（サーバー名）: {conn.getinfo(pyodbc.SQL_SERVER_NAME)}")
#             logger.info(f"[DEBUG] データベース名: {conn.getinfo(pyodbc.SQL_DATABASE_NAME)}")
#             logger.info(f"[DEBUG] 接続状態: {conn.getinfo(pyodbc.SQL_CONNECTION_DEAD)}")
#             logger.info(f"[DEBUG] 認証方式: Microsoft Entra ID (DefaultAzureCredential)")
#             conn.close()
#         except Exception as conn_error:
#             logger.warning(f"[DEBUG] DB接続情報取得エラー: {str(conn_error)}")
#             logger.info(f"[DEBUG] 接続文字列（サーバー名）: tcp:w-paas-salesanalyzer-sqlserver.database.windows.net")
#             logger.info(f"[DEBUG] データベース名: w-paas-salesanalyzer-sql")
#             logger.info(f"[DEBUG] 認証方式: Microsoft Entra ID (DefaultAzureCredential)")

#         query = """
#             SELECT m.meeting_id, m.user_id, m.client_contact_name, m.client_company_name, 
#                    m.meeting_datetime, m.duration_seconds, m.status, m.transcript_text, 
#                    m.file_name, m.file_size, m.error_message, u.user_name 
#             FROM dbo.Meetings m 
#             JOIN dbo.Users u ON m.user_id = u.user_id
#             WHERE u.manager_id = ?
#             ORDER BY m.meeting_datetime DESC
#         """
#         meetings = execute_query(query, (int(manager_id),))

#         return func.HttpResponse(
#             json.dumps(meetings, ensure_ascii=False),
#             mimetype="application/json",
#             status_code=200,
#             headers={
#                 "Access-Control-Allow-Origin": "https://audio-sales-analyzer.vercel.app",
#                 "Access-Control-Allow-Credentials": "true",
#                 "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
#                 "Access-Control-Allow-Headers": "Content-Type"
#             }
#         )

#     except Exception as e:
#         logger.error(f"Get members meetings error: {str(e)}")
#         logger.error(f"Error details: {traceback.format_exc()}")
#         return func.HttpResponse(
#             json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
#             mimetype="application/json",
#             status_code=500,
#             headers={
#                 "Access-Control-Allow-Origin": "https://audio-sales-analyzer.vercel.app",
#                 "Access-Control-Allow-Credentials": "true",
#                 "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
#                 "Access-Control-Allow-Headers": "Content-Type"
#             }
#         ) 