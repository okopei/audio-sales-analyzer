import logging
import json
import traceback
import azure.functions as func
from datetime import datetime, UTC
import re
import os
from azure.storage.blob import BlobServiceClient

from ..utils.http import get_cors_headers, handle_options_request, create_json_response, create_error_response, parse_json_request, log_request
from ..models.meeting import Meeting
from ..utils.db import execute_query, get_current_time

def get_meetings(req: func.HttpRequest) -> func.HttpResponse:
    """
    会議一覧を取得する
    """
    log_request(req, "GetMeetings")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    try:
        # 会議一覧を取得
        query = """
            SELECT meeting_id, user_id, client_contact_name, client_company_name, 
                   meeting_datetime, duration_seconds, status, transcript_text, 
                   file_name, file_size, error_message 
            FROM dbo.Meetings
        """
        meetings = execute_query(query)
        
        return create_json_response({"meetings": meetings})
        
    except Exception as e:
        logging.error(f"Error retrieving meetings: {str(e)}")
        return create_error_response(f"Internal server error: {str(e)}", 500)

def get_members_meetings(req: func.HttpRequest) -> func.HttpResponse:
    """
    メンバーの会議一覧を取得する
    """
    log_request(req, "GetMembersMeetings")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    try:
        # メンバーの会議一覧を取得
        query = """
            SELECT m.meeting_id, m.user_id, m.client_contact_name, m.client_company_name, 
                   m.meeting_datetime, m.duration_seconds, m.status, m.transcript_text, 
                   m.file_name, m.file_size, m.error_message, u.user_name 
            FROM dbo.Meetings m 
            JOIN dbo.Users u ON m.user_id = u.user_id
        """
        meetings = execute_query(query)
        
        return create_json_response({"meetings": meetings})
        
    except Exception as e:
        logging.error(f"Error retrieving members meetings: {str(e)}")
        return create_error_response(f"Internal server error: {str(e)}", 500)

def save_basic_info(req: func.HttpRequest) -> func.HttpResponse:
    """
    会議の基本情報を保存する
    """
    log_request(req, "SaveBasicInfo")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    try:
        # リクエストデータの取得
        req_body = parse_json_request(req)
        if not req_body:
            return create_error_response("Invalid JSON data", 400)
        
        # 必須フィールドの確認
        required_fields = ["user_id", "client_contact_name", "client_company_name", "meeting_datetime"]
        for field in required_fields:
            if field not in req_body:
                return create_error_response(f"Missing required field: {field}", 400)
        
        # 現在時刻
        now = get_current_time()
        
        # 新しい会議IDを生成
        query = "SELECT TOP 1 meeting_id FROM dbo.Meetings ORDER BY meeting_id DESC"
        last_meeting = execute_query(query)
        new_meeting_id = 1
        if last_meeting:
            new_meeting_id = int(last_meeting[0]['meeting_id']) + 1
        
        # 会議情報をデータベースに挿入
        insert_query = """
            INSERT INTO dbo.Meetings (
                meeting_id, user_id, client_contact_name, client_company_name,
                meeting_datetime, duration_seconds, status, transcript_text,
                file_name, file_size, error_message, inserted_datetime, updated_datetime
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        execute_query(insert_query, {
            'meeting_id': new_meeting_id,
            'user_id': req_body['user_id'],
            'client_contact_name': req_body['client_contact_name'],
            'client_company_name': req_body['client_company_name'],
            'meeting_datetime': req_body['meeting_datetime'],
            'duration_seconds': req_body.get('duration_seconds', 0),
            'status': req_body.get('status', 'pending'),
            'transcript_text': req_body.get('transcript_text', ''),
            'file_name': req_body.get('file_name', ''),
            'file_size': req_body.get('file_size', 0),
            'error_message': req_body.get('error_message', ''),
            'inserted_datetime': now,
            'updated_datetime': now
        })
        
        logging.info(f"Basic info saved for meeting ID: {new_meeting_id}")
        
        return create_json_response({
            "message": "会議の基本情報が保存されました",
            "meeting_id": new_meeting_id
        }, 201)
        
    except Exception as e:
        logging.error(f"Error saving basic info: {str(e)}")
        return create_error_response(f"Internal server error: {str(e)}", 500)

def get_basic_info(req: func.HttpRequest) -> func.HttpResponse:
    """
    会議の基本情報を取得する
    """
    log_request(req, "GetBasicInfo")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    try:
        # 会議IDを取得
        meeting_id = req.route_params.get('meeting_id')
        if not meeting_id:
            return create_error_response("meeting_id is required", 400)
        
        # 会議情報を取得
        query = """
            SELECT meeting_id, user_id, client_contact_name, client_company_name,
                   meeting_datetime, duration_seconds, status, transcript_text,
                   file_name, file_size, error_message
            FROM dbo.Meetings
            WHERE meeting_id = ?
        """
        meetings = execute_query(query, [meeting_id])
        
        if not meetings:
            return create_error_response("Meeting not found", 404)
        
        return create_json_response({"meeting": meetings[0]})
        
    except Exception as e:
        logging.error(f"Error retrieving basic info: {str(e)}")
        return create_error_response(f"Internal server error: {str(e)}", 500)