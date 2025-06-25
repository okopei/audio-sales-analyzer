import json
import os
import azure.functions as func
import logging

def get_cors_headers():
    """
    CORS対応のためのヘッダーを返す
    """
    return {
        "Access-Control-Allow-Origin": "https://audio-sales-analyzer.vercel.app",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
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