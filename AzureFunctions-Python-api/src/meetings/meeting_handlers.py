import logging
import json
import traceback
import azure.functions as func
from datetime import datetime, UTC
import re

from ..utils.http import get_cors_headers, handle_options_request, create_json_response, create_error_response, parse_json_request, log_request
from ..utils.db import get_db_connection, execute_query, get_current_time
from ..models.meeting import Meeting

def get_meetings(req: func.HttpRequest, meeting_rows: func.SqlRowList) -> func.HttpResponse:
    """
    会議一覧を取得する
    """
    log_request(req, "GetMeetings")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    user_id = None
    manager_id = None
    
    # クエリパラメータからuser_idを取得
    if 'user_id' in req.params:
        user_id = req.params.get('user_id')
    
    # クエリパラメータからmanager_idを取得
    if 'manager_id' in req.params:
        manager_id = req.params.get('manager_id')
    
    # ユーザーIDまたはマネージャーIDが存在する場合に処理を続行
    if user_id or manager_id:
        rows = []
        
        for row in meeting_rows:
            # user_idフィルターが存在する場合は、該当するレコードのみを追加
            if user_id and str(row['user_id']) == user_id:
                rows.append(dict(row))
            
            # manager_idフィルターが存在する場合、今後のロジックで処理する予定（現時点では未実装）
            elif manager_id:
                # TODO: manager_idに基づくフィルタリングロジックを実装する
                pass
        
        return create_json_response(rows)
    
    # user_idもmanager_idも指定されていない場合はすべての会議を返す
    else:
        rows = [dict(row) for row in meeting_rows]
        return create_json_response(rows)

def get_members_meetings(req: func.HttpRequest, members_rows: func.SqlRowList, meeting_rows: func.SqlRowList) -> func.HttpResponse:
    """
    マネージャーIDに基づいてメンバーの会議一覧を取得する
    """
    log_request(req, "GetMembersMeetings")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    # クエリパラメータからmanager_idを取得
    manager_id = req.params.get('manager_id')
    if not manager_id:
        return create_error_response("Manager ID is required", 400)
    
    # manager_idに基づいてメンバーのuser_idを取得
    member_user_ids = []
    for row in members_rows:
        if str(row['manager_id']) == manager_id:
            member_user_ids.append(str(row['user_id']))
    
    # 特定のマネージャーのメンバーの会議を取得
    meetings = []
    for row in meeting_rows:
        # user_idをstr型に変換して比較
        if str(row['user_id']) in member_user_ids:
            meetings.append(dict(row))
    
    return create_json_response(meetings)

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
            
            # ワーニングからインフォに変更し、機密情報を含まないようにする
            logging.info("Missing required fields detected")
            return create_error_response(f"Missing required fields: {', '.join(missing_fields)}", 400)
        
        # 日付文字列を作成
        meeting_date_str = f"{year}-{month}-{day}T{hour}:00:00"
        
        # 現在の時刻を取得
        now = get_current_time()
        
        # SQLバインディングを使用してデータを挿入
        basicInfo_out.set(func.SqlRow({
            "user_id": user_id,
            "meeting_datetime": meeting_date_str,
            "client_company_name": client_company_name,  # フロントエンドから送信された企業名
            "client_contact_name": client_contact_name,  # フロントエンドから送信された顧客名
            "industry_type": industry if industry else None,
            "company_scale": scale if scale else None,
            "sales_goal": meeting_goal if meeting_goal else None,
            "inserted_datetime": now,
            "updated_datetime": now
        }))
        
        # 成功レスポンス - 検索用の情報を含める
        response_data = {
            "success": True,
            "message": f"BasicInfo for meeting with '{company_name}' saved successfully.",
            "search_info": {
                "user_id": user_id,
                "client_company_name": client_company_name,
                "client_contact_name": client_contact_name,
                "meeting_datetime": meeting_date_str
            }
        }
        
        return create_json_response(response_data, 201)
    except Exception as e:
        logging.error(f"Error creating basic info: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        
        return create_error_response(f"Error creating basic info: {str(e)}", 500)

def normalize_datetime_str(datetime_str):
    """
    日付文字列を正規化して、フォーマットの違いを無視して比較できるようにする
    スペース、'T'、ミリ秒、タイムゾーン情報を除去し、YYYY-MM-DDThh:mm:ss形式に統一
    """
    if not datetime_str:
        return ""
    
    # 正規表現を使って日付部分と時間部分を抽出
    # YYYY-MM-DD と hh:mm:ss の部分を取り出す
    match = re.match(r'(\d{4}-\d{2}-\d{2})[T\s]?(\d{2}:\d{2}:\d{2})', datetime_str)
    if match:
        date_part, time_part = match.groups()
        return f"{date_part}T{time_part}"
    
    return datetime_str  # マッチしない場合は元の文字列を返す

def get_basic_info(req: func.HttpRequest, basic_info_query: func.SqlRowList, search_mode=False) -> func.HttpResponse:
    """
    会議の基本情報を取得する
    - meeting_idで検索する方法と
    - user_id + client_company_name + client_contact_name + meeting_datetimeの組み合わせで検索する方法を提供
    """
    log_request(req, "GetBasicInfo")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    try:
        # 検索モードの場合はルートパラメータがない
        if search_mode:
            meeting_id = 'search'
        else:
            # ルートから会議IDを取得
            meeting_id = req.route_params.get('meeting_id')
            
        # クエリパラメータからユーザーIDを取得
        user_id = req.params.get('user_id')
        
        # 追加の検索パラメータを取得
        client_company_name = req.params.get('company_name')
        client_contact_name = req.params.get('contact_name')
        meeting_datetime = req.params.get('meeting_datetime')
        
        # 検索条件の日時を正規化
        normalized_search_datetime = normalize_datetime_str(meeting_datetime) if meeting_datetime else None
        
        # 検索方法を判断（meeting_idが'search'の場合、詳細検索を行う）
        is_detail_search = meeting_id == 'search' or search_mode
        
        if not is_detail_search and not meeting_id:
            return create_error_response("meeting_id is required", 400)
            
        if is_detail_search and not user_id:
            return create_error_response("user_id is required for detail search", 400)
            
        # パラメータを数値に変換
        if not is_detail_search:
            try:
                meeting_id = int(meeting_id)
            except ValueError:
                return create_error_response("meeting_id must be an integer", 400)
            
        if user_id:
            try:
                user_id = int(user_id)
            except ValueError:
                return create_error_response("user_id must be an integer", 400)
        
        # 基本情報の検索
        basic_info = None
        all_records = []
        
        # すべてのレコードを取得
        for row in basic_info_query:
            row_dict = dict(row)
            all_records.append(row_dict)
        
        # IDによる検索（標準モード）またはdetail searchモードで検索
        for row_dict in all_records:
            row_meeting_id = row_dict.get("meeting_id")
            row_user_id = row_dict.get("user_id")
            
            if not is_detail_search:
                # ID検索モード
                if row_meeting_id == meeting_id:
                    # user_idが指定されている場合は、それも一致するか確認
                    if not user_id or row_user_id == user_id:
                        basic_info = row_dict
                        break
            else:
                # 詳細検索モード (user_id + その他の条件)
                if row_user_id == user_id:
                    # 会社名が指定され、一致するか確認
                    if client_company_name and row_dict.get("client_company_name", "") != client_company_name:
                        continue
                        
                    # 担当者名が指定され、一致するか確認
                    if client_contact_name and row_dict.get("client_contact_name", "") != client_contact_name:
                        continue
                        
                    # 会議日時が指定され、一致するか確認 (正規化した日時で比較)
                    if normalized_search_datetime:
                        row_datetime = row_dict.get("meeting_datetime", "")
                        row_normalized_datetime = normalize_datetime_str(str(row_datetime))
                        
                        if row_normalized_datetime != normalized_search_datetime:
                            continue
                        
                    # すべての条件を満たした場合
                    basic_info = row_dict
                    break
        
        # 日付データをシリアライズ可能な形式に変換
        if basic_info:
            for key, value in basic_info.items():
                if isinstance(value, datetime):
                    basic_info[key] = value.isoformat()
            
            return create_json_response({
                "basic_info": basic_info, 
                "found": True, 
                "meeting_id": basic_info.get('meeting_id')
            })
        else:
            # 詳細な検索パラメータを含まないシンプルなレスポンス
            return create_json_response({
                "message": "No basic info found for the specified criteria",
                "found": False
            }, 404)
    except Exception as e:
        logging.error(f"Error retrieving basic info: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        return create_error_response(f"Internal server error: {str(e)}", 500) 