"""
GetConversationSegments関数
会話セグメント取得エンドポイント
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

@app.function_name(name="GetConversationSegments")
@app.route(route="conversation/segments/{meeting_id}", methods=["GET", "OPTIONS"])
def get_conversation_segments(req: func.HttpRequest) -> func.HttpResponse:
    """会話セグメント取得エンドポイント"""
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
            
        meeting_id = req.route_params.get('meeting_id')
        
        query = """
            SELECT s.segment_id, s.user_id, s.speaker_id, s.meeting_id, s.content, 
                   s.file_name, s.file_path, s.file_size, s.duration_seconds, s.status, 
                   s.inserted_datetime, s.updated_datetime, s.start_time, s.end_time, 
                   sp.speaker_name, sp.speaker_role 
            FROM dbo.ConversationSegments s 
            LEFT JOIN dbo.Speakers sp ON s.speaker_id = sp.speaker_id 
            WHERE s.deleted_datetime IS NULL AND s.meeting_id = ?
        """
        segments = execute_query(query, (meeting_id,))
        
        # 日付時刻の適切な変換
        for segment in segments:
            if hasattr(segment['inserted_datetime'], 'isoformat'):
                segment['inserted_datetime'] = segment['inserted_datetime'].isoformat()
            elif segment['inserted_datetime'] is not None and not isinstance(segment['inserted_datetime'], str):
                segment['inserted_datetime'] = str(segment['inserted_datetime'])
            
            if hasattr(segment['updated_datetime'], 'isoformat'):
                segment['updated_datetime'] = segment['updated_datetime'].isoformat()
            elif segment['updated_datetime'] is not None and not isinstance(segment['updated_datetime'], str):
                segment['updated_datetime'] = str(segment['updated_datetime'])
        
        response = {
            "success": True,
            "message": f"会話セグメントを取得しました（meeting_id: {meeting_id}）",
            "segments": segments
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )
    except Exception as e:
        logger.error(f"Get conversation segments error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )
 