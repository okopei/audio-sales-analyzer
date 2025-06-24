"""
GetFeedbackByMeetingId関数
会議IDによるフィードバック取得エンドポイント
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

# FunctionAppインスタンスの生成（1回のみ）
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# ロガーの設定
logger = logging.getLogger(__name__)

@app.function_name(name="GetFeedbackByMeetingId")
@app.route(route="feedback/{meeting_id}", methods=["GET", "OPTIONS"])
def get_feedback_by_meeting_id_func(req: func.HttpRequest) -> func.HttpResponse:
    """会議IDによるフィードバック取得エンドポイント"""
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

        meeting_id = req.route_params.get('meeting_id')
        if not meeting_id:
            return func.HttpResponse(
                json.dumps({"error": "Meeting ID is required"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                }
            )

        query = """
            SELECT f.feedback_id, f.meeting_id, f.user_id, f.feedback_text, 
                   f.inserted_datetime, f.updated_datetime, u.user_name 
            FROM dbo.Feedback f 
            JOIN dbo.Users u ON f.user_id = u.user_id 
            WHERE f.meeting_id = ?
        """
        feedback_list = execute_query(query, (meeting_id,))

        return func.HttpResponse(
            json.dumps(feedback_list, ensure_ascii=False),
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
        logger.error(f"Get feedback by meeting ID error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
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