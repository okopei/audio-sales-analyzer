"""
TestDbConnection関数
データベース接続をテストするエンドポイント
"""

import azure.functions as func
import logging
import json
import traceback
import sys
import os

# パスを追加してutilsモジュールをインポート可能にする
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.db_utils import test_db_connection

# FunctionAppインスタンスの生成（1回のみ）
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# ロガーの設定
logger = logging.getLogger(__name__)

@app.function_name(name="TestDbConnection")
@app.route(route="test/db-connection", methods=["GET", "OPTIONS"])
def test_db_connection_func(req: func.HttpRequest) -> func.HttpResponse:
    """データベース接続をテストするエンドポイント"""
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        # 接続テストを実行
        success = test_db_connection()
        
        if success:
            response = {
                "success": True,
                "message": "データベース接続テストが成功しました"
            }
            status_code = 200
        else:
            response = {
                "success": False,
                "message": "データベース接続テストが失敗しました"
            }
            status_code = 500

        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=status_code,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Database connection test error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({
                "success": False,
                "message": f"データベース接続テスト中にエラーが発生しました: {str(e)}"
            }, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        ) 