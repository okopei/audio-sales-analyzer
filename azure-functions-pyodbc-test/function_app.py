import logging
import os
import pyodbc  # または pyodbc
import traceback
import azure.functions as func
from azure.functions import FunctionApp

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

        conn = pyodbc.connect(conn_str, timeout=10)
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
