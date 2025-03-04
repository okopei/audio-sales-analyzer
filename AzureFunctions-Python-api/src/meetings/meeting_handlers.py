import logging
import json
import traceback
import azure.functions as func
from datetime import datetime, UTC

from ..utils.http import get_cors_headers, handle_options_request, create_json_response, create_error_response, parse_json_request, log_request
from ..utils.db import get_db_connection, execute_query, get_current_time
from ..models.meeting import Meeting

def get_meetings(req: func.HttpRequest, meetings_query: func.SqlRowList) -> func.HttpResponse:
    """
    ユーザーの会議一覧を取得する
    """
    log_request(req, "GetMeetings")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    try:
        user_id = req.params.get('user_id')
        if not user_id:
            return create_error_response("user_id is required", 400)
        
        # デバッグ用に、全てのミーティングデータをログに出力
        meetings_list = list(meetings_query)
        logging.info(f"Total meetings retrieved from DB: {len(meetings_list)}")
        
        # ユーザーIDフィルタリング
        meetings = []
        for row in meetings_list:
            row_dict = dict(row)
            row_user_id = row_dict.get("user_id")
            
            # ユーザーIDの比較
            try:
                if str(row_user_id) == str(user_id):
                    # Meetingモデルを使用してデータを整形
                    meeting = Meeting.from_dict(row_dict)
                    meetings.append(meeting.to_dict())
            except (ValueError, TypeError) as ve:
                logging.error(f"Error converting user_id: {str(ve)}")
        
        # 最終的なミーティング数をログに出力
        logging.info(f"Filtered meetings count: {len(meetings)}")
        
        if meetings:
            return create_json_response({"meetings": meetings})
        else:
            return create_json_response({
                "message": "No meetings found for the specified user",
                "debug": {
                    "user_id_requested": user_id,
                    "total_records": len(meetings_list)
                }
            })
    except Exception as e:
        logging.error(f"Error retrieving meetings: {str(e)}")
        return create_error_response(f"Internal server error: {str(e)}", 500)

def get_members_meetings(req: func.HttpRequest, users_query: func.SqlRowList, meetings_query: func.SqlRowList) -> func.HttpResponse:
    """
    マネージャーのチームメンバーの会議一覧を取得する
    """
    log_request(req, "GetMembersMeetings")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    try:
        manager_id = req.params.get('manager_id')
        show_all = req.params.get('show_all', '').lower() == 'true'
        
        logging.info(f"[DEBUG] Received manager_id: {manager_id}, show_all: {show_all}")
        
        if not manager_id:
            return create_error_response("manager_id is required", 400)
        
        # マネージャー名を取得
        manager_name = None
        for user in users_query:
            if str(user.get("user_id")) == manager_id:
                manager_name = user.get("user_name")
                break
        
        logging.info(f"[DEBUG] Found manager_name: {manager_name}")
        
        if not manager_name:
            return create_error_response("Manager not found", 404)
        
        # マネージャーが管理するチームメンバーのIDを取得
        team_member_ids = []
        for user in users_query:
            user_dict = dict(user)
            if show_all or user_dict.get("manager_name") == manager_name:
                user_id = str(user_dict.get("user_id"))
                team_member_ids.append(user_id)
                logging.info(f"[DEBUG] Found team member - user_id: {user_id}, user_name: {user_dict.get('user_name')}, manager_name: {user_dict.get('manager_name')}")
        
        logging.info(f"[DEBUG] Team member IDs: {team_member_ids}")
        
        # すべてのユーザーのmanager_name情報をログに出力
        logging.info("[DEBUG] All users manager_name info:")
        for user in users_query:
            user_dict = dict(user)
            logging.info(f"[DEBUG] user_id: {user_dict.get('user_id')}, user_name: {user_dict.get('user_name')}, manager_name: {user_dict.get('manager_name')}")
        
        # チームメンバーのミーティングを取得
        meetings = []
        meeting_count = 0
        for row in meetings_query:
            try:
                row_dict = dict(row)
                row_user_id = str(row_dict.get("user_id"))
                
                if row_user_id in team_member_ids:
                    # Meetingモデルを使用してデータを整形
                    meeting = Meeting.from_dict(row_dict)
                    meetings.append(meeting.to_dict())
                    meeting_count += 1
                    logging.info(f"[DEBUG] Found meeting for team member - meeting_id: {row_dict.get('meeting_id')}, user_id: {row_user_id}, title: {row_dict.get('title')}")
            except Exception as row_error:
                logging.error(f"Error processing row: {str(row_error)}")
        
        logging.info(f"[DEBUG] Total meetings found: {meeting_count}")
        
        if meetings:
            return create_json_response({"meetings": meetings})
        else:
            logging.info(f"[DEBUG] No meetings found for team members with IDs: {team_member_ids}")
            return create_json_response({"message": "No meetings found for the team members"})
    except Exception as e:
        logging.error(f"Error retrieving team meetings: {str(e)}")
        return create_error_response(f"Internal server error: {str(e)}", 500)

def save_meeting(req: func.HttpRequest, meetings_out: func.Out[func.SqlRow], last_meeting: func.SqlRowList) -> func.HttpResponse:
    """
    会議情報を保存する
    """
    log_request(req, "SaveMeeting")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    try:
        # JSONデータを取得
        req_body = parse_json_request(req)
        if not req_body:
            return create_error_response("Invalid JSON data", 400)
        
        logging.info(f"Received data: {req_body}")
        
        # 必須フィールドの確認
        year = req_body.get('year')
        month = req_body.get('month')
        day = req_body.get('day')
        hour = req_body.get('hour')
        company_name = req_body.get('companyName')
        user_id = req_body.get('userId')
        
        # オプションフィールド
        contact_person = req_body.get('contactPerson', '')
        industry = req_body.get('industry', '')
        scale = req_body.get('scale', '')
        meeting_goal = req_body.get('meetingGoal', '')
        
        if not all([year, month, day, hour, company_name, user_id]):
            missing_fields = []
            if not year: missing_fields.append("year")
            if not month: missing_fields.append("month")
            if not day: missing_fields.append("day")
            if not hour: missing_fields.append("hour")
            if not company_name: missing_fields.append("companyName")
            if not user_id: missing_fields.append("userId")
            
            logging.warning(f"Missing required fields: {', '.join(missing_fields)}")
            return create_error_response(f"Missing required fields: {', '.join(missing_fields)}", 400)
        
        # 日付文字列を作成
        meeting_date_str = f"{year}-{month}-{day}T{hour}:00:00"
        
        # タイトルを会社名から生成
        title = f"{company_name}との商談"
        
        # 会議モデルを作成
        meeting = Meeting(
            user_id=user_id,
            title=title,
            meeting_datetime=meeting_date_str,
            status="pending",
            inserted_datetime=get_current_time(),
            updated_datetime=get_current_time()
        )
        
        # 最後の会議IDを取得
        last_meeting_id = 0
        for row in last_meeting:
            last_meeting_id = row["meeting_id"]
            break
        
        logging.info(f"Last meeting ID before insert: {last_meeting_id}")
        
        # SQLバインディングを使用してデータを挿入
        meetings_out.set(func.SqlRow(meeting.to_sql_row()))
        
        # 新しい会議IDは最後の会議ID + 1と推定
        new_meeting_id = last_meeting_id + 1
        
        # 成功レスポンス
        response_data = {
            "meetingId": new_meeting_id,
            "message": f"Meeting with '{company_name}' created successfully."
        }
        
        return create_json_response(response_data, 201)
    except Exception as e:
        logging.error(f"Error creating meeting: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        
        return create_error_response(f"Error creating meeting: {str(e)}", 500)

def save_basic_info(req: func.HttpRequest, basicInfo_out: func.Out[func.SqlRow], last_basicInfo: func.SqlRowList) -> func.HttpResponse:
    """
    基本情報を保存する
    """
    log_request(req, "SaveBasicInfo")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    try:
        # JSONデータを取得
        req_body = parse_json_request(req)
        if not req_body:
            return create_error_response("Invalid JSON data", 400)
        
        logging.info(f"Received data: {req_body}")
        
        # 必須フィールドの確認
        year = req_body.get('year')
        month = req_body.get('month')
        day = req_body.get('day')
        hour = req_body.get('hour')
        company_name = req_body.get('companyName')  # 顧客名（担当者名）- フロントエンドの互換性のために残す
        user_id = req_body.get('userId')
        
        # フロントエンドから送信されるフィールド
        client_company_name = req_body.get('client_company_name', '')  # 企業名
        client_contact_name = req_body.get('client_contact_name', '')  # 顧客名
        
        # オプションフィールド
        industry = req_body.get('industry', '')
        scale = req_body.get('scale', '')
        meeting_goal = req_body.get('meeting_goal', '')
        
        if not all([year, month, day, hour, company_name, user_id]):
            missing_fields = []
            if not year: missing_fields.append("year")
            if not month: missing_fields.append("month")
            if not day: missing_fields.append("day")
            if not hour: missing_fields.append("hour")
            if not company_name: missing_fields.append("companyName")
            if not user_id: missing_fields.append("userId")
            
            logging.warning(f"Missing required fields: {', '.join(missing_fields)}")
            return create_error_response(f"Missing required fields: {', '.join(missing_fields)}", 400)
        
        # 日付文字列を作成
        meeting_date_str = f"{year}-{month}-{day}T{hour}:00:00"
        
        # 最後の基本情報IDを取得
        last_basic_info_id = 0
        for row in last_basicInfo:
            last_basic_info_id = row["meeting_id"]
            break
        
        logging.info(f"Last basic info ID before insert: {last_basic_info_id}")
        
        # 新しい基本情報ID
        new_basic_info_id = last_basic_info_id + 1
        
        # 現在の時刻を取得
        now = get_current_time()
        
        # SQLバインディングを使用してデータを挿入
        basicInfo_out.set(func.SqlRow({
            "user_id": user_id,
            "meeting_id": new_basic_info_id,
            "meeting_datetime": meeting_date_str,
            "client_company_name": client_company_name,  # フロントエンドから送信された企業名
            "client_contact_name": client_contact_name,  # フロントエンドから送信された顧客名
            "industry_type": industry if industry else None,
            "company_scale": scale if scale else None,
            "sales_goal": meeting_goal if meeting_goal else None,
            "inserted_datetime": now,
            "updated_datetime": now
        }))
        
        # 成功レスポンス
        response_data = {
            "meetingId": new_basic_info_id,
            "message": f"BasicInfo for meeting with '{company_name}' created successfully."
        }
        
        return create_json_response(response_data, 201)
    except Exception as e:
        logging.error(f"Error creating basic info: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        
        return create_error_response(f"Error creating basic info: {str(e)}", 500) 