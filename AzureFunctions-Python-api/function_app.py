"""
Audio Sales Analyzer API
Azure Functions アプリケーションのエントリーポイント
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import azure.functions as func
import logging
import json
from typing import Optional, Dict, List, Any
from datetime import datetime, UTC
from azure.functions import AuthLevel, FunctionApp
import traceback
import pyodbc
from azure.identity import DefaultAzureCredential
import struct
from src.models.user import User

# ロガーの設定
logger = logging.getLogger(__name__)

# モジュール構造からのインポート
from src.auth import login, register, get_user_by_id
from src.meetings import get_meetings, get_members_meetings, save_basic_info, get_basic_info

# Azure Functions アプリケーションの初期化
app = FunctionApp(http_auth_level=AuthLevel.ANONYMOUS)

def get_db_connection():
    """
    Entra ID認証を使用してAzure SQL Databaseに接続する
    ODBC Driver 17 for SQL Serverを使用
    """
    try:
        # Microsoft Entra ID認証のトークンを取得
        credential = DefaultAzureCredential()
        token = credential.get_token("https://database.windows.net/.default")
        
        # トークンをバイナリ形式に変換
        token_bytes = bytes(token.token, 'utf-8')
        exptoken = b''.join(bytes((b, 0)) for b in token_bytes)
        access_token = struct.pack('=i', len(exptoken)) + exptoken
        
        # 接続文字列の構築
        conn_str = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:w-paas-salesanalyzer-sqlserver.database.windows.net,1433;"
            f"Database=w-paas-salesanalyzer-sql;"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
        
        logger.info("Connecting to database with ODBC Driver 17 for SQL Server")
        conn = pyodbc.connect(conn_str, attrs_before={1256: access_token})
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        logger.error(f"Connection string (masked): {conn_str.replace('w-paas-salesanalyzer-sqlserver.database.windows.net', '***').replace('w-paas-salesanalyzer-sql', '***')}")
        raise

def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    SQLクエリを実行し、結果を返します。
    
    Args:
        query (str): 実行するSQLクエリ
        params (Optional[Dict[str, Any]]): クエリパラメータ
        
    Returns:
        List[Dict[str, Any]]: クエリ結果のリスト
    """
    try:
        with get_db_connection() as conn:
            logger.info(f"クエリを実行: {query}")
            if params:
                logger.info(f"パラメータ: {params}")
            
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith("SELECT"):
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                results = [dict(zip(columns, row)) for row in rows]

                # datetime → 文字列化
                for row in results:
                    for key, value in row.items():
                        if hasattr(value, 'isoformat'):
                            row[key] = value.isoformat()

                return results
            else:
                conn.commit()
                return []
                
    except Exception as e:
        logger.error(f"クエリ実行エラー: {str(e)}")
        raise

def test_db_connection() -> bool:
    """
    データベース接続をテストします。
    
    Returns:
        bool: 接続テストの結果
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            logger.info(f"SQL Server バージョン: {version}")
            return True
    except Exception as e:
        logger.error(f"接続テストエラー: {str(e)}")
        return False

def get_current_time():
    """
    現在時刻をUTCで取得し、SQLサーバー互換の形式で返す
    """
    return datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')

# ヘルスチェックエンドポイント
@app.function_name(name="HealthCheck")
@app.route(route="health", methods=["GET", "OPTIONS"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """APIサーバーの稼働状態を確認するためのヘルスチェックエンドポイント"""
    logger.info("Health check endpoint called")
    
    if req.method == "OPTIONS":
        # CORS プリフライトリクエスト処理
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        return func.HttpResponse(status_code=204, headers=headers)
    
    # ヘルスチェックレスポンス
    headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
    return func.HttpResponse(
        body='{"status":"ok","message":"API server is running"}',
        status_code=200,
        headers=headers
    )

# データベース接続テストエンドポイント
@app.function_name(name="TestDbConnection")
@app.route(route="test/db-connection", methods=["GET", "OPTIONS"])
def test_db_connection_func(req: func.HttpRequest) -> func.HttpResponse:
    """データベース接続をテストするエンドポイント"""
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        # 接続テストを実行
        success = test_db_connection()
        
        if success:
            response = {
                "success": True,
                "message": "データベース接続テストが成功しました"
            }
            status_code = 200
        else:
            response = {
                "success": False,
                "message": "データベース接続テストが失敗しました"
            }
            status_code = 500

        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=status_code,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Database connection test error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({
                "success": False,
                "message": f"データベース接続テスト中にエラーが発生しました: {str(e)}"
            }, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# 認証関連のエンドポイント
@app.function_name(name="RegisterTest")
@app.route(route="register/test", methods=["GET", "POST", "OPTIONS"])
def register_test(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        data = req.get_json()
        return register(req, data)

    except Exception as e:
        logger.error(f"Register test error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# ログインエンドポイント
@app.function_name(name="Login")
@app.route(route="users/login", methods=["POST", "OPTIONS"])
def login_func(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        data = req.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return func.HttpResponse(
                json.dumps({"error": "Email and password are required"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400
            )

        # データベースからユーザー情報を取得
        query = "SELECT * FROM dbo.Users WHERE email = ?"
        users = execute_query(query, (email,))

        if not users:
            return func.HttpResponse(
                json.dumps({"error": "Invalid email or password"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=401
            )

        user = User.from_dict(users[0])
        if not user.verify_password(password):
            return func.HttpResponse(
                json.dumps({"error": "Invalid email or password"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=401
            )

        response = {
            "user_id": user.user_id,
            "user_name": user.user_name,
            "email": user.email,
            "is_manager": user.is_manager,
            "manager_name": user.manager_name,
            "is_active": user.is_active,
            "account_status": user.account_status
        }

        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# ユーザー情報取得エンドポイント
@app.function_name(name="GetUserById")
@app.route(route="users/{user_id}", methods=["GET", "OPTIONS"])
def get_user_by_id_func(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        user_id = req.route_params.get('user_id')
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "User ID is required"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400
            )

        # データベースからユーザー情報を取得
        query = """
            SELECT user_id, user_name, email, is_manager, manager_name, is_active, account_status 
            FROM dbo.Users 
            WHERE user_id = ?
        """
        users = execute_query(query, (user_id,))

        if not users:
            return func.HttpResponse(
                json.dumps({"error": "User not found"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=404
            )

        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(users[0], ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# 会議関連のエンドポイント
@app.function_name(name="SaveBasicInfo")
@app.route(route="basicinfo", auth_level=func.AuthLevel.ANONYMOUS)
def save_basic_info_func(req: func.HttpRequest) -> func.HttpResponse:
    """会議の基本情報を保存する"""
    try:
        # OPTIONSリクエスト処理
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        # reqオブジェクトをそのまま渡す
        return save_basic_info(req)
        
    except ValueError as e:
        logger.error(f"Invalid request data: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Invalid request data: {str(e)}"}),
            status_code=400,
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Save basic info error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

# 会議一覧取得エンドポイント
@app.function_name(name="GetMeetings")
@app.route(route="meetings", methods=["GET", "OPTIONS"])
def get_meetings_func(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        # クエリパラメータからユーザーIDを取得
        user_id = req.params.get('userId')
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "ユーザーIDが必要です"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400
            )

        query = """
            SELECT meeting_id, user_id, client_contact_name, client_company_name, 
                   meeting_datetime, duration_seconds, status, transcript_text, 
                   file_name, file_size, error_message 
            FROM dbo.Meetings
            WHERE user_id = ?
            ORDER BY meeting_datetime DESC
        """
        meetings = execute_query(query, (user_id,))

        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(meetings, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Get meetings error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# メンバー会議一覧取得エンドポイント
@app.function_name(name="GetMembersMeetings")
@app.route(route="members-meetings", methods=["GET", "OPTIONS"])
def get_members_meetings_func(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        query = """
            SELECT m.meeting_id, m.user_id, m.client_contact_name, m.client_company_name, 
                   m.meeting_datetime, m.duration_seconds, m.status, m.transcript_text, 
                   m.file_name, m.file_size, m.error_message, u.user_name 
            FROM dbo.Meetings m 
            JOIN dbo.Users u ON m.user_id = u.user_id
        """
        meetings = execute_query(query)

        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(meetings, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Get members meetings error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# 基本情報検索エンドポイント
@app.function_name(name="SearchBasicInfo")
@app.route(route="basicinfo/search", methods=["GET", "OPTIONS"])
def search_basic_info_func(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        query = "SELECT * FROM dbo.BasicInfo"
        basic_info = execute_query(query)

        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(basic_info, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Search basic info error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# フィードバック一覧取得エンドポイント
@app.function_name(name="GetFeedback")
@app.route(route="feedback", methods=["GET", "OPTIONS"])
def get_feedback_func(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        query = """
            SELECT f.feedback_id, f.meeting_id, f.user_id, f.feedback_text, 
                   f.inserted_datetime, f.updated_datetime, u.user_name 
            FROM dbo.Feedback f 
            JOIN dbo.Users u ON f.user_id = u.user_id
        """
        feedback_list = execute_query(query)

        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(feedback_list, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Get feedback error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# 会議IDによるフィードバック取得エンドポイント
@app.function_name(name="GetFeedbackByMeetingId")
@app.route(route="feedback/{meeting_id}", methods=["GET", "OPTIONS"])
def get_feedback_by_meeting_id_func(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        meeting_id = req.route_params.get('meeting_id')
        if not meeting_id:
            return func.HttpResponse(
                json.dumps({"error": "Meeting ID is required"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400
            )

        query = """
            SELECT f.feedback_id, f.meeting_id, f.user_id, f.feedback_text, 
                   f.inserted_datetime, f.updated_datetime, u.user_name 
            FROM dbo.Feedback f 
            JOIN dbo.Users u ON f.user_id = u.user_id 
            WHERE f.meeting_id = ?
        """
        feedback_list = execute_query(query, (meeting_id,))

        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(feedback_list, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Get feedback by meeting ID error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# 会話セグメント取得エンドポイント
@app.function_name(name="GetConversationSegments")
@app.route(route="conversation/segments/{meeting_id}", methods=["GET", "OPTIONS"])
def get_conversation_segments(req: func.HttpRequest) -> func.HttpResponse:
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

# コメント取得エンドポイント
@app.function_name(name="GetComments")
@app.route(route="comments/{segment_id}", methods=["GET", "OPTIONS"])
def get_segment_comments(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
            
        segment_id = req.route_params.get('segment_id')
        
        query = """
            SELECT c.comment_id, c.segment_id, c.meeting_id, c.user_id, c.content, 
                   c.inserted_datetime, c.updated_datetime, u.user_name 
            FROM dbo.Comments c 
            JOIN dbo.Users u ON c.user_id = u.user_id 
            WHERE c.deleted_datetime IS NULL AND c.segment_id = ?
        """
        comments = execute_query(query, (segment_id,))
                
                # 日付時刻の適切な変換
        for comment in comments:
            if hasattr(comment['inserted_datetime'], 'isoformat'):
                comment['inserted_datetime'] = comment['inserted_datetime'].isoformat()
            elif comment['inserted_datetime'] is not None and not isinstance(comment['inserted_datetime'], str):
                comment['inserted_datetime'] = str(comment['inserted_datetime'])
            
            if hasattr(comment['updated_datetime'], 'isoformat'):
                comment['updated_datetime'] = comment['updated_datetime'].isoformat()
            elif comment['updated_datetime'] is not None and not isinstance(comment['updated_datetime'], str):
                comment['updated_datetime'] = str(comment['updated_datetime'])
            
            # 既読情報（一時的に空配列を返す）
            comment['readers'] = []
        
        response = {
            "success": True,
            "message": f"コメントを取得しました（segment_id: {segment_id}）",
            "comments": comments
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False), 
            mimetype="application/json",
            status_code=200,
            headers=headers
        )
    except Exception as e:
        logger.error(f"Get comments error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# コメント追加エンドポイント
@app.function_name(name="AddComment")
@app.route(route="comments", methods=["POST", "OPTIONS"])
def create_comment(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
            
        req_body = req.get_json()
        
        # リクエストのバリデーション
        segment_id = req_body.get('segment_id')
        meeting_id = req_body.get('meeting_id')
        user_id = req_body.get('user_id')
        content = req_body.get('content')
        
        if not all([segment_id, meeting_id, user_id, content]):
            headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
            return func.HttpResponse(
                json.dumps({"success": False, "message": "必須パラメータが不足しています"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400,
                headers=headers
            )
        
        # 現在の日時をSQL Serverに適した形式で文字列化
        now = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
        
        # コメントをデータベースに挿入
        insert_query = """
            INSERT INTO dbo.Comments (segment_id, meeting_id, user_id, content, inserted_datetime, updated_datetime)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        execute_query(insert_query, (
            segment_id,
            meeting_id,
            user_id,
            content,
            now,
            now
        ))
        
        # 新しく追加されたコメントのIDを取得
        query = "SELECT TOP 1 comment_id FROM dbo.Comments ORDER BY comment_id DESC"
        last_comment = execute_query(query)
        new_comment_id = last_comment[0]['comment_id'] if last_comment else None
        
        response = {
            "success": True,
            "message": "コメントが追加されました",
            "comment_id": new_comment_id
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=201,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Add comment error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# コメント既読状態更新エンドポイント
@app.function_name(name="MarkCommentAsRead")
@app.route(route="comments/read", methods=["POST", "OPTIONS"])
def mark_comment_as_read(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
        
        # 正常なレスポンスを返す（実際の処理は行わない）
        response = {
            "success": True,
            "message": "既読機能は一時的に無効化されています"
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Mark comment as read error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# 最新コメント取得エンドポイント
@app.function_name(name="GetLatestComments")
@app.route(route="comments-latest", methods=["GET", "OPTIONS"])
def get_latest_comments(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        # クエリパラメータの取得
        user_id = req.params.get('userId')
        limit = int(req.params.get('limit', 5))
        
        logger.info(f"=== GetLatestComments Debug Info ===")
        logger.info(f"Request parameters - userId: {user_id}, limit: {limit}")

        # user_idが指定されていない場合はエラーを返す
        if not user_id:
            logger.warning("userId parameter is required")
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "ユーザーIDが必要です",
                    "comments": []
                }, ensure_ascii=False),
                mimetype="application/json",
                status_code=400,
                headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
            )

        # user_idが指定されている場合、そのユーザーに関連するmeeting_idを取得
        meeting_query = """
            SELECT DISTINCT meeting_id 
            FROM dbo.BasicInfo 
            WHERE user_id = ? AND deleted_datetime IS NULL
        """
        meetings = execute_query(meeting_query, (user_id,))
        meeting_ids = [m['meeting_id'] for m in meetings]
        
        logger.info(f"Found meetings for user_id {user_id}: {meeting_ids}")

        if not meeting_ids:
            logger.info(f"No meetings found for user_id {user_id}")
            return func.HttpResponse(
                json.dumps({
                    "success": True,
                    "message": "関連する会議が見つかりませんでした",
                    "comments": []
                }, ensure_ascii=False),
                mimetype="application/json",
                status_code=200,
                headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
            )

        # meeting_idsを使用してコメントを取得
        query = """
            SELECT TOP (?) c.comment_id, c.segment_id, c.meeting_id, c.user_id, c.content, 
                   c.inserted_datetime, c.updated_datetime, u.user_name, 
                   b.client_company_name, b.client_contact_name,
                   CASE WHEN cr.reader_id IS NOT NULL THEN 1 ELSE 0 END as is_read
            FROM dbo.Comments c 
            JOIN dbo.Users u ON c.user_id = u.user_id 
            JOIN dbo.BasicInfo b ON c.meeting_id = b.meeting_id 
            LEFT JOIN dbo.CommentReads cr ON c.comment_id = cr.comment_id AND cr.reader_id = ?
            WHERE c.deleted_datetime IS NULL 
            AND c.meeting_id IN ({})
            AND b.user_id = ?
            ORDER BY c.inserted_datetime DESC
        """.format(','.join(['?'] * len(meeting_ids)))

        params = [limit, user_id] + meeting_ids + [user_id]
        logger.info(f"Executing comments query with params: {params}")
        comments = execute_query(query, params)
        logger.info(f"Found {len(comments)} comments for user_id {user_id}")
        
        # コメントの詳細をログ出力
        for comment in comments:
            logger.info(f"Comment details - id: {comment['comment_id']}, meeting_id: {comment['meeting_id']}, user_id: {comment['user_id']}, user_name: {comment['user_name']}")

        # 日付時刻の変換とisReadの設定
        for comment in comments:
            if hasattr(comment['inserted_datetime'], 'isoformat'):
                comment['inserted_datetime'] = comment['inserted_datetime'].isoformat()
            if hasattr(comment['updated_datetime'], 'isoformat'):
                comment['updated_datetime'] = comment['updated_datetime'].isoformat()
            comment['isRead'] = bool(comment['is_read'])
            del comment['is_read']

        response = {
            "success": True,
            "message": f"最新コメントを取得しました（userId: {user_id}, limit: {limit}）",
            "comments": comments
        }

        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )
    except Exception as e:
        logger.error(f"Get latest comments error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# 会議IDによる基本情報取得エンドポイント
@app.function_name(name="GetBasicInfoByMeetingId")
@app.route(route="basicinfo/{meeting_id}", methods=["GET", "OPTIONS"])
def get_basic_info_by_meeting_id(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        meeting_id = req.route_params.get('meeting_id')
        if not meeting_id:
            return func.HttpResponse(
                json.dumps({"error": "会議IDが必要です"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400
            )

        query = """
            SELECT meeting_id, user_id, client_contact_name, client_company_name,
                   meeting_datetime, duration_seconds, status, transcript_text,
                   file_name, file_size, error_message
            FROM dbo.Meetings
            WHERE meeting_id = ?
        """
        meetings = execute_query(query, (meeting_id,))

        if not meetings:
            return func.HttpResponse(
                json.dumps({"error": "会議が見つかりません"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=404
            )

        response = {
            "success": True,
            "message": f"会議の基本情報を取得しました（meeting_id: {meeting_id}）",
            "basicInfo": meetings[0]
        }

        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )

    except Exception as e:
        logger.error(f"Get basic info by meeting ID error: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )
