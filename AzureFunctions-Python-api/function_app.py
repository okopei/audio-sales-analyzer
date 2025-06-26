import logging
import os
import pypyodbc  # または pyodbc
import traceback
import azure.functions as func
from azure.functions import FunctionApp
import json

app = FunctionApp()

@app.function_name(name="TestDbConnection")
@app.route(route="testdb", auth_level=func.AuthLevel.ANONYMOUS)
def test_db_connection(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logging.info("A: DB接続開始前")
        
        server = os.getenv("SQL_SERVER")
        database = os.getenv("SQL_DATABASE")

        conn_str = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:{server},1433;"
            f"Database={database};"
            "Authentication=ActiveDirectoryMsi;"
            "Encrypt=yes;TrustServerCertificate=no;"
        )

        conn = pypyodbc.connect(conn_str, timeout=10)
        logging.info("B: DB接続成功")
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM [dbo].[Users] WHERE [user_id] = ?", [27])
        rows = cursor.fetchall()
        result = "\n".join(str(row) for row in rows)

        return func.HttpResponse(f"ユーザーデータ取得成功:\n{result}", status_code=200)

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

        server = os.getenv("SQL_SERVER")
        database = os.getenv("SQL_DATABASE")

        conn_str = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:{server},1433;"
            f"Database={database};"
            "Authentication=ActiveDirectoryMsi;"
            "Encrypt=yes;TrustServerCertificate=no;"
        )

        conn = pypyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM [dbo].[Users] WHERE [user_id] = ?", [user_id])
        row = cursor.fetchone()

        if row:
            return func.HttpResponse(str(row), status_code=200)
        else:
            return func.HttpResponse("ユーザーが見つかりません", status_code=404)

    except Exception as e:
        logging.exception("ユーザー取得エラー:")
        return func.HttpResponse(f"エラー: {str(e)}", status_code=500)

@app.function_name(name="GetLatestComments")
@app.route(route="comments-latest", auth_level=func.AuthLevel.ANONYMOUS)
def get_latest_comments(req: func.HttpRequest) -> func.HttpResponse:
    try:
        user_id = req.params.get("userId")
        if not user_id:
            return func.HttpResponse("userId is required", status_code=400)

        server = os.getenv("SQL_SERVER")
        database = os.getenv("SQL_DATABASE")

        conn_str = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:{server},1433;"
            f"Database={database};"
            "Authentication=ActiveDirectoryMsi;"
            "Encrypt=yes;TrustServerCertificate=no;"
        )

        conn = pypyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()

        query = """
            SELECT c.*
            FROM Comments c
            JOIN BasicInfo b ON c.meeting_id = b.meeting_id
            WHERE b.user_id = ?
            ORDER BY c.inserted_datetime DESC
        """

        cursor.execute(query, [user_id])
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]

        return func.HttpResponse(json.dumps(result, ensure_ascii=False, default=str), status_code=200, mimetype="application/json")

    except Exception as e:
        logging.exception("コメント取得エラー:")
        return func.HttpResponse(f"エラー: {str(e)}", status_code=500)
    
@app.function_name(name="MarkCommentAsRead")
@app.route(route="comments/read", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def mark_comment_as_read(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        comment_id = data.get("comment_id")
        reader_id = data.get("user_id")

        if not comment_id or not reader_id:
            return func.HttpResponse("comment_id と user_id は必須です", status_code=400)

        server = os.getenv("SQL_SERVER")
        database = os.getenv("SQL_DATABASE")

        conn_str = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:{server},1433;"
            f"Database={database};"
            "Authentication=ActiveDirectoryMsi;"
            "Encrypt=yes;TrustServerCertificate=no;"
        )

        conn = pypyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()

        insert_sql = """
            INSERT INTO CommentReads (comment_id, reader_id, read_datetime)
            VALUES (?, ?, GETDATE())
        """

        try:
            cursor.execute(insert_sql, (comment_id, reader_id))
            conn.commit()
        except pypyodbc.IntegrityError:
            # 既に既読なら無視（PK衝突）
            pass

        return func.HttpResponse("既読としてマークされました", status_code=200)

    except Exception as e:
        logging.exception("既読マークエラー:")
        return func.HttpResponse(f"エラー: {str(e)}", status_code=500)
