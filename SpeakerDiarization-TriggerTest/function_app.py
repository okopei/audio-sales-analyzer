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
import sys
from pathlib import Path

# openai_processing モジュールを import できるように sys.path を調整
sys.path.append(str(Path(__file__).parent))
from openai_processing.openai_completion_step1 import step1_process_transcript
# from openai_processing.openai_completion_core import clean_and_complete_conversation


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

@app.function_name(name="TriggerTranscriptionJob")
@app.event_grid_trigger(arg_name="event")
def trigger_transcription_job(event: func.EventGridEvent):
    try:
        logging.info("=== Transcription Job Trigger Start ===")

        # イベントから Blob URL を取得
        event_json = event.get_json()
        blob_url = event_json.get("url")
        if not blob_url:
            raise ValueError("イベントデータに Blob URL が含まれていません")
        logging.info(f"Blob URL: {blob_url}")

        # ファイル名とコンテナ名を抽出
        path_parts = blob_url.split('/')
        container_name = path_parts[-2]
        blob_name = path_parts[-1]

        # .wav 以外はスキップ
        if not blob_name.lower().endswith('.wav'):
            logging.warning(f"❌ 非WAVファイルが検知されました: {blob_name} → スキップします")
            return

        # ファイル名から meeting_id, user_id を抽出
        match = re.match(r"meeting_(\d+)_user_(\d+)_.*", blob_name)
        if not match:
            raise ValueError("ファイル名から meeting_id, user_id を抽出できません")
        meeting_id = int(match.group(1))
        user_id = int(match.group(2))
        logging.info(f"🎯 Extracted meeting_id={meeting_id}, user_id={user_id}")

        # DB接続
        conn = get_db_connection()
        cursor = conn.cursor()

        # BasicInfo 取得
        cursor.execute("""
            SELECT client_company_name, client_contact_name, meeting_datetime
            FROM dbo.BasicInfo
            WHERE meeting_id = ?
        """, (meeting_id,))
        row = cursor.fetchone()
        if not row:
            raise Exception(f"meeting_id={meeting_id} に該当する BasicInfo が存在しません")
        client_company_name, client_contact_name, meeting_datetime = row

        # 既存レコードの確認
        cursor.execute("""
            SELECT COUNT(*) FROM dbo.Meetings WHERE meeting_id = ? AND user_id = ?
        """, (meeting_id, user_id))
        if cursor.fetchone()[0] > 0:
            logging.info(f"🔁 会議レコードが既に存在するためスキップ (meeting_id={meeting_id}, user_id={user_id})")
            return

        # SAS URL生成
        account_name = os.environ["ACCOUNT_NAME"]
        account_key = os.environ["ACCOUNT_KEY"]
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        sas_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
        logging.info(f"✅ SAS URL 生成成功: {sas_url}")

        # Speech-to-Text transcription job
        speech_key = os.environ["SPEECH_KEY"]
        region = os.environ["SPEECH_REGION"]
        callback_url = os.environ["TRANSCRIPTION_CALLBACK_URL"]

        payload = {
            "contentUrls": [sas_url],
            "locale": "ja-JP",
            "displayName": f"transcription-{meeting_id}-{user_id}",
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
        job_url = result.get("self")
        job_id = job_url.split("/")[-1] if job_url else None
        logging.info(f"🆔 Transcription Job ID: {job_id}")

        # Meetings テーブルに挿入
        insert_query = """
            INSERT INTO dbo.Meetings (
                meeting_id, user_id, title, file_name, file_path, file_size,
                duration_seconds, status, transcript_text, error_message,
                client_company_name, client_contact_name, meeting_datetime,
                start_datetime, inserted_datetime, updated_datetime, end_datetime, deleted_datetime
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), NULL, NULL)
        """
        cursor.execute(insert_query, (
            meeting_id,
            user_id,
            "Auto generated meeting",
            blob_name,
            job_id,
            0,  # file_size
            0,  # duration_seconds
            "processing",
            None,
            None,
            client_company_name,
            client_contact_name,
            meeting_datetime,
            datetime.now(timezone.utc)
        ))
        conn.commit()
        logging.info("✅ Meetings テーブルにレコード挿入完了")

    except Exception as e:
        logging.exception("❌ TriggerTranscriptionJob エラー:")

@app.function_name(name="PollingTranscriptionResults")
@app.schedule(schedule="0 */5 * * * *", arg_name="timer", run_on_startup=False, use_monitor=False)
def polling_transcription_results(timer: func.TimerRequest) -> None:
    try:
        logging.info("🕓 PollingTranscriptionResults 開始")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT meeting_id, user_id, file_path, transcript_text, status
            FROM dbo.Meetings
            WHERE status IN ('processing', 'transcribed')
        """)
        rows = cursor.fetchall()

        if not rows:
            logging.info("🎯 対象レコードなし（status = 'processing' または 'transcribed'）")
            return

        speech_key = os.environ["SPEECH_KEY"]
        region = os.environ["SPEECH_REGION"]
        headers = {
            "Ocp-Apim-Subscription-Key": speech_key,
            "Content-Type": "application/json"
        }

        for meeting_id, user_id, file_path, transcript_text, current_status in rows:
            try:
                if current_status == "processing":
                    job_id = file_path.strip().split("/")[-1]
                    transcription_url = f"https://{region}.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions/{job_id}"

                    resp = requests.get(transcription_url, headers=headers)
                    resp.raise_for_status()
                    job_data = resp.json()
                    job_status = job_data.get("status")
                    logging.info(f"🎯 JobID={job_id} のステータス: {job_status}")

                    if job_status == "Succeeded":
                        files_url = f"https://{region}.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions/{job_id}/files"
                        files_resp = requests.get(files_url, headers=headers)
                        files_resp.raise_for_status()
                        files_data = files_resp.json()

                        transcription_files = [
                            f for f in files_data["values"]
                            if f.get("kind") == "Transcription" and f.get("name", "").startswith("contenturl_0")
                        ]
                        if not transcription_files:
                            cursor.execute("""
                                UPDATE dbo.Meetings
                                SET status = 'noresult', updated_datetime = GETDATE(), end_datetime = GETDATE(), error_message = ?
                                WHERE meeting_id = ? AND user_id = ?
                            """, ("No transcription file (contenturl_0.json) found", meeting_id, user_id))
                            logging.warning(f"⚠️ Transcription ファイルが見つかりません (job_id={job_id}) → 'noresult' に更新")
                            continue

                        results_url = transcription_files[0]["links"]["contentUrl"]
                        result_resp = requests.get(results_url, headers=headers)
                        result_json = result_resp.json()

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

                        cursor.execute("""
                            UPDATE dbo.Meetings
                            SET transcript_text = ?, status = 'transcribed',
                                updated_datetime = GETDATE(), end_datetime = GETDATE()
                            WHERE meeting_id = ? AND user_id = ?
                        """, (transcript_text, meeting_id, user_id))
                        conn.commit()

                    elif job_status in ["Failed", "Canceled"]:
                        cursor.execute("""
                            UPDATE dbo.Meetings
                            SET status = 'failed', updated_datetime = GETDATE(),
                                end_datetime = GETDATE(), error_message = ?
                            WHERE meeting_id = ? AND user_id = ?
                        """, (f"Speech job {job_status}", meeting_id, user_id))
                        logging.warning(f"❌ transcription 失敗 → status=failed (meeting_id={meeting_id})")
                        continue
                    else:
                        logging.info(f"🕒 transcription 未完了 → スキップ (meeting_id={meeting_id})")
                        continue

                # ステップ1だけを実行してConversationEnrichmentSegmentsへINSERT
                if current_status == 'transcribed':
                    segments = step1_process_transcript(transcript_text)

                    if not segments:
                        logging.warning(f"⚠️ ステップ1の出力が空です (meeting_id={meeting_id})")
                        continue

                    for line_no, seg in enumerate(segments, start=1):
                        speaker = seg["speaker"]
                        text = seg["text"]
                        offset = seg["offset"]
                        is_filler = 1 if len(text.strip("（）")) < 10 else 0

                        cursor.execute("""
                            INSERT INTO dbo.ConversationEnrichmentSegments (
                                meeting_id, line_no, speaker, transcript_text_segment,
                                offset_seconds, is_filler,
                                front_score, after_score,
                                inserted_datetime, updated_datetime
                            )
                            VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, GETDATE(), GETDATE())
                        """, (
                            meeting_id, line_no, speaker, text,
                            offset, is_filler
                        ))

            except Exception as inner_e:
                logging.exception(f"⚠️ 個別処理エラー (meeting_id={meeting_id}): {inner_e}")

        conn.commit()
        logging.info("🔁 Polling 処理完了")

    except Exception as e:
        logging.exception("❌ PollingTranscriptionResults 関数全体でエラーが発生")




# @app.function_name(name="TranscriptionCallback")
# @app.route(route="transcription-callback", methods=["POST"])
# def transcription_callback(req: func.HttpRequest) -> func.HttpResponse:
#     try:
#         data = req.get_json()
#         transcription_url = data["self"]
#         content_urls = data["contentUrls"]
#         results_url = data["resultsUrls"].get("channel_0")
#         if not results_url:
#             return func.HttpResponse("Missing resultsUrl", status_code=400)

#         file_name = content_urls[0].split("/")[-1]
#         match = re.search(r"meeting_(\d+)_user_(\d+)", file_name)
#         if not match:
#             return func.HttpResponse("Invalid file name format", status_code=400)

#         meeting_id = int(match.group(1))
#         user_id = int(match.group(2))

#         headers = {"Ocp-Apim-Subscription-Key": os.environ["SPEECH_KEY"]}
#         status_resp = requests.get(transcription_url, headers=headers)
#         if status_resp.json()["status"] != "Succeeded":
#             return func.HttpResponse("Not ready", status_code=202)

#         response = requests.get(results_url, headers=headers)
#         result_json = response.json()

#         transcript = []
#         for phrase in result_json["recognizedPhrases"]:
#             speaker = phrase.get("speaker", "Unknown")
#             text = phrase["nBest"][0]["display"]
#             offset = phrase.get("offset", "PT0S")
#             try:
#                 offset_seconds = round(isodate.parse_duration(offset).total_seconds(), 1)
#             except:
#                 offset_seconds = 0.0
#             transcript.append(f"(Speaker{speaker})[{text}]({offset_seconds})")

#         transcript_text = " ".join(transcript)

#         conn = get_db_connection()
#         cursor = conn.cursor()

#         # BasicInfoから情報取得
#         cursor.execute("""
#             SELECT client_company_name, client_contact_name, meeting_datetime
#             FROM dbo.BasicInfo
#             WHERE meeting_id = ?
#         """, meeting_id)
#         row = cursor.fetchone()
#         if not row:
#             return func.HttpResponse(f"BasicInfo に meeting_id={meeting_id} が見つかりません", status_code=400)

#         client_company_name, client_contact_name, meeting_datetime = row

#         # 既存のレコードがないことを確認
#         cursor.execute("""
#             SELECT COUNT(*) FROM dbo.Meetings WHERE meeting_id = ? AND user_id = ?
#         """, meeting_id, user_id)
#         existing = cursor.fetchone()[0]
#         if existing > 0:
#             return func.HttpResponse(f"Meetings に meeting_id={meeting_id}, user_id={user_id} のレコードが既に存在しています", status_code=400)

#         # INSERT
#         title = "Auto generated meeting"
#         file_path = content_urls[0]
#         file_size = 0
#         duration_seconds = 0

#         insert_sql = """
#         INSERT INTO dbo.Meetings (
#             meeting_id, user_id, title, file_name, file_path,
#             file_size, duration_seconds, status,
#             client_company_name, client_contact_name,
#             meeting_datetime, start_datetime, inserted_datetime,
#             updated_datetime, transcript_text
#         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), ?)
#         """
#         insert_params = (
#             meeting_id, user_id, title, file_name, file_path,
#             file_size, duration_seconds, 'completed',
#             client_company_name, client_contact_name,
#             meeting_datetime, meeting_datetime, transcript_text
#         )

#         cursor.execute(insert_sql, insert_params)
#         conn.commit()

#         return func.HttpResponse("OK", status_code=200)

#     except Exception as e:
#         logging.error(f"Callback error: {str(e)}")
#         return func.HttpResponse("Error", status_code=500)




