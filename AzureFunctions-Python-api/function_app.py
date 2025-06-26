import logging
import os
import pypyodbc  # または pyodbc
import traceback
import azure.functions as func
from azure.functions import FunctionApp
import json
from typing import Optional, Dict, List, Any




app = FunctionApp()

def get_db_connection():
    """
    Microsoft Entra ID（Managed Identity）を使用して Azure SQL Database に接続する。
    ODBC Driver 17 for SQL Server + Authentication=ActiveDirectoryMsi を使用。
    """
    try:
        logging.info("[DB接続] 開始")

        # 環境変数から接続先情報を取得
        server = os.getenv("SQL_SERVER")
        database = os.getenv("SQL_DATABASE")

        if not server or not database:
            raise ValueError("SQL_SERVER または SQL_DATABASE の環境変数が設定されていません")

        # 接続文字列の構築（Managed Identity認証）
        conn_str = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:{server},1433;"
            f"Database={database};"
            "Authentication=ActiveDirectoryMsi;"
            "Encrypt=yes;TrustServerCertificate=no;"
        )

        logging.info(f"[DB接続] 接続文字列（masked）: Server={server}, Database={database}")
        conn = pypyodbc.connect(conn_str, timeout=10)

        logging.info("[DB接続] 成功")
        return conn

    except Exception as e:
        logging.error("[DB接続] エラー発生")
        logging.exception("詳細:")
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
            logging.info(f"クエリを実行: {query}")
            if params:
                logging.info(f"パラメータ: {params}")
            
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
        logging.error(f"クエリ実行エラー: {str(e)}")
        raise


@app.function_name(name="TestDbConnection")
@app.route(route="testdb", auth_level=func.AuthLevel.ANONYMOUS)
def test_db_connection(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logging.info("A: DB接続開始前")
        
        query = "SELECT * FROM [dbo].[Users] WHERE [user_id] = ?"
        result = execute_query(query, (27,))
        
        if result:
            result_str = "\n".join(str(row) for row in result)
            return func.HttpResponse(f"ユーザーデータ取得成功:\n{result_str}", status_code=200)
        else:
            return func.HttpResponse("ユーザーデータが見つかりません", status_code=404)

    except Exception as e:
        logging.error("C: DB接続失敗")
        logging.exception("接続エラー詳細:")
        return func.HttpResponse(
            f"接続失敗: {str(e)}\n{traceback.format_exc()}",
            status_code=500
        )
    
@app.function_name(name="GetUserById")
@app.route(route="users/{user_id}", auth_level=func.AuthLevel.ANONYMOUS)
def get_user_by_id_func(req: func.HttpRequest) -> func.HttpResponse:
    try:
        user_id = req.route_params.get("user_id")
        if not user_id:
            return func.HttpResponse("user_id is required", status_code=400)

        query = "SELECT * FROM [dbo].[Users] WHERE [user_id] = ?"
        result = execute_query(query, (user_id,))

        if result:
            return func.HttpResponse(
                json.dumps(result[0], ensure_ascii=False, default=str),
                mimetype="application/json",
                status_code=200
            )
        else:
            return func.HttpResponse(
                json.dumps({"error": "ユーザーが見つかりません"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=404
            )

    except Exception as e:
        logging.exception("ユーザー取得エラー:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500
        )


@app.function_name(name="GetLatestComments")
@app.route(route="comments-latest", auth_level=func.AuthLevel.ANONYMOUS)
def get_latest_comments(req: func.HttpRequest) -> func.HttpResponse:
    try:
        user_id = req.params.get("userId")
        if not user_id:
            return func.HttpResponse("userId is required", status_code=400)

        query = """
            SELECT c.*
            FROM Comments c
            JOIN BasicInfo b ON c.meeting_id = b.meeting_id
            WHERE b.user_id = ?
            ORDER BY c.inserted_datetime DESC
        """

        result = execute_query(query, (user_id,))

        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, default=str), 
            status_code=200, 
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception("コメント取得エラー:")
        return func.HttpResponse(f"エラー: {str(e)}", status_code=500)
    
@app.function_name(name="GetMembersMeetings")
@app.route(route="members-meetings", auth_level=func.AuthLevel.ANONYMOUS)
def get_members_meetings(req: func.HttpRequest) -> func.HttpResponse:
    try:
        manager_id = req.params.get("manager_id")
        if not manager_id:
            return func.HttpResponse("manager_id is required", status_code=400)

        query = """
            SELECT m.*, u.user_name
            FROM Meetings m
            JOIN Users u ON m.user_id = u.user_id
            WHERE u.manager_id = ?
            ORDER BY m.meeting_datetime DESC
        """

        result = execute_query(query, (manager_id,))

        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception("メンバー会議取得エラー:")
        return func.HttpResponse(f"エラー: {str(e)}", status_code=500)

@app.function_name(name="SaveBasicInfo")
@app.route(route="basicinfo", methods=["POST", "OPTIONS"], auth_level=func.AuthLevel.ANONYMOUS)
def save_basic_info_func(req: func.HttpRequest) -> func.HttpResponse:
    """会議の基本情報を保存する（datetime変換を使わない版）"""
    try:
        if req.method == "OPTIONS":
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)

        req_body = req.get_json()
        logging.info(f"リクエストボディ: {req_body}")

        required_fields = ['user_id', 'client_contact_name', 'client_company_name', 'meeting_datetime']
        for field in required_fields:
            if field not in req_body:
                return func.HttpResponse(
                    f"Missing required field: {field}",
                    status_code=400
                )

        # フィールド取得（datetime変換しない）
        user_id = req_body["user_id"]
        contact_name = req_body["client_contact_name"]
        company_name = req_body["client_company_name"]
        meeting_datetime = req_body["meeting_datetime"]
        industry_type = req_body.get("industry", "")
        company_scale = req_body.get("scale", "")
        sales_goal = req_body.get("meeting_goal", "")

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

        # execute_queryはSELECTクエリの結果を返すため、INSERTの場合は直接DB接続を使用
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(insert_query, (
                user_id,
                contact_name,
                company_name,
                meeting_datetime,
                industry_type,
                company_scale,
                sales_goal
            ))

            row = cursor.fetchone()
            if not row or row[0] is None:
                raise Exception("会議IDの取得に失敗しました")

            conn.commit()
            return func.HttpResponse(
                json.dumps({
                    "message": "会議の基本情報が保存されました",
                    "meeting_id": int(row[0])
                }, ensure_ascii=False, default=str),
                mimetype="application/json",
                status_code=201
            )

    except Exception as e:
        logging.exception("SaveBasicInfo エラー:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False, default=str),
            mimetype="application/json",
            status_code=500
        )

# 会話セグメント取得エンドポイント
@app.function_name(name="GetConversationSegments")
@app.route(route="conversation/segments/{meeting_id}", methods=["GET", "OPTIONS"])
def get_conversation_segments(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            })

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

        for segment in segments:
            segment['inserted_datetime'] = segment['inserted_datetime'].isoformat()
            segment['updated_datetime'] = segment['updated_datetime'].isoformat()

        return func.HttpResponse(
            json.dumps({"success": True, "segments": segments}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )
    

# コメント一覧取得
@app.function_name(name="GetComments")
@app.route(route="comments/{segment_id}", methods=["GET", "OPTIONS"])
def get_segment_comments(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            })

        segment_id = req.route_params.get('segment_id')
        query = """
            SELECT c.comment_id, c.segment_id, c.meeting_id, c.user_id, c.content, 
                   c.inserted_datetime, c.updated_datetime, u.user_name
            FROM dbo.Comments c 
            JOIN dbo.Users u ON c.user_id = u.user_id 
            WHERE c.deleted_datetime IS NULL AND c.segment_id = ?
        """
        comments = execute_query(query, (segment_id,))

        for comment in comments:
            comment['inserted_datetime'] = comment['inserted_datetime'].isoformat()
            comment['updated_datetime'] = comment['updated_datetime'].isoformat()
            comment['readers'] = []

        return func.HttpResponse(
            json.dumps({"success": True, "comments": comments}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )

# コメント追加
@app.function_name(name="AddComment")
@app.route(route="comments", methods=["POST", "OPTIONS"])
def create_comment(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            })

        data = req.get_json()
        required = ['segment_id', 'meeting_id', 'user_id', 'content']
        if not all(k in data for k in required):
            return func.HttpResponse(json.dumps({"success": False, "message": "Missing fields"}, ensure_ascii=False), status_code=400)

        insert_query = """
            INSERT INTO dbo.Comments (segment_id, meeting_id, user_id, content, inserted_datetime, updated_datetime)
            VALUES (?, ?, ?, ?, GETDATE(), GETDATE())
        """
        execute_query(insert_query, (
            data['segment_id'], data['meeting_id'], data['user_id'], data['content']
        ))

        comment_id = execute_query("SELECT TOP 1 comment_id FROM dbo.Comments ORDER BY comment_id DESC")[0]['comment_id']
        return func.HttpResponse(json.dumps({"success": True, "comment_id": comment_id}, ensure_ascii=False), status_code=201)

    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}, ensure_ascii=False), status_code=500)

# コメント既読
@app.function_name(name="MarkCommentAsRead")
@app.route(route="comments/read", methods=["POST", "OPTIONS"])
def mark_comment_as_read(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers={"Access-Control-Allow-Origin": "*"})

        data = req.get_json()
        comment_id = data.get('comment_id')
        user_id = data.get('user_id')

        insert_query = """
            IF NOT EXISTS (SELECT 1 FROM dbo.CommentReads WHERE comment_id = ? AND reader_id = ?)
            INSERT INTO dbo.CommentReads (comment_id, reader_id, read_datetime)
            VALUES (?, ?, GETDATE())
        """
        execute_query(insert_query, (comment_id, user_id, comment_id, user_id))

        return func.HttpResponse(json.dumps({"success": True, "message": "Marked as read"}, ensure_ascii=False), status_code=200)

    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}, ensure_ascii=False), status_code=500)

# コメント削除（論理）
@app.function_name(name="DeleteComment")
@app.route(route="comments/{comment_id}", methods=["DELETE", "OPTIONS"])
def delete_comment(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers={"Access-Control-Allow-Origin": "*"})

        comment_id = req.route_params.get('comment_id')
        update_query = "UPDATE dbo.Comments SET deleted_datetime = GETDATE() WHERE comment_id = ?"
        execute_query(update_query, (comment_id,))

        return func.HttpResponse(json.dumps({"success": True, "message": "コメントを削除しました"}, ensure_ascii=False), status_code=200)

    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}, ensure_ascii=False), status_code=500)

# 会議基本情報取得
@app.function_name(name="GetBasicInfoByMeetingId")
@app.route(route="basicinfo/{meeting_id}", methods=["GET", "OPTIONS"])
def get_basic_info_by_meeting_id(req: func.HttpRequest) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=204, headers={"Access-Control-Allow-Origin": "*"})

        meeting_id = req.route_params.get('meeting_id')
        query = """
            SELECT meeting_id, user_id, client_contact_name, client_company_name,
                   meeting_datetime, duration_seconds, status, transcript_text,
                   file_name, file_size, error_message
            FROM dbo.Meetings
            WHERE meeting_id = ?
        """
        results = execute_query(query, (meeting_id,))

        if not results:
            return func.HttpResponse(json.dumps({"error": "Not found"}, ensure_ascii=False), status_code=404)

        return func.HttpResponse(json.dumps({"success": True, "basicInfo": results[0]}, ensure_ascii=False), status_code=200)

    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}, ensure_ascii=False), status_code=500)
