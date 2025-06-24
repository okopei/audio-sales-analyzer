"""
HealthCheck関数
APIサーバーの稼働状態を確認するためのヘルスチェックエンドポイント
"""

import azure.functions as func
import logging

# FunctionAppインスタンスの生成（1回のみ）
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# ロガーの設定
logger = logging.getLogger(__name__)

@app.function_name(name="HealthCheck")
@app.route(route="health", methods=["GET", "OPTIONS"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """APIサーバーの稼働状態を確認するためのヘルスチェックエンドポイント"""
    logger.info("Health check endpoint called")
    
    if req.method == "OPTIONS":
        # CORS プリフライトリクエスト処理
        return func.HttpResponse(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )
    
    # ヘルスチェックレスポンス
    return func.HttpResponse(
        body='{"status":"ok","message":"API server is running"}',
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    ) 