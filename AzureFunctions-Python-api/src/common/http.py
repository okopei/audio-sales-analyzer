def add_cors_headers(headers=None):
    """CORSヘッダーを追加する"""
    if headers is None:
        headers = {}
    
    headers.update({
        "Access-Control-Allow-Origin": "http://localhost:3000",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Credentials": "true"
    })
    
    return headers

def handle_options_request():
    """OPTIONSリクエストを処理する"""
    from azure.functions import HttpResponse
    return HttpResponse(status_code=204, headers=add_cors_headers())