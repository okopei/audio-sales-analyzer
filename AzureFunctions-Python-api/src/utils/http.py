import json
import os
import azure.functions as func
import logging

def get_cors_headers():
    """
    CORS対応のためのヘッダーを返す
    """
    return {
        # TODO: 本番環境デプロイ時に環境変数に変更
        "Access-Control-Allow-Origin": os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000"),
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS, PUT, DELETE",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }

def handle_options_request():
    """
    OPTIONSリクエストに対するレスポンスを返す
    """
    return func.HttpResponse(
        status_code=204,
        headers=get_cors_headers()
    )

def create_json_response(data, status_code=200):
    """
    JSONレスポンスを作成する
    """
    return func.HttpResponse(
        body=json.dumps(data),
        status_code=status_code,
        mimetype="application/json",
        headers=get_cors_headers()
    )

def create_error_response(message, status_code=400):
    """
    エラーレスポンスを作成する
    """
    return create_json_response({"error": message}, status_code)

def parse_json_request(req):
    """
    リクエストからJSONデータを取得する
    """
    try:
        return req.get_json()
    except ValueError:
        logging.warning("Invalid JSON data in request")
        return None

def log_request(req, function_name):
    """
    リクエストの基本情報をログに記録する
    """
    logging.info(f"{function_name} - {req.method} request received")
    
    # 詳細ログは開発環境でのみ出力
    if os.environ.get("FUNCTIONS_ENVIRONMENT") == "Development":
        logging.debug(f"URL: {req.url}")
    
    # 機密情報は記録しない
    # ヘッダーやボディの詳細ログは削除 