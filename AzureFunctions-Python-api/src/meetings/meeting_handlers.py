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
from ..utils.db import get_db_connection, execute_query, get_current_time

logger = logging.getLogger(__name__)

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
                   file_name, file_size, error_message, title, file_path
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
    クエリパラメータ:
    - user_id: ユーザーIDでフィルタリング（オプション）
    - from_date: 開始日でフィルタリング（オプション）
    - to_date: 終了日でフィルタリング（オプション）
    """
    log_request(req, "GetMembersMeetings")
    
    # OPTIONSリクエスト処理
    if req.method == "OPTIONS":
        return handle_options_request()
    
    try:
        # クエリパラメータの取得と検証
        user_id = req.params.get('user_id')
        from_date = req.params.get('from_date')
        to_date = req.params.get('to_date')

        # 日付形式の検証
        if from_date:
            try:
                datetime.strptime(from_date, '%Y-%m-%d')
            except ValueError:
                return create_error_response("Invalid from_date format. Use YYYY-MM-DD", 400)
        
        if to_date:
            try:
                datetime.strptime(to_date, '%Y-%m-%d')
            except ValueError:
                return create_error_response("Invalid to_date format. Use YYYY-MM-DD", 400)

        # クエリの構築
        query = """
            SELECT m.meeting_id, m.user_id, m.client_contact_name, m.client_company_name, 
                   m.meeting_datetime, m.duration_seconds, m.status, m.transcript_text, 
                   m.file_name, m.file_size, m.error_message, m.title, m.file_path, u.user_name 
            FROM dbo.Meetings m 
            JOIN dbo.Users u ON m.user_id = u.user_id
            WHERE 1=1
        """
        params = []

        # ユーザーIDでフィルタリング
        if user_id:
            try:
                user_id = int(user_id)
                query += " AND m.user_id = ?"
                params.append(user_id)
            except ValueError:
                return create_error_response("Invalid user_id format", 400)

        # 日付範囲でフィルタリング
        if from_date:
            query += " AND CAST(m.meeting_datetime AS DATE) >= ?"
            params.append(from_date)
        if to_date:
            query += " AND CAST(m.meeting_datetime AS DATE) <= ?"
            params.append(to_date)

        # 日付の降順でソート
        query += " ORDER BY m.meeting_datetime DESC"

        logging.info(f"Executing query: {query}")
        logging.info(f"With parameters: {params}")

        # クエリの実行
        meetings = execute_query(query, params)
        logging.info(f"Found {len(meetings)} meetings")
        
        # ユーザー一覧の取得
        users_query = "SELECT user_id, user_name FROM dbo.Users WHERE deleted_datetime IS NULL"
        users = execute_query(users_query)
        logging.info(f"Found {len(users)} users")
        
        return create_json_response({
            "meetings": meetings,
            "users": users
        })
        
    except Exception as e:
        error_details = traceback.format_exc()
        logging.error(f"Error retrieving members meetings: {str(e)}")
        logging.error(f"Error details: {error_details}")
        return create_error_response({
            "error": "Internal server error",
            "message": str(e),
            "details": error_details
        }, 500)

def save_basic_info(req: func.HttpRequest) -> func.HttpResponse:
    """
    会議の基本情報をBasicInfoテーブルに保存する
    """
    try:
        # リクエストボディを取得
        req_body = req.get_json()
        logging.info(f"リクエストボディ: {req_body}")

        # 必須フィールドの検証
        required_fields = ['user_id', 'client_contact_name', 'client_company_name', 'meeting_datetime']
        for field in required_fields:
            if field not in req_body:
                return func.HttpResponse(
                    f"Missing required field: {field}",
                    status_code=400
                )

        # 日時文字列をdatetimeオブジェクトに変換
        meeting_datetime = datetime.strptime(req_body['meeting_datetime'], '%Y-%m-%d %H:%M:%S')
        
        # オプショナルフィールドの取得（デフォルトは空文字列）
        industry_type = req_body.get('industry', '')
        company_scale = req_body.get('scale', '')
        sales_goal = req_body.get('meeting_goal', '')

        # データベース接続
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # INSERTクエリを実行
            insert_query = """
            INSERT INTO dbo.BasicInfo (
                user_id,
                client_contact_name,
                client_company_name,
                meeting_datetime,
                industry_type,
                company_scale,
                sales_goal,
                inserted_datetime,
                updated_datetime
            )
            OUTPUT INSERTED.meeting_id
            VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())
            """
            
            logging.info(f"実行するINSERTクエリ: {insert_query}")
            logging.info(f"パラメータ: user_id={req_body['user_id']}, client_contact_name={req_body['client_contact_name']}, client_company_name={req_body['client_company_name']}, meeting_datetime={meeting_datetime}, industry_type={industry_type}, company_scale={company_scale}, sales_goal={sales_goal}")
            
            cursor.execute(insert_query, (
                req_body['user_id'],
                req_body['client_contact_name'],
                req_body['client_company_name'],
                meeting_datetime,
                industry_type,
                company_scale,
                sales_goal
            ))
            
            # 新しく挿入されたレコードのIDを取得
            row = cursor.fetchone()
            if not row or row[0] is None:
                raise Exception("会議IDの取得に失敗しました")
            
            new_meeting_id = int(row[0])
            logging.info(f"取得された meeting_id: {new_meeting_id}")

            # トランザクションをコミット
            conn.commit()
            logging.info("トランザクションをコミットしました")

            return func.HttpResponse(
                json.dumps({
                    "message": "会議の基本情報が保存されました",
                    "meeting_id": new_meeting_id
                }),
                mimetype="application/json",
                status_code=201
            )

        except Exception as e:
            conn.rollback()
            logging.error(f"データベース操作エラー: {str(e)}")
            raise
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logging.error(f"エラーが発生しました: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )

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
                   file_name, file_size, error_message, title, file_path
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