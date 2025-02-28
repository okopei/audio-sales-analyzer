import logging
import json
from datetime import datetime
import azure.functions as func
from ..common.http import add_cors_headers, handle_options_request
from .models import Meeting

def save_meeting_handler(req: func.HttpRequest, meetings_out: func.Out[func.SqlRow], last_meeting: func.SqlRowList) -> func.HttpResponse:
    """会議保存ハンドラー"""
    logging.info('Save meeting function processed a request.')
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    headers = add_cors_headers()
    
    try:
        # JSONデータを取得
        req_body = req.get_json()
        logging.info(f"Received data: {req_body}")
        
        # 必須フィールドの確認
        year = req_body.get('year')
        month = req_body.get('month')
        day = req_body.get('day')
        hour = req_body.get('hour')
        company_name = req_body.get('companyName')
        
        # オプションフィールド
        contact_person = req_body.get('contactPerson', '')
        industry = req_body.get('industry', '')
        scale = req_body.get('scale', '')
        meeting_goal = req_body.get('meetingGoal', '')
        
    except ValueError as e:
        logging.error(f"JSON parsing error: {str(e)}")
        return func.HttpResponse(
            "Invalid JSON data",
            status_code=400,
            headers=headers
        )

    if not all([year, month, day, hour, company_name]):
        missing_fields = []
        if not year: missing_fields.append("year")
        if not month: missing_fields.append("month")
        if not day: missing_fields.append("day")
        if not hour: missing_fields.append("hour")
        if not company_name: missing_fields.append("companyName")
        
        logging.warning(f"Missing required fields: {', '.join(missing_fields)}")
        return func.HttpResponse(
            f"Missing required fields: {', '.join(missing_fields)}",
            status_code=400,
            headers=headers
        )
    
    try:
        # 日付文字列を作成
        meeting_date_str = f"{year}-{month}-{day}T{hour}:00:00"
        
        # タイトルを会社名から生成
        title = f"{company_name}との商談"
        
        # 会議モデルを作成
        meeting = Meeting(
            user_id=2,
            title=title,
            meeting_datetime=meeting_date_str
        )
        
        # 最後の会議IDを取得
        last_meeting_id = 0
        for row in last_meeting:
            last_meeting_id = row["meeting_id"]
            break
        
        logging.info(f"Last meeting ID before insert: {last_meeting_id}")
        
        # SQLバインディングを使用してデータを挿入
        meetings_out.set(func.SqlRow(meeting.to_dict()))
        
        # 新しい会議IDは最後の会議ID + 1と推定
        new_meeting_id = last_meeting_id + 1
        
        # 成功レスポンス
        response_data = {
            "meetingId": new_meeting_id,
            "message": f"Meeting with '{company_name}' created successfully."
        }
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=201,
            mimetype="application/json",
            headers=headers
        )
    except Exception as e:
        logging.error(f"Error creating meeting: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        
        return func.HttpResponse(
            json.dumps({"error": f"Error creating meeting: {str(e)}"}),
            status_code=500,
            mimetype="application/json",
            headers=headers
        )