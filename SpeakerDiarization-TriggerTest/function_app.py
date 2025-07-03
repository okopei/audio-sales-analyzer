import logging
import azure.functions as func
import pyodbc
import os
import struct
import uuid
import re
import requests
from datetime import datetime, timezone, timedelta
from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
import isodate

app = func.FunctionApp()

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

# @app.function_name(name="InsertMeetingFromBlob")
# @app.event_grid_trigger(arg_name="event")
# def insert_meeting_from_blob(event: func.EventGridEvent):
#     try:
#         logging.info("EventGrid Trigger received event.")

#         # イベントデータ構造を確認用ログ出力
#         event_json = event.get_json()
#         logging.info(f"Full event JSON: {event_json}")

#         blob_url = event_json.get("url")
#         if not blob_url:
#             raise ValueError("イベントデータから Blob URL を取得できません")

#         logging.info(f"Blob URL: {blob_url}")

#         # ファイル名から meeting_id, user_id を抽出
#         file_name = blob_url.split("/")[-1]
#         match = re.match(r"meeting_(\d+)_user_(\d+)_.*", file_name)
#         if not match:
#             raise ValueError("ファイル名から meeting_id と user_id を抽出できません")

#         meeting_id = int(match.group(1))
#         user_id = int(match.group(2))
#         logging.info(f"Extracted meeting_id={meeting_id}, user_id={user_id}")

#         conn = get_db_connection()
#         cursor = conn.cursor()

#         # BasicInfo テーブルから会議情報取得
#         cursor.execute("""
#             SELECT client_company_name, client_contact_name, meeting_datetime
#             FROM dbo.BasicInfo
#             WHERE meeting_id = ?
#         """, meeting_id)

#         row = cursor.fetchone()
#         if not row:
#             raise Exception(f"BasicInfo に meeting_id={meeting_id} が見つかりません")

#         client_company_name, client_contact_name, meeting_datetime = row
#         logging.info(f"Retrieved from BasicInfo: {client_company_name}, {client_contact_name}, {meeting_datetime}")

#         # Meetings テーブルに挿入
#         insert_query = """
#             INSERT INTO dbo.Meetings (
#                 meeting_id, user_id, title, file_name, file_path, file_size,
#                 duration_seconds, status, client_company_name, client_contact_name,
#                 meeting_datetime, start_datetime, inserted_datetime, updated_datetime
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())
#         """
#         cursor.execute(insert_query, (
#             meeting_id,
#             user_id,
#             "Auto generated meeting",
#             file_name,
#             blob_url,
#             0,  # file_size 仮
#             0,  # duration_seconds 仮
#             "processing",
#             client_company_name,
#             client_contact_name,
#             meeting_datetime,
#             datetime.utcnow()
#         ))

#         conn.commit()
#         logging.info(f"Inserted meeting_id={meeting_id} into Meetings.")

#     except Exception as e:
#         logging.exception("Error during InsertMeetingFromBlob:")


@app.function_name(name="TriggerTranscriptionJob")
@app.event_grid_trigger(arg_name="event")
def trigger_transcription_job(event: func.EventGridEvent):
    try:
        logging.info("=== Transcription Job Trigger Start ===")

        event_json = event.get_json()
        logging.info(f"Full event JSON: {event_json}")

        blob_url = event_json.get("url")
        if not blob_url:
            raise ValueError("イベントデータから Blob URL を取得できません")

        logging.info(f"Blob URL: {blob_url}")

        path_parts = blob_url.split('/')
        container_name = path_parts[-2]
        blob_name = path_parts[-1]

        if not blob_name.lower().endswith('.wav'):
            logging.warning(f"❌ 非WAVファイルが検知されました: {blob_name} → スキップします")
            return

        account_name = os.environ["ACCOUNT_NAME"]
        account_key = os.environ["ACCOUNT_KEY"].strip().replace('\n', '')

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        sas_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
        logging.info(f"Generated SAS URL: {sas_url}")

        speech_key = os.environ["SPEECH_KEY"]
        region = os.environ["SPEECH_REGION"]
        callback_url = os.environ["TRANSCRIPTION_CALLBACK_URL"]

        payload = {
            "contentUrls": [sas_url],
            "locale": "ja-JP",
            "displayName": f"transcription-{uuid.uuid4()}",
            "properties": {
                "diarizationEnabled": True,
                "wordLevelTimestampsEnabled": True,
                "punctuationMode": "DictatedAndAutomatic",
                "profanityFilterMode": "Masked",
                "callbackUrl": callback_url
            }
        }
        headers = {
            "Ocp-Apim-Subscription-Key": speech_key,
            "Content-Type": "application/json"
        }
        endpoint = f"https://{region}.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions"
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        logging.info(f"✅ Transcription job submitted successfully.")
        logging.info(f"🎯 Job self URL: {result.get('self')}")
        
        job_url = result.get("self")
        job_id = job_url.split("/")[-1] if job_url else "N/A"
        logging.info(f"🆔 Transcription Job ID: {job_id}")

    except Exception as e:
        logging.error(f"❌ Trigger error: {str(e)}")




@app.function_name(name="TranscriptionCallback")
@app.route(route="transcription-callback", methods=["POST"])
def transcription_callback(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
        transcription_url = data["self"]
        content_urls = data["contentUrls"]
        results_url = data["resultsUrls"].get("channel_0")
        if not results_url:
            return func.HttpResponse("Missing resultsUrl", status_code=400)

        file_name = content_urls[0].split("/")[-1]
        match = re.search(r"meeting_(\d+)_user_(\d+)", file_name)
        if not match:
            return func.HttpResponse("Invalid file name format", status_code=400)

        meeting_id = int(match.group(1))
        user_id = int(match.group(2))

        headers = {"Ocp-Apim-Subscription-Key": os.environ["SPEECH_KEY"]}
        status_resp = requests.get(transcription_url, headers=headers)
        if status_resp.json()["status"] != "Succeeded":
            return func.HttpResponse("Not ready", status_code=202)

        response = requests.get(results_url, headers=headers)
        result_json = response.json()

        transcript = []
        for phrase in result_json["recognizedPhrases"]:
            speaker = phrase.get("speaker", "Unknown")
            text = phrase["nBest"][0]["display"]
            offset = phrase.get("offset", "PT0S")
            try:
                offset_seconds = round(isodate.parse_duration(offset).total_seconds(), 1)
            except:
                offset_seconds = 0.0
            transcript.append(f"(Speaker{speaker})[{text}]({offset_seconds})")

        transcript_text = " ".join(transcript)

        conn = get_db_connection()
        cursor = conn.cursor()

        # BasicInfoから情報取得
        cursor.execute("""
            SELECT client_company_name, client_contact_name, meeting_datetime
            FROM dbo.BasicInfo
            WHERE meeting_id = ?
        """, meeting_id)
        row = cursor.fetchone()
        if not row:
            return func.HttpResponse(f"BasicInfo に meeting_id={meeting_id} が見つかりません", status_code=400)

        client_company_name, client_contact_name, meeting_datetime = row

        # 既存のレコードがないことを確認
        cursor.execute("""
            SELECT COUNT(*) FROM dbo.Meetings WHERE meeting_id = ? AND user_id = ?
        """, meeting_id, user_id)
        existing = cursor.fetchone()[0]
        if existing > 0:
            return func.HttpResponse(f"Meetings に meeting_id={meeting_id}, user_id={user_id} のレコードが既に存在しています", status_code=400)

        # INSERT
        title = "Auto generated meeting"
        file_path = content_urls[0]
        file_size = 0
        duration_seconds = 0

        insert_sql = """
        INSERT INTO dbo.Meetings (
            meeting_id, user_id, title, file_name, file_path,
            file_size, duration_seconds, status,
            client_company_name, client_contact_name,
            meeting_datetime, start_datetime, inserted_datetime,
            updated_datetime, transcript_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), ?)
        """
        insert_params = (
            meeting_id, user_id, title, file_name, file_path,
            file_size, duration_seconds, 'completed',
            client_company_name, client_contact_name,
            meeting_datetime, meeting_datetime, transcript_text
        )

        cursor.execute(insert_sql, insert_params)
        conn.commit()

        return func.HttpResponse("OK", status_code=200)

    except Exception as e:
        logging.error(f"Callback error: {str(e)}")
        return func.HttpResponse("Error", status_code=500)
