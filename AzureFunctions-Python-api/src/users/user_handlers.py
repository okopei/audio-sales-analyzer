import logging
import azure.functions as func
from ..utils.http import get_cors_headers, handle_options_request, create_json_response, create_error_response, log_request
from ..utils.db import execute_query

logger = logging.getLogger(__name__)

def get_users(req: func.HttpRequest) -> func.HttpResponse:
    """
    ユーザー一覧を取得する
    """
    log_request(req, "GetUsers")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    try:
        # ユーザー一覧を取得
        query = """
            SELECT user_id, user_name, email
            FROM dbo.Users
            WHERE deleted_datetime IS NULL
            ORDER BY user_name
        """
        users = execute_query(query)
        
        return create_json_response(users)
        
    except Exception as e:
        logging.error(f"Error retrieving users: {str(e)}")
        return create_error_response(f"Internal server error: {str(e)}", 500) 