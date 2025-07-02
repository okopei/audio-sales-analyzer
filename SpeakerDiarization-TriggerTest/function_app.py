import logging
import azure.functions as func
import pyodbc
import os
import struct
import re
from azure.identity import ClientSecretCredential
from datetime import datetime
from azure.functions import FunctionApp

app = FunctionApp()

def get_db_connection():
    """
    ローカル：ClientSecretCredential（pyodbc）
    本番環境：Microsoft Entra ID（Managed Identity）を使用して Azure SQL Database に接続する。
    ODBC Driver 17 for SQL Server + Authentication=ActiveDirectoryMsi を使用。
    """
    try:
        logging.info("[DB接続] 開始")

        server = os.getenv("SQL_SERVER")
        database = os.getenv("SQL_DATABASE")

        if not server or not database:
            raise ValueError("SQL_SERVER または SQL_DATABASE の環境変数が設定されていません")

        env = os.getenv("AZURE_ENVIRONMENT", "local")  # "local" or "production"
        is_local = env.lower() != "production"

        if is_local:
            # 🔐 ローカル用：ClientSecretCredential + pyodbc + アクセストークン
            logging.info("[DB接続] ローカル環境（pyodbc + Entra認証トークン）")

            tenant_id = os.getenv("TENANT_ID")
            client_id = os.getenv("CLIENT_ID")
            client_secret = os.getenv("CLIENT_SECRET")

            if not all([tenant_id, client_id, client_secret]):
                raise ValueError("TENANT_ID, CLIENT_ID, CLIENT_SECRET が未設定です")

            credential = ClientSecretCredential(tenant_id, client_id, client_secret)
            token = credential.get_token("https://database.windows.net/.default")

            token_bytes = bytes(token.token, "utf-8")
            exptoken = b''.join(bytes((b, 0)) for b in token_bytes)
            access_token = struct.pack("=i", len(exptoken)) + exptoken

            conn_str = (
                f"Driver={{ODBC Driver 17 for SQL Server}};"
                f"Server=tcp:{server},1433;"
                f"Database={database};"
                "Encrypt=yes;TrustServerCertificate=no;"
                "Connection Timeout=30;"
            )

            conn = pyodbc.connect(conn_str, attrs_before={1256: access_token})
        else:
            # ☁️ 本番用：Managed Identity + pypyodbc + MSI認証
            logging.info("[DB接続] Azure 環境（pypyodbc + MSI）")

            conn_str = (
                f"Driver={{ODBC Driver 17 for SQL Server}};"
                f"Server=tcp:{server},1433;"
                f"Database={database};"
                "Authentication=ActiveDirectoryMsi;"
                "Encrypt=yes;TrustServerCertificate=no;"
            )
            conn = pyodbc.connect(conn_str, timeout=10)
        logging.info("[DB接続] 成功")
        return conn
    except Exception as e:
        logging.error("[DB接続] エラー発生")
        logging.exception("詳細:")
        raise

@app.function_name(name="InsertMeetingFromBlob")
@app.event_grid_trigger(arg_name="event")
def insert_meeting_from_blob(event: func.EventGridEvent):
    try:
        logging.info("EventGrid Trigger received event.")

        # イベントデータ構造を確認用ログ出力
        event_json = event.get_json()
        logging.info(f"Full event JSON: {event_json}")

        blob_url = event_json.get("url")
        if not blob_url:
            raise ValueError("イベントデータから Blob URL を取得できません")

        logging.info(f"Blob URL: {blob_url}")

        # ファイル名から meeting_id, user_id を抽出
        file_name = blob_url.split("/")[-1]
        match = re.match(r"meeting_(\d+)_user_(\d+)_.*", file_name)
        if not match:
            raise ValueError("ファイル名から meeting_id と user_id を抽出できません")

        meeting_id = int(match.group(1))
        user_id = int(match.group(2))
        logging.info(f"Extracted meeting_id={meeting_id}, user_id={user_id}")

        conn = get_db_connection()
        cursor = conn.cursor()

        # BasicInfo テーブルから会議情報取得
        cursor.execute("""
            SELECT client_company_name, client_contact_name, meeting_datetime
            FROM dbo.BasicInfo
            WHERE meeting_id = ?
        """, meeting_id)

        row = cursor.fetchone()
        if not row:
            raise Exception(f"BasicInfo に meeting_id={meeting_id} が見つかりません")

        client_company_name, client_contact_name, meeting_datetime = row
        logging.info(f"Retrieved from BasicInfo: {client_company_name}, {client_contact_name}, {meeting_datetime}")

        # Meetings テーブルに挿入
        insert_query = """
            INSERT INTO dbo.Meetings (
                meeting_id, user_id, title, file_name, file_path, file_size,
                duration_seconds, status, client_company_name, client_contact_name,
                meeting_datetime, start_datetime, inserted_datetime, updated_datetime
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())
        """
        cursor.execute(insert_query, (
            meeting_id,
            user_id,
            "Auto generated meeting",
            file_name,
            blob_url,
            0,  # file_size 仮
            0,  # duration_seconds 仮
            "processing",
            client_company_name,
            client_contact_name,
            meeting_datetime,
            datetime.utcnow()
        ))

        conn.commit()
        logging.info(f"Inserted meeting_id={meeting_id} into Meetings.")

    except Exception as e:
        logging.exception("Error during InsertMeetingFromBlob:")
