"""
SaveBasicInfo関数
会議の基本情報を保存するエンドポイント
"""

import azure.functions as func
import logging
import json
import traceback
import sys
import os

# パスを追加してsrcモジュールをインポート可能にする
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.meetings import save_basic_info

# FunctionAppインスタンスの生成（1回のみ）
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# ロガーの設定
logger = logging.getLogger(__name__)

@app.function_name(name="SaveBasicInfo")
@app.route(route="basicinfo", auth_level=func.AuthLevel.ANONYMOUS)
def save_basic_info_func(req: func.HttpRequest) -> func.HttpResponse:
    """会議の基本情報を保存する"""
    try:
        # OPTIONSリクエスト処理
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        # reqオブジェクトをそのまま渡す
        return save_basic_info(req)
        
    except ValueError as e:
        logger.error(f"Invalid request data: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Invalid request data: {str(e)}"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Save basic info error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        ) 