import logging
import azure.functions as func
import pyodbc
import os
import struct
import uuid
import re
import requests
import json
import openai
from datetime import datetime, timezone, timedelta
from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from azure.storage.queue import QueueServiceClient
import isodate
import sys
from pathlib import Path

# openai_processing モジュールを import できるように sys.path を調整
sys.path.append(str(Path(__file__).parent))
from openai_processing.openai_completion_step1 import step1_process_transcript
from openai_processing.openai_completion_step2 import evaluate_connection_naturalness_no_period


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

def get_queue_service_client():
    """
    Azure Storage Queue Service Client を取得します。
    """
    try:
        connection_string = os.environ.get("AzureWebJobsStorage")
        if not connection_string:
            raise ValueError("AzureWebJobsStorage 環境変数が設定されていません")
        
        return QueueServiceClient.from_connection_string(connection_string)
    except Exception as e:
        logging.error(f"[Queue Service] 接続エラー: {e}")
        raise

def send_queue_message(queue_name: str, message: dict):
    """
    指定されたキューにメッセージを送信します。
    """
    try:
        queue_service = get_queue_service_client()
        queue_client = queue_service.get_queue_client(queue_name)
        
        # メッセージをJSON文字列に変換
        message_json = json.dumps(message)
        queue_client.send_message(message_json)
        
        logging.info(f"✅ キュー '{queue_name}' にメッセージ送信完了: {message}")
    except Exception as e:
        logging.error(f"❌ キュー '{queue_name}' へのメッセージ送信失敗: {e}")
        raise

def get_naturalness_score(text: str) -> float:
    """
    OpenAI APIを使用して日本語文の自然さを評価し、0.0〜1.0のスコアを返します。
    """
    if not text or not text.strip():
        return 0.5  # 空文字の場合はデフォルトスコア
    
    prompt = f"""
次の日本語文の自然さを評価してください。
語順、意味の流れ、文脈のつながりを考慮し、
0.0〜1.0 のスコアで返答してください。

文：{text}

※スコアのみを返してください（例：0.7）
    """.strip()
    
    try:
        # OpenAI client を初期化
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": "あなたは日本語の文の自然さを評価するAIです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        content = response.choices[0].message.content.strip()
        score = float(content)
        
        return score
    except Exception as e:
        logging.error(f"[OpenAI] API call failed: {e}")
        return 0.5  # 応答異常時のフォールバックスコア

def log_trigger_error(event_type: str, table_name: str, record_id: int, additional_info: str):
    """
    TriggerLog テーブルにエラー情報を記録します。
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            insert_log_query = """
                INSERT INTO dbo.TriggerLog (
                    event_type, table_name, record_id, event_time, additional_info
                ) VALUES (?, ?, ?, GETDATE(), ?)
            """
            cursor.execute(insert_log_query, (
                event_type,
                table_name,
                record_id,
                additional_info[:1000]  # 長すぎる場合は切り捨て
            ))
            conn.commit()
            logging.info("⚠️ TriggerLog にエラー記録を挿入しました")
    except Exception as log_error:
        logging.error(f"🚨 TriggerLog への挿入に失敗: {log_error}")

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

        # ✅ コンテナ名を環境変数で取得し一致しない場合スキップ
        expected_container = os.environ.get("TRANSCRIPTION_CONTAINER")
        if expected_container and container_name != expected_container:
            logging.warning(f"🚫 対象外コンテナ {container_name} → スキップします")
            return

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

        # file_size を取得
        blob_service_client = BlobServiceClient(account_url=f"https://{account_name}.blob.core.windows.net", credential=account_key)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        properties = blob_client.get_blob_properties()
        file_size = properties.size  # バイト数

        # duration_seconds を取得（WAVファイル限定）
        import wave
        import contextlib
        import urllib.request

        temp_wav_path = "/tmp/temp.wav"
        urllib.request.urlretrieve(sas_url, temp_wav_path)

        with contextlib.closing(wave.open(temp_wav_path, 'r')) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration_seconds = int(frames / float(rate))

        logging.info(f"📏 file_size={file_size} bytes, duration_seconds={duration_seconds} sec")

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
            file_size,
            duration_seconds,
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
        log_trigger_error(
            event_type="error",
            table_name="Meetings",
            record_id=meeting_id if 'meeting_id' in locals() else -1,
            additional_info=f"[trigger_transcription_job] {str(e)}"
        )

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
            WHERE status IN ('processing', 'transcribed','step1_completed','step2_completed','step3_completed','step4_completed','step5_completed','step6_completed','step7_completed')
        """)
        rows = cursor.fetchall()

        if not rows:
            logging.info("🎯 対象レコードなし（status = 'processing' または 'transcribed','step1_completed','step2_completed','step3_completed','step4_completed','step5_completed','step6_completed','step7_completed'）")
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

                    # 話者ごとの重複排除リストを作る
                    unique_speakers = list(set(seg["speaker"] for seg in segments))

                    # meeting_id から user_id を取得
                    cursor.execute("SELECT user_id FROM dbo.BasicInfo WHERE meeting_id = ?", (meeting_id,))
                    row = cursor.fetchone()
                    user_id = row[0] if row else None

                    for speaker_name in unique_speakers:
                        # 同じ話者がすでに登録されているかチェック（meeting_id + speaker_name で一意とする）
                        cursor.execute("""
                            SELECT 1 FROM dbo.Speakers
                            WHERE meeting_id = ? AND speaker_name = ? AND deleted_datetime IS NULL
                        """, (meeting_id, speaker_name))
                        exists = cursor.fetchone()
                        if not exists:
                            # 新規登録
                            cursor.execute("""
                                INSERT INTO dbo.Speakers (
                                    speaker_name, speaker_role, user_id, meeting_id,
                                    inserted_datetime, updated_datetime
                                )
                                VALUES (?, NULL, ?, ?, GETDATE(), GETDATE())
                            """, (speaker_name, user_id, meeting_id))
                            logging.info(f"👤 新しい話者をSpeakersテーブルに登録: {speaker_name}")

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

                    # ✅ ステップ1完了 → Meetingsテーブルのステータス更新
                    cursor.execute("""
                        UPDATE dbo.Meetings
                        SET status = 'step1_completed', updated_datetime = GETDATE()
                        WHERE meeting_id = ?
                    """, (meeting_id,))
                    logging.info(f"✅ ステップ1完了 → status=step1_completed に更新 (meeting_id={meeting_id})")
                     # ステップ2: Meetings.status='step1_completed' のデータを対象にスコアリング
                elif current_status == 'step1_completed':
                    cursor.execute("""
                        SELECT line_no, transcript_text_segment
                        FROM dbo.ConversationEnrichmentSegments
                        WHERE meeting_id = ? AND is_filler = 1
                        ORDER BY line_no
                    """, (meeting_id,))
                    filler_segments = cursor.fetchall()

                    if not filler_segments:
                        logging.info(f"🟡 filler セグメントなし → ステータスを step2_completed に更新 (meeting_id={meeting_id})")
                        cursor.execute("""
                            UPDATE dbo.Meetings
                            SET status = 'step2_completed', updated_datetime = GETDATE()
                            WHERE meeting_id = ?
                        """, (meeting_id,))
                        continue

                    for (line_no, text) in filler_segments:
                        # 前後のセグメントを取得
                        cursor.execute("""
                            SELECT transcript_text_segment FROM dbo.ConversationEnrichmentSegments
                            WHERE meeting_id = ? AND line_no = ?
                        """, (meeting_id, line_no - 1))
                        prev_row = cursor.fetchone()
                        prev_text = prev_row[0] if prev_row else ""

                        cursor.execute("""
                            SELECT transcript_text_segment FROM dbo.ConversationEnrichmentSegments
                            WHERE meeting_id = ? AND line_no = ?
                        """, (meeting_id, line_no + 1))
                        next_row = cursor.fetchone()
                        next_text = next_row[0] if next_row else ""

                        front_text = prev_text.strip("。")
                        back_text = next_text.strip("。")
                        bracket_text = text.strip("（）")

                        scores = evaluate_connection_naturalness_no_period(front_text, bracket_text, back_text)
                        front_score = scores.get("front_score", 0.0)
                        back_score = scores.get("back_score", 0.0)

                        # DB更新
                        cursor.execute("""
                            UPDATE dbo.ConversationEnrichmentSegments
                            SET front_score = ?, after_score = ?, updated_datetime = GETDATE()
                            WHERE meeting_id = ? AND line_no = ?
                        """, (front_score, back_score, meeting_id, line_no))

                    # ステータス更新
                    cursor.execute("""
                        UPDATE dbo.Meetings
                        SET status = 'step2_completed', updated_datetime = GETDATE()
                        WHERE meeting_id = ?
                    """, (meeting_id,))
                    logging.info(f"✅ ステップ2完了 → status=step2_completed に更新 (meeting_id={meeting_id})")
                 # ステップ3: Meetings.status='step2_completed' のデータを対象に補完処理
                elif current_status == 'step2_completed':
                    cursor.execute("""
                        SELECT line_no, transcript_text_segment, front_score, after_score
                        FROM dbo.ConversationEnrichmentSegments
                        WHERE meeting_id = ? AND is_filler = 1
                        ORDER BY line_no
                    """, (meeting_id,))
                    filler_segments = cursor.fetchall()

                    if not filler_segments:
                        logging.info(f"🟡 ステップ3: filler セグメントなし → ステータスを step3_completed に更新 (meeting_id={meeting_id})")
                        cursor.execute("""
                            UPDATE dbo.Meetings
                            SET status = 'step3_completed', updated_datetime = GETDATE()
                            WHERE meeting_id = ?
                        """, (meeting_id,))
                        continue

                    for line_no, text, front_score, after_score in filler_segments:
                        bracket_text = text.strip("（）")
                        revised_text = None
                        delete_candidate = None
                        delete_target_line = None  

                        if front_score >= after_score:
                            # 前のセグメントから「最後の文」を取得
                            cursor.execute("""
                                SELECT transcript_text_segment FROM dbo.ConversationEnrichmentSegments
                                WHERE meeting_id = ? AND line_no = ?
                            """, (meeting_id, line_no - 1))
                            prev_row = cursor.fetchone()
                            prev_text = prev_row[0] if prev_row else ""

                            sentences = [s for s in prev_text.strip().split("。") if s]
                            if sentences:
                                selected = sentences[-1].strip() + "。"
                                revised_text = (selected + bracket_text).replace("。", "")
                                delete_candidate = selected
                                delete_target_line = line_no - 1
                        else:
                            # 後のセグメントから最初の文を取得
                            cursor.execute("""
                                SELECT transcript_text_segment FROM dbo.ConversationEnrichmentSegments
                                WHERE meeting_id = ? AND line_no = ?
                            """, (meeting_id, line_no + 1))
                            next_row = cursor.fetchone()
                            next_text = next_row[0] if next_row else ""

                            sentences = [s for s in next_text.strip().split("。") if s]
                            if sentences:
                                selected = sentences[0].strip() + "。"
                                revised_text = (selected + bracket_text).replace("。", "")
                                delete_candidate = selected
                                delete_target_line = line_no + 1

                        # filler 行に revised_text を更新
                        cursor.execute("""
                            UPDATE dbo.ConversationEnrichmentSegments
                            SET revised_text_segment = ?, updated_datetime = GETDATE()
                            WHERE meeting_id = ? AND line_no = ?
                        """, (revised_text, meeting_id, line_no))

                        # delete 対象行に delete_candidate_word を更新
                        if delete_target_line is not None:
                            cursor.execute("""
                                UPDATE dbo.ConversationEnrichmentSegments
                                SET delete_candidate_word = ?, updated_datetime = GETDATE()
                                WHERE meeting_id = ? AND line_no = ?
                            """, (delete_candidate, meeting_id, delete_target_line))

                    # ステータス更新
                    cursor.execute("""
                        UPDATE dbo.Meetings
                        SET status = 'step3_completed', updated_datetime = GETDATE()
                        WHERE meeting_id = ?
                    """, (meeting_id,))
                    logging.info(f"✅ ステップ3完了 → status=step3_completed に更新 (meeting_id={meeting_id})")

                # ステップ4: step3_completed の会議に対して ConversationMergedSegments を生成
                elif current_status == 'step3_completed':
                    # ConversationMergedSegments に既にデータがあればスキップ
                    cursor.execute("""
                        SELECT COUNT(*) FROM dbo.ConversationMergedSegments WHERE meeting_id = ?
                    """, (meeting_id,))
                    if cursor.fetchone()[0] > 0:
                        logging.info(f"🔁 ステップ4スキップ（既にConversationMergedSegmentsあり）meeting_id={meeting_id}")
                        cursor.execute("""
                            UPDATE dbo.Meetings
                            SET status = 'step4_completed', updated_datetime = GETDATE()
                            WHERE meeting_id = ?
                        """, (meeting_id,))
                        continue
                    # ステップ4: step3_completed の会議に対して ConversationMergedSegments を生成      
                    cursor.execute("""
                        SELECT line_no, speaker, transcript_text_segment, revised_text_segment, offset_seconds
                        FROM dbo.ConversationEnrichmentSegments
                        WHERE meeting_id = ?
                        ORDER BY line_no
                    """, (meeting_id,))
                    segments = cursor.fetchall()

                    for idx, (line_no, speaker, transcript_text, revised_text, offset_seconds) in enumerate(segments):
                        # filler（補完先）はスキップ（merged_textは前の行で構成する）
                        if revised_text:
                            continue

                        # delete_candidate_word を取得
                        cursor.execute("""
                            SELECT delete_candidate_word FROM dbo.ConversationEnrichmentSegments
                            WHERE meeting_id = ? AND line_no = ?
                        """, (meeting_id, line_no))
                        del_row = cursor.fetchone()
                        delete_word = del_row[0] if del_row else None

                        # 1行先の revised_text_segment を取得（存在すれば）
                        next_revised = None
                        if idx + 1 < len(segments):
                            next_revised = segments[idx + 1][3]  # revised_text_segment

                        # delete_word を除去し、merged_text を構成
                        cleaned_text = transcript_text.replace(delete_word or "", "")
                        merged_text = cleaned_text
                        if next_revised:
                            merged_text += f"({next_revised})"

                        # INSERT 実行
                        cursor.execute("""
                            INSERT INTO dbo.ConversationMergedSegments (
                                meeting_id, line_no, speaker, offset_seconds, original_text, merged_text,
                                source_segment_ids, inserted_datetime, updated_datetime
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())
                        """, (
                            meeting_id,
                            line_no,
                            speaker,
                            offset_seconds,
                            transcript_text,
                            merged_text,
                            f"{line_no},{line_no + 1}" if next_revised else f"{line_no}"
                        ))

                    cursor.execute("""
                        UPDATE dbo.Meetings
                        SET status = 'step4_completed', updated_datetime = GETDATE()
                        WHERE meeting_id = ?
                    """, (meeting_id,))
                    logging.info(f"✅ ステップ4完了 → status=step4_completed に更新 (meeting_id={meeting_id})")


                # ステップ5: step4_completed の会議に対して 同一話者セグメントを統合し ConversationFinalSegments に挿入
                elif current_status == 'step4_completed':
                    # ConversationFinalSegments に既にデータがあればスキップ
                    cursor.execute("""
                        SELECT COUNT(*) FROM dbo.ConversationFinalSegments WHERE meeting_id = ?
                    """, (meeting_id,))
                    if cursor.fetchone()[0] > 0:
                        logging.info(f"🔁 ステップ5スキップ（既にConversationFinalSegmentsあり）meeting_id={meeting_id}")
                        cursor.execute("""
                            UPDATE dbo.Meetings
                            SET status = 'step5_completed', updated_datetime = GETDATE()
                            WHERE meeting_id = ?
                        """, (meeting_id,))
                        continue

                    # ConversationMergedSegments 取得
                    cursor.execute("""
                        SELECT speaker, merged_text, offset_seconds
                        FROM dbo.ConversationMergedSegments
                        WHERE meeting_id = ?
                        ORDER BY offset_seconds
                    """, (meeting_id,))
                    merged_segments = cursor.fetchall()

                    # 同一話者ごとに文をマージ（重複を除去）
                    final_segments = []
                    current_speaker = None
                    current_offset = None
                    sentence_set = set()
                    sentence_list = []

                    for speaker, text, offset in merged_segments:
                        # 文単位に分割（「。」で区切り）
                        sentences = [s.strip() + "。" for s in text.split("。") if s.strip()]

                        if speaker == current_speaker:
                            for sentence in sentences:
                                if sentence not in sentence_set:
                                    sentence_set.add(sentence)
                                    sentence_list.append(sentence)
                        else:
                            if current_speaker is not None:
                                combined_text = " ".join(sentence_list).strip()
                                final_segments.append((meeting_id, current_speaker, combined_text, current_offset))

                            current_speaker = speaker
                            current_offset = offset
                            sentence_set = set(sentences)
                            sentence_list = sentences.copy()

                    # 最後のセグメントも保存
                    if current_speaker is not None and sentence_list:
                        combined_text = " ".join(sentence_list).strip()
                        final_segments.append((meeting_id, current_speaker, combined_text, current_offset))

                    # ConversationFinalSegments に INSERT
                    for seg in final_segments:
                        cursor.execute("""
                            INSERT INTO dbo.ConversationFinalSegments (
                                meeting_id, speaker, merged_text, offset_seconds, inserted_datetime, updated_datetime
                            ) VALUES (?, ?, ?, ?, GETDATE(), GETDATE())
                        """, seg)

                    # ステータス更新
                    cursor.execute("""
                        UPDATE dbo.Meetings
                        SET status = 'step5_completed', updated_datetime = GETDATE()
                        WHERE meeting_id = ?
                    """, (meeting_id,))
                    logging.info(f"✅ ステップ5完了（重複文排除版）→ status=step5_completed に更新 (meeting_id={meeting_id})")


                # ステップ6: step5_completed の会議に対して フィラー削除処理を実施
                elif current_status == 'step5_completed':
                    cursor.execute("""
                        SELECT id, merged_text
                        FROM dbo.ConversationFinalSegments
                        WHERE meeting_id = ?
                    """, (meeting_id,))
                    segments = cursor.fetchall()

                    if not segments:
                        logging.warning(f"⚠ ステップ6スキップ（ConversationFinalSegmentsが空）meeting_id={meeting_id}")
                        cursor.execute("""
                            UPDATE dbo.Meetings
                            SET status = 'step6_completed', updated_datetime = GETDATE()
                            WHERE meeting_id = ?
                        """, (meeting_id,))
                        continue

                    # フィラー削除処理
                    from openai_processing.openai_completion_step6 import remove_fillers_from_text
                    for segment_id, merged_text in segments:
                        try:
                            cleaned = remove_fillers_from_text(merged_text)
                        except Exception as e:
                            logging.warning(f"❌ フィラー削除失敗 id={segment_id} error={e}")
                            cleaned = merged_text  # フォールバック

                        cursor.execute("""
                            UPDATE dbo.ConversationFinalSegments
                            SET cleaned_text = ?, updated_datetime = GETDATE()
                            WHERE id = ?
                        """, (cleaned, segment_id))

                    # ステータス更新
                    cursor.execute("""
                        UPDATE dbo.Meetings
                        SET status = 'step6_completed', updated_datetime = GETDATE()
                        WHERE meeting_id = ?
                    """, (meeting_id,))
                    logging.info(f"✅ ステップ6完了 → status=step6_completed に更新 (meeting_id={meeting_id})")
                 # ステップ7: step6_completed の会議に対して タイトル要約生成を実行
                elif current_status == 'step6_completed':
                    cursor.execute("""
                        SELECT id, speaker, cleaned_text, offset_seconds
                        FROM dbo.ConversationFinalSegments
                        WHERE meeting_id = ?
                        ORDER BY offset_seconds
                    """, (meeting_id,))
                    rows = cursor.fetchall()

                    if not rows:
                        logging.warning(f"⚠ ステップ7スキップ（データなし）meeting_id={meeting_id}")
                        cursor.execute("""
                            UPDATE dbo.Meetings
                            SET status = 'step7_completed', updated_datetime = GETDATE()
                            WHERE meeting_id = ?
                        """, (meeting_id,))
                        continue

                    # openai_completion_step7 から処理関数をインポート
                    from openai_processing.openai_completion_step7 import generate_summary_title, extract_offset_from_line

                    # テキスト形式に変換してブロック化処理用に準備
                    lines = []
                    for row in rows:
                        segment_id, speaker, text, offset = row
                        if text:
                            lines.append((segment_id, f"Speaker{speaker}: {text}({offset})"))

                    # ブロック化（300秒単位）
                    blocks = []
                    current_block = {
                        "lines": [],
                        "block_index": 0,
                        "start_offset": 0.0
                    }
                    for seg_id, line in lines:
                        body, offset = extract_offset_from_line(line)
                        if offset is None:
                            continue
                        block_index = int(offset // 300)
                        if block_index != current_block["block_index"]:
                            if current_block["lines"]:
                                blocks.append(current_block.copy())
                            current_block = {
                                "lines": [],
                                "block_index": block_index,
                                "start_offset": offset
                            }
                        current_block["lines"].append((seg_id, line))
                    if current_block["lines"]:
                        blocks.append(current_block)

                    # 各ブロックに対してタイトルを生成し、先頭のsummaryにだけ挿入
                    for i, block in enumerate(blocks):
                        lines_only = [line for _, line in block["lines"]]
                        conversation_text = "\n".join(lines_only)
                        title = generate_summary_title(conversation_text, i, len(blocks))
                        first_seg_id = block["lines"][0][0]
                        cursor.execute("""
                            UPDATE dbo.ConversationFinalSegments
                            SET summary = ?, updated_datetime = GETDATE()
                            WHERE id = ?
                        """, (title, first_seg_id))

                    # ステータス更新
                    cursor.execute("""
                        UPDATE dbo.Meetings
                        SET status = 'step7_completed', updated_datetime = GETDATE()
                        WHERE meeting_id = ?
                    """, (meeting_id,))
                    logging.info(f"✅ ステップ7完了 → status=step7_completed に更新 (meeting_id={meeting_id})")
                 # ステップ8: step7_completed の会議に対して ConversationSegments にデータを移行
                elif current_status == 'step7_completed':
                    # ConversationFinalSegments を取得
                    cursor.execute("""
                        SELECT id, speaker, meeting_id, cleaned_text, summary, offset_seconds
                        FROM dbo.ConversationFinalSegments
                        WHERE meeting_id = ?
                        ORDER BY offset_seconds
                    """, (meeting_id,))
                    final_segments = cursor.fetchall()

                    if not final_segments:
                        logging.warning(f"⚠ ステップ8スキップ（ConversationFinalSegmentsなし）meeting_id={meeting_id}")
                        cursor.execute("""
                            UPDATE dbo.Meetings
                            SET status = 'AllStepCompleted', updated_datetime = GETDATE()
                            WHERE meeting_id = ?
                        """, (meeting_id,))
                        continue

                    # Meetingsテーブルからユーザー・音声情報を取得
                    cursor.execute("""
                        SELECT user_id, file_name, file_path, file_size, duration_seconds
                        FROM dbo.Meetings
                        WHERE meeting_id = ?
                    """, (meeting_id,))
                    meeting_row = cursor.fetchone()
                    if not meeting_row:
                        logging.warning(f"⚠ ミーティング情報取得失敗 meeting_id={meeting_id}")
                        continue

                    meeting_user_id, file_name, file_path, file_size, duration_seconds = meeting_row

                    for segment_id, speaker_raw, _, cleaned_text, summary, offset in final_segments:
                        speaker_name = str(speaker_raw)

                        # speaker_id を取得
                        cursor.execute("""
                            SELECT speaker_id FROM dbo.Speakers
                            WHERE meeting_id = ? AND speaker_name = ?
                        """, (meeting_id, speaker_name))
                        speaker_row = cursor.fetchone()
                        speaker_id = speaker_row[0] if speaker_row else 0

                        # サマリがある場合：1行目に summary を挿入（user_id=0, speaker_id=0）
                        if summary:
                            cursor.execute("""
                                INSERT INTO dbo.ConversationSegments (
                                    user_id, speaker_id, meeting_id, content, file_name, file_path, file_size,
                                    duration_seconds, status, inserted_datetime, updated_datetime,
                                    start_time, end_time
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', GETDATE(), GETDATE(), ?, NULL)
                            """, (
                                0, 0, meeting_id, summary,
                                file_name, file_path, file_size,
                                duration_seconds,
                                offset
                            ))

                        # cleaned_text を挿入（常に1回だけ）
                        cursor.execute("""
                            INSERT INTO dbo.ConversationSegments (
                                user_id, speaker_id, meeting_id, content, file_name, file_path, file_size,
                                duration_seconds, status, inserted_datetime, updated_datetime,
                                start_time, end_time
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', GETDATE(), GETDATE(), ?, NULL)
                        """, (
                            meeting_user_id, speaker_id, meeting_id, cleaned_text,
                            file_name, file_path, file_size,
                            duration_seconds,
                            offset
                        ))

                    # ステータス更新
                    cursor.execute("""
                        UPDATE dbo.Meetings
                        SET status = 'AllStepCompleted', updated_datetime = GETDATE()
                        WHERE meeting_id = ?
                    """, (meeting_id,))
                    logging.info(f"✅ ステップ8完了 → status=AllStepCompleted に更新 (meeting_id={meeting_id})")

            except Exception as inner_e:
                logging.exception(f"⚠️ 個別処理エラー (meeting_id={meeting_id}): {inner_e}")
                log_trigger_error(
                    event_type="error",
                    table_name="Meetings",
                    record_id=meeting_id if meeting_id else -1,
                    additional_info=f"[polling_transcription_results_inner] {str(inner_e)}"
                )

        conn.commit()
        logging.info("🔁 Polling 処理完了")

    except Exception as e:
        logging.exception("❌ PollingTranscriptionResults 関数全体でエラーが発生")
        log_trigger_error(
            event_type="error",
            table_name="System",
            record_id=-1,
            additional_info=f"[polling_transcription_results] {str(e)}"
        )

# ============================================================================
# 🔄 Queue Trigger ベースの新しい処理関数群
# ============================================================================

@app.function_name(name="QueuePreprocessingFunc")
@app.queue_trigger(arg_name="message", queue_name="queue-preprocessing", connection="AzureWebJobsStorage")
def queue_preprocessing_func(message: func.QueueMessage):
    """
    ステップ1-3: セグメント化、フィラースコア、補完候補を TranscriptProcessingSegments に保存
    """
    try:
        logging.info("=== QueuePreprocessingFunc 開始 ===")
        
        # メッセージから meeting_id を取得
        message_data = json.loads(message.get_body().decode('utf-8'))
        meeting_id = message_data.get("meeting_id")
        
        if not meeting_id:
            raise ValueError("メッセージに meeting_id が含まれていません")
        
        logging.info(f"🎯 処理対象: meeting_id={meeting_id}")
        
        # ステータスを preprocessing_in_progress に更新
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE dbo.Meetings
            SET status = 'preprocessing_in_progress', updated_datetime = GETDATE()
            WHERE meeting_id = ?
        """, (meeting_id,))
        
        # transcript_text を取得
        cursor.execute("""
            SELECT transcript_text FROM dbo.Meetings WHERE meeting_id = ?
        """, (meeting_id,))
        row = cursor.fetchone()
        
        if not row or not row[0]:
            logging.warning(f"⚠️ transcript_text が存在しません (meeting_id={meeting_id})")
            cursor.execute("""
                UPDATE dbo.Meetings
                SET status = 'preprocessing_completed', updated_datetime = GETDATE()
                WHERE meeting_id = ?
            """, (meeting_id,))
            conn.commit()
            return
        
        transcript_text = row[0]
        
        # ステップ1: セグメント化処理
        segments = step1_process_transcript(transcript_text)
        
        if not segments:
            logging.warning(f"⚠️ ステップ1の出力が空です (meeting_id={meeting_id})")
            cursor.execute("""
                UPDATE dbo.Meetings
                SET status = 'preprocessing_completed', updated_datetime = GETDATE()
                WHERE meeting_id = ?
            """, (meeting_id,))
            conn.commit()
            return
        
        # 話者ごとの重複排除リストを作る
        unique_speakers = list(set(seg["speaker"] for seg in segments))
        
        # meeting_id から user_id を取得
        cursor.execute("SELECT user_id FROM dbo.BasicInfo WHERE meeting_id = ?", (meeting_id,))
        row = cursor.fetchone()
        user_id = row[0] if row else None
        
        # Speakers テーブルに話者を登録
        for speaker_name in unique_speakers:
            cursor.execute("""
                SELECT 1 FROM dbo.Speakers
                WHERE meeting_id = ? AND speaker_name = ? AND deleted_datetime IS NULL
            """, (meeting_id, speaker_name))
            exists = cursor.fetchone()
            if not exists:
                cursor.execute("""
                    INSERT INTO dbo.Speakers (
                        speaker_name, speaker_role, user_id, meeting_id,
                        inserted_datetime, updated_datetime
                    )
                    VALUES (?, NULL, ?, ?, GETDATE(), GETDATE())
                """, (speaker_name, user_id, meeting_id))
                logging.info(f"👤 新しい話者をSpeakersテーブルに登録: {speaker_name}")
        
        # TranscriptProcessingSegments に挿入
        for line_no, seg in enumerate(segments, start=1):
            speaker = seg["speaker"]
            text = seg["text"]
            offset = seg["offset"]
            is_filler = 1 if len(text.strip("（）")) < 10 else 0
            
            cursor.execute("""
                INSERT INTO dbo.TranscriptProcessingSegments (
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
            
            logging.info(f"[DB] Inserted TranscriptProcessingSegment: meeting_id={meeting_id}, line_no={line_no}, speaker={speaker}")
        
        # ステップ2: フィラースコアリング
        cursor.execute("""
            SELECT line_no, transcript_text_segment
            FROM dbo.TranscriptProcessingSegments
            WHERE meeting_id = ? AND is_filler = 1
            ORDER BY line_no
        """, (meeting_id,))
        filler_segments = cursor.fetchall()
        
        for (line_no, text) in filler_segments:
            logging.info(f"[FILLER] Processing line {line_no}, text: '{text}'")
            
            # 前後のセグメントを取得
            cursor.execute("""
                SELECT transcript_text_segment FROM dbo.TranscriptProcessingSegments
                WHERE meeting_id = ? AND line_no = ?
            """, (meeting_id, line_no - 1))
            prev_row = cursor.fetchone()
            prev_text = prev_row[0] if prev_row else ""

            cursor.execute("""
                SELECT transcript_text_segment FROM dbo.TranscriptProcessingSegments
                WHERE meeting_id = ? AND line_no = ?
            """, (meeting_id, line_no + 1))
            next_row = cursor.fetchone()
            next_text = next_row[0] if next_row else ""

            front_text = prev_text.strip("。")
            back_text = next_text.strip("。")
            bracket_text = text.strip("（）")

            # フィラー判定補助カラムの構築
            merged_text_with_prev = ""
            merged_text_with_next = ""

            # merged_text_with_prev: 前のセグメントの最後の文 + 現在の文
            if prev_text and prev_text.strip():
                prev_sentences = [s.strip() for s in prev_text.strip().split("。") if s.strip()]
                if prev_sentences:
                    prev_last_sentence = prev_sentences[-1]
                    merged_text_with_prev = prev_last_sentence + bracket_text
                else:
                    logging.warning(f"[FILLER] No valid sentences found in prev_text")
            else:
                logging.warning(f"[FILLER] Prev text is empty for line {line_no - 1}")

            # merged_text_with_next: 現在の文（。を除く）+ 次のセグメントの最初の文
            if next_text and next_text.strip():
                next_sentences = [s.strip() for s in next_text.strip().split("。") if s.strip()]
                if next_sentences:
                    next_first_sentence = next_sentences[0]
                    merged_text_with_next = bracket_text.strip("。") + next_first_sentence
                else:
                    logging.warning(f"[FILLER] No valid sentences found in next_text")
            else:
                logging.warning(f"[FILLER] Next text is empty for line {line_no + 1}")

            # merged_text_with_prev/nextを使用してOpenAI APIで自然さスコア判定
            front_score = 0.0
            back_score = 0.0
            
            if merged_text_with_prev and merged_text_with_prev.strip():
                try:
                    front_score = get_naturalness_score(merged_text_with_prev)
                except Exception as e:
                    logging.warning(f"[FILLER] Front score calculation failed: {e}")
                    front_score = 0.5  # フォールバックスコア
            else:
                front_score = 0.5

            if merged_text_with_next and merged_text_with_next.strip():
                try:
                    back_score = get_naturalness_score(merged_text_with_next)
                except Exception as e:
                    logging.warning(f"[FILLER] Back score calculation failed: {e}")
                    back_score = 0.5  # フォールバックスコア
            else:
                back_score = 0.5

            # DB更新（補助カラムも含めて）
            cursor.execute("""
                UPDATE dbo.TranscriptProcessingSegments
                SET front_score = ?, after_score = ?, 
                    merged_text_with_prev = ?, merged_text_with_next = ?,
                    updated_datetime = GETDATE()
                WHERE meeting_id = ? AND line_no = ?
            """, (front_score, back_score, merged_text_with_prev, merged_text_with_next, meeting_id, line_no))

            logging.info(f"[FILLER] Updated line {line_no} with scores: front={front_score}, back={back_score}")
        
        # ステップ3: 補完候補挿入
        cursor.execute("""
            SELECT line_no, transcript_text_segment, front_score, after_score
            FROM dbo.TranscriptProcessingSegments
            WHERE meeting_id = ? AND is_filler = 1
            ORDER BY line_no
        """, (meeting_id,))
        filler_segments = cursor.fetchall()
        
        for line_no, text, front_score, after_score in filler_segments:
            logging.info(f"[REVISION] Processing line {line_no}, front_score={front_score}, after_score={after_score}")
            
            # merged_text_with_prev/nextを取得
            cursor.execute("""
                SELECT merged_text_with_prev, merged_text_with_next FROM dbo.TranscriptProcessingSegments
                WHERE meeting_id = ? AND line_no = ?
            """, (meeting_id, line_no))
            row = cursor.fetchone()
            merged_text_with_prev = row[0] if row and row[0] else ""
            merged_text_with_next = row[1] if row and row[1] else ""
            
            delete_candidate = None
            
            # 前後のセグメントを再取得（delete_candidate_word生成用）
            cursor.execute("""
                SELECT transcript_text_segment FROM dbo.TranscriptProcessingSegments
                WHERE meeting_id = ? AND line_no = ?
            """, (meeting_id, line_no - 1))
            prev_row = cursor.fetchone()
            prev_text = prev_row[0] if prev_row else ""

            cursor.execute("""
                SELECT transcript_text_segment FROM dbo.TranscriptProcessingSegments
                WHERE meeting_id = ? AND line_no = ?
            """, (meeting_id, line_no + 1))
            next_row = cursor.fetchone()
            next_text = next_row[0] if next_row else ""
            
            # 前後の文から構成元を抽出
            prev_last_sentence = ""
            next_first_sentence = ""
            
            if prev_text and prev_text.strip():
                prev_sentences = [s.strip() for s in prev_text.strip().split("。") if s.strip()]
                if prev_sentences:
                    prev_last_sentence = prev_sentences[-1]
            
            if next_text and next_text.strip():
                next_sentences = [s.strip() for s in next_text.strip().split("。") if s.strip()]
                if next_sentences:
                    next_first_sentence = next_sentences[0]
            
            # スコアに基づいて補完に使われた文を特定し、その構成元をdelete_candidate_wordに格納
            if front_score > after_score:
                # front_scoreが高い（より自然）→ merged_text_with_prevが採用された
                if merged_text_with_prev and merged_text_with_prev.strip():
                    delete_candidate = prev_last_sentence.rstrip("。") + "。"  # 前の文の最後の文を削除候補とする（語尾に「。」を付与）
                    logging.info(f"[REVISION] Using merged_text_with_prev (front_score={front_score} > after_score={after_score}), delete_candidate: '{delete_candidate}'")
                else:
                    logging.warning(f"[REVISION] merged_text_with_prev is empty")
            else:
                # after_scoreが高い（より自然）→ merged_text_with_nextが採用された
                if merged_text_with_next and merged_text_with_next.strip():
                    delete_candidate = next_first_sentence.rstrip("。") + "。"  # 次の文の最初の文を削除候補とする（語尾に「。」を付与）
                    logging.info(f"[REVISION] Using merged_text_with_next (front_score={front_score} <= after_score={after_score}), delete_candidate: '{delete_candidate}'")
                else:
                    logging.warning(f"[REVISION] merged_text_with_next is empty")
            
            # filler 行に delete_candidate_word のみを更新（revised_text_segment は使用しない）
            cursor.execute("""
                UPDATE dbo.TranscriptProcessingSegments
                SET delete_candidate_word = ?, updated_datetime = GETDATE()
                WHERE meeting_id = ? AND line_no = ?
            """, (delete_candidate, meeting_id, line_no))
        
        # ステータス更新
        cursor.execute("""
            UPDATE dbo.Meetings
            SET status = 'preprocessing_completed', updated_datetime = GETDATE()
            WHERE meeting_id = ?
        """, (meeting_id,))
        
        conn.commit()
        logging.info(f"✅ Preprocessing完了 → status=preprocessing_completed (meeting_id={meeting_id})")
        
        # 次のキューにメッセージ送信
        send_queue_message("queue-merging", {"meeting_id": meeting_id})
        
    except Exception as e:
        logging.exception(f"❌ QueuePreprocessingFunc エラー (meeting_id={meeting_id if 'meeting_id' in locals() else 'unknown'}): {e}")
        log_trigger_error(
            event_type="error",
            table_name="TranscriptProcessingSegments",
            record_id=meeting_id if 'meeting_id' in locals() else -1,
            additional_info=f"[queue_preprocessing_func] {str(e)}"
        )
        
        # エラー時はステータスを failed に更新
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dbo.Meetings
                SET status = 'preprocessing_failed', updated_datetime = GETDATE()
                WHERE meeting_id = ?
            """, (meeting_id,))
            conn.commit()
        except Exception as update_error:
            logging.error(f"❌ ステータス更新失敗: {update_error}")

@app.function_name(name="QueueMergingAndCleanupFunc")
@app.queue_trigger(arg_name="message", queue_name="queue-merging", connection="AzureWebJobsStorage")
def queue_merging_and_cleanup_func(message: func.QueueMessage):
    """
    ステップ4-6: セグメント統合、話者ごと整形、OpenAIフィラー除去 → ProcessedTranscriptSegments に保存
    """
    try:
        logging.info("=== QueueMergingAndCleanupFunc 開始 ===")
        
        # メッセージから meeting_id を取得
        message_data = json.loads(message.get_body().decode('utf-8'))
        meeting_id = message_data.get("meeting_id")
        
        if not meeting_id:
            raise ValueError("メッセージに meeting_id が含まれていません")
        
        logging.info(f"🎯 処理対象: meeting_id={meeting_id}")
        
        # ステータスを merging_in_progress に更新
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE dbo.Meetings
            SET status = 'merging_in_progress', updated_datetime = GETDATE()
            WHERE meeting_id = ?
        """, (meeting_id,))
        
        # TranscriptProcessingSegments からデータ取得（バッチ処理で最適化）
        cursor.execute("""
            SELECT line_no, speaker, transcript_text_segment, merged_text_with_prev, merged_text_with_next, 
                   offset_seconds, delete_candidate_word, front_score, after_score
            FROM dbo.TranscriptProcessingSegments
            WHERE meeting_id = ?
            ORDER BY line_no
        """, (meeting_id,))
        segments = cursor.fetchall()
        
        if not segments:
            logging.warning(f"⚠️ TranscriptProcessingSegments にデータがありません (meeting_id={meeting_id})")
            cursor.execute("""
                UPDATE dbo.Meetings
                SET status = 'merging_completed', updated_datetime = GETDATE()
                WHERE meeting_id = ?
            """, (meeting_id,))
            conn.commit()
            return
        
        # ステップ4: 話者連続ブロック構造でのフィラー除去・文脈補完付きセグメント整形
        
        # ステップ①：発話ブロックの構築（is_filler=Falseの行のみ対象）
        speaker_blocks = []
        current_block = None
        
        for idx, (line_no, speaker, transcript_text, merged_text_with_prev, merged_text_with_next, 
                  offset_seconds, delete_candidate_word, front_score, after_score) in enumerate(segments):
            
            # is_filler判定
            cursor.execute("""
                SELECT is_filler FROM dbo.TranscriptProcessingSegments 
                WHERE meeting_id = ? AND line_no = ?
            """, (meeting_id, line_no))
            is_filler_row = cursor.fetchone()
            is_filler = is_filler_row[0] if is_filler_row else 0
            
            # is_filler=Falseの行のみをブロック対象とする
            if not is_filler:
                if current_block is None:
                    # 新しいブロック開始
                    current_block = {
                        "speaker": speaker,
                        "start_line_no": line_no,
                        "end_line_no": line_no,
                        "start_offset": offset_seconds
                    }
                elif current_block["speaker"] == speaker:
                    # 同一話者のブロック継続
                    current_block["end_line_no"] = line_no
                else:
                    # 話者が変わった場合、前のブロックを保存して新しいブロック開始
                    speaker_blocks.append(current_block)
                    current_block = {
                        "speaker": speaker,
                        "start_line_no": line_no,
                        "end_line_no": line_no,
                        "start_offset": offset_seconds
                    }
        
        # 最後のブロックも忘れずに保存
        if current_block is not None:
            speaker_blocks.append(current_block)
        
        logging.info(f"[STEP4] Created {len(speaker_blocks)} speaker blocks: {speaker_blocks}")
        
        # ステップ②：各ブロック内のマージ済み発話を構築
        processed_blocks = []
        
        for block in speaker_blocks:
            speaker = block["speaker"]
            start_line_no = block["start_line_no"]
            end_line_no = block["end_line_no"]
            start_offset = block["start_offset"]
            
            logging.info(f"[STEP4] Processing block: speaker={speaker}, lines={start_line_no}-{end_line_no}")
            
            # ブロック内の全セグメントを取得（is_filler=Trueも含む）
            cursor.execute("""
                SELECT line_no, transcript_text_segment, merged_text_with_prev, merged_text_with_next,
                       delete_candidate_word, front_score, after_score, is_filler
                FROM dbo.TranscriptProcessingSegments
                WHERE meeting_id = ? AND line_no BETWEEN ? AND ?
                ORDER BY line_no
            """, (meeting_id, start_line_no, end_line_no))
            block_segments = cursor.fetchall()
            
            logging.info(f"[STEP4] Found {len(block_segments)} segments in block {start_line_no}-{end_line_no}")
            
            merged_text_parts = []
            
            for seg_idx, (line_no, transcript_text, merged_text_with_prev, merged_text_with_next,
                         delete_candidate_word, front_score, after_score, is_filler) in enumerate(block_segments):
                
                logging.info(f"[STEP4] Processing segment {line_no}, is_filler={is_filler}, "
                           f"front_score={front_score}, after_score={after_score}")
                
                if not is_filler:
                    # 非フィラー行：そのまま追加
                    merged_text_parts.append(transcript_text)
                    logging.info(f"[STEP4] Added non-filler text: '{transcript_text[:50]}...'")
                    
                    # 前のフィラー行からの補完テキストがある場合は追加
                    if seg_idx > 0:
                        prev_seg = block_segments[seg_idx - 1]
                        prev_line_no, prev_transcript_text, prev_merged_text_with_prev, prev_merged_text_with_next, \
                        prev_delete_candidate_word, prev_front_score, prev_after_score, prev_is_filler = prev_seg
                        
                        if prev_is_filler and prev_after_score >= prev_front_score:
                            # 前のフィラー行がafter_score >= front_scoreの場合、補完テキストを追加
                            if prev_merged_text_with_next and prev_merged_text_with_next.strip():
                                complement_text = f"({prev_merged_text_with_next})"
                            else:
                                complement_text = f"({prev_transcript_text})"
                            
                            merged_text_parts[-1] = f"{merged_text_parts[-1]}{complement_text}"
                            logging.info(f"[STEP4] Added complement from previous filler: '{complement_text[:100]}...'")
                
                else:
                    # フィラー行：補完処理
                    if delete_candidate_word and delete_candidate_word.strip():
                        logging.info(f"[STEP4] Processing filler with delete_candidate_word: '{delete_candidate_word}'")
                        
                        if front_score > after_score:
                            # front_score > after_score: 前の文からdelete_candidate_wordを削除し、merged_text_with_prevを挿入
                            if seg_idx > 0 and merged_text_parts:
                                # 前の文からdelete_candidate_wordを削除
                                delete_pattern = re.escape(delete_candidate_word.strip())
                                prev_text = merged_text_parts[-1]
                                cleaned_prev_text = re.sub(f"{delete_pattern}[。]?\\s*", "", prev_text)
                                
                                logging.info(f"[STEP4] Removed '{delete_candidate_word}' from prev_text: '{prev_text}' -> '{cleaned_prev_text}'")
                                
                                # 補完テキストを結合（前の文に追加）
                                if merged_text_with_prev and merged_text_with_prev.strip():
                                    complement_text = f"({merged_text_with_prev})"
                                else:
                                    complement_text = f"({transcript_text})"
                                
                                merged_text_parts[-1] = f"{cleaned_prev_text}{complement_text}"
                                logging.info(f"[STEP4] Applied front_score > after_score merge: '{merged_text_parts[-1][:100]}...'")
                            
                        elif after_score >= front_score:
                            # after_score >= front_score: 次の文にmerged_text_with_nextを付加し、次のセグメントのdelete_candidate_wordを削除
                            
                            # 次のセグメントが存在し、非フィラーの場合
                            if seg_idx + 1 < len(block_segments):
                                next_seg = block_segments[seg_idx + 1]
                                next_line_no, next_transcript_text, next_merged_text_with_prev, next_merged_text_with_next, \
                                next_delete_candidate_word, next_front_score, next_after_score, next_is_filler = next_seg
                                
                                if not next_is_filler:
                                    # 次の文からdelete_candidate_wordを削除
                                    if next_delete_candidate_word and next_delete_candidate_word.strip():
                                        delete_pattern = re.escape(next_delete_candidate_word.strip())
                                        cleaned_next_text = re.sub(f"{delete_pattern}[。]?\\s*", "", next_transcript_text)
                                        
                                        logging.info(f"[STEP4] Removed '{next_delete_candidate_word}' from next_text: '{next_transcript_text}' -> '{cleaned_next_text}'")
                                        
                                        # 次のセグメントを更新（後で処理される）
                                        block_segments[seg_idx + 1] = (next_line_no, cleaned_next_text, next_merged_text_with_prev, 
                                                                       next_merged_text_with_next, next_delete_candidate_word, 
                                                                       next_front_score, next_after_score, next_is_filler)
                                    
                                    # 次の文に補完テキストを追加
                                    if merged_text_with_next and merged_text_with_next.strip():
                                        complement_text = f"({merged_text_with_next})"
                                    else:
                                        complement_text = f"({transcript_text})"
                                    
                                    # 次のセグメントの処理時に反映されるよう、一時的に保存
                                    # 実際の処理は次のセグメントのループで行われる
                                    logging.info(f"[STEP4] Will add complement to next segment: '{complement_text[:100]}...'")
                                    
                                    # 次のセグメントの処理時に補完テキストを追加するよう、フラグを設定
                                    # この処理は次のセグメントのループで行われる
                                
                            else:
                                # 次のセグメントが存在しない場合
                                logging.info(f"[STEP4] No next segment available for after_score >= front_score merge")
                        
                        else:
                            # スコアが同じ場合やdelete_candidate_wordがNoneの場合
                            logging.info(f"[STEP4] Skipping filler line {line_no} (no clear score difference or no delete_candidate_word)")
                    else:
                        # delete_candidate_wordがNoneの場合
                        logging.info(f"[STEP4] Skipping filler line {line_no} (no delete_candidate_word)")
            
            # ブロック内のテキストを結合
            final_merged_text = " ".join(merged_text_parts).strip()
            
            processed_blocks.append({
                "meeting_id": meeting_id,
                "line_no": start_line_no,  # ブロック内の最初の行を代表として使用
                "speaker": speaker,
                "merged_text": final_merged_text,
                "offset_seconds": start_offset  # ブロック内の最初の行のoffsetを使用
            })
            
            logging.info(f"[STEP4] Final block text: speaker={speaker}, text='{final_merged_text[:100]}...'")
        
        # ステップ③：マージ済みテキストの登録
        for block in processed_blocks:
            cursor.execute("""
                INSERT INTO dbo.ProcessedTranscriptSegments (
                    meeting_id, line_no, speaker, merged_text, offset_seconds,
                    inserted_datetime, updated_datetime
                ) VALUES (?, ?, ?, ?, ?, GETDATE(), GETDATE())
            """, (block["meeting_id"], block["line_no"], block["speaker"], 
                  block["merged_text"], block["offset_seconds"]))
            
            logging.info(f"[DB] Inserted ProcessedTranscriptSegment: meeting_id={block['meeting_id']}, "
                        f"line_no={block['line_no']}, speaker={block['speaker']}, "
                        f"merged_text='{block['merged_text'][:100]}...'")
        
        # ステップ6: OpenAIフィラー除去
        cursor.execute("""
            SELECT id, merged_text
            FROM dbo.ProcessedTranscriptSegments
            WHERE meeting_id = ?
        """, (meeting_id,))
        segments = cursor.fetchall()
        
        # OpenAIクライアントの初期化
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        def improve_text_with_openai(text: str) -> str:
            """
            OpenAI APIを使用して話し言葉を自然で読みやすい文章に整形する
            """
            user_message = f"""以下の文字起こし結果を、できるだけ元の口調や文体（常体・丁寧語）を維持しながら、読みやすく自然な文章に整えてください。

- 「あ、」「うん。」など、一文字＋読点・句点のフィラーは削除してください  
- 話し言葉の崩れ（接続詞の繰り返しや、文の論理のズレなど）は必要最小限の範囲で整えてください  
- 句読点や空白は自然な形に整えてください  
- 常体で話されている部分は常体のまま、丁寧語の部分は丁寧語のままで残してください（例：「ですよ」は「です」に変えないでください）  
- 話者の口癖や語尾の特徴（例：「〜ですよ」「〜だよね」など）はなるべく保持してください  
- 意味の通る自然な構文になる場合には、前後の文脈を読み取って文を補ったり整理して構いません  
- 括弧付きの補完語句（例：「（こんにちは。）」）は削除せずにそのまま保持してください
- あ、あの、えっと、うーん、なんか、そのー、うん、はい、えー、ま、まあ、
- 上記に句読点が付いたパターン（例：「あ、」「うーん。」「えっと、」など）もすべて削除してください
- 不要な接続詞の繰り返し（例：「で、で、」「その、そのー」）も1つにまとめてください

文字起こし結果：
{text}

修正後："""

            try:
                response = client.chat.completions.create(
                    model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
                    messages=[
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.6,  # 話者の口調を保持するため適度な温度に設定
                    max_tokens=300    # 適度な長さの応答に制限
                )

                # トークン使用量を取得（エラーハンドリング付き）
                try:
                    tokens_used = response.usage.total_tokens
                    logging.info(f"🔢 トークン使用量: {tokens_used} (文章整形)")
                except (AttributeError, KeyError):
                    tokens_used = 0

                result = response.choices[0].message.content.strip()
                
                # 「」を削除する処理
                result = result.strip('「」')
                
                # 結果が空でない場合は返す
                if result:
                    return result
                else:
                    return text
                    
            except Exception as e:
                logging.warning(f"文章整形失敗: {e}")
                return text  # フォールバック
        
        for segment_id, merged_text in segments:
            logging.info(f"[CLEANUP] Processing segment_id={segment_id}, merged_text='{merged_text[:100]}...'")
            try:
                cleaned = improve_text_with_openai(merged_text)
                logging.info(f"[CLEANUP] Improved text: '{cleaned[:100]}...'")
            except Exception as e:
                logging.warning(f"❌ 文章整形失敗 id={segment_id} error={e}")
                cleaned = merged_text  # フォールバック
            
            cursor.execute("""
                UPDATE dbo.ProcessedTranscriptSegments
                SET cleaned_text = ?, updated_datetime = GETDATE()
                WHERE id = ?
            """, (cleaned, segment_id))
            logging.info(f"[DB] Updated ProcessedTranscriptSegment: id={segment_id}, cleaned_text='{cleaned[:100]}...'")
        
        # ステータス更新
        cursor.execute("""
            UPDATE dbo.Meetings
            SET status = 'merging_completed', updated_datetime = GETDATE()
            WHERE meeting_id = ?
        """, (meeting_id,))
        
        conn.commit()
        logging.info(f"✅ MergingAndCleanup完了 → status=merging_completed (meeting_id={meeting_id})")
        
        # 次のキューにメッセージ送信
        send_queue_message("queue-summary", {"meeting_id": meeting_id})
        
    except Exception as e:
        logging.exception(f"❌ QueueMergingAndCleanupFunc エラー (meeting_id={meeting_id if 'meeting_id' in locals() else 'unknown'}): {e}")
        log_trigger_error(
            event_type="error",
            table_name="ProcessedTranscriptSegments",
            record_id=meeting_id if 'meeting_id' in locals() else -1,
            additional_info=f"[queue_merging_and_cleanup_func] {str(e)}"
        )
        
        # エラー時はステータスを failed に更新
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dbo.Meetings
                SET status = 'merging_failed', updated_datetime = GETDATE()
                WHERE meeting_id = ?
            """, (meeting_id,))
            conn.commit()
        except Exception as update_error:
            logging.error(f"❌ ステータス更新失敗: {update_error}")

@app.function_name(name="QueueSummarizationFunc")
@app.queue_trigger(arg_name="message", queue_name="queue-summary", connection="AzureWebJobsStorage")
def queue_summarization_func(message: func.QueueMessage):
    """
    ステップ7: ブロック要約タイトル生成 → ConversationSummaries に保存
    """
    try:
        logging.info("=== QueueSummarizationFunc 開始 ===")
        
        # メッセージから meeting_id を取得
        message_data = json.loads(message.get_body().decode('utf-8'))
        meeting_id = message_data.get("meeting_id")
        
        if not meeting_id:
            raise ValueError("メッセージに meeting_id が含まれていません")
        
        logging.info(f"🎯 処理対象: meeting_id={meeting_id}")
        
        # ステータスを summary_in_progress に更新
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE dbo.Meetings
            SET status = 'summary_in_progress', updated_datetime = GETDATE()
            WHERE meeting_id = ?
        """, (meeting_id,))
        
        # ProcessedTranscriptSegments からデータ取得
        cursor.execute("""
            SELECT id, speaker, cleaned_text, offset_seconds
            FROM dbo.ProcessedTranscriptSegments
            WHERE meeting_id = ?
            ORDER BY offset_seconds
        """, (meeting_id,))
        rows = cursor.fetchall()
        
        if not rows:
            logging.warning(f"⚠️ ProcessedTranscriptSegments にデータがありません (meeting_id={meeting_id})")
            cursor.execute("""
                UPDATE dbo.Meetings
                SET status = 'summary_completed', updated_datetime = GETDATE()
                WHERE meeting_id = ?
            """, (meeting_id,))
            conn.commit()
            return
        
        # openai_completion_step7 から処理関数をインポート
        from openai_processing.openai_completion_step7 import generate_summary_title, extract_offset_from_line
        
        # テキスト形式に変換してブロック化処理用に準備
        lines = []
        for row in rows:
            segment_id, speaker, text, offset = row
            if text:
                lines.append((segment_id, f"Speaker{speaker}: {text}({offset})"))
        
        # ブロック化（300秒単位）
        blocks = []
        current_block = {
            "lines": [],
            "block_index": 0,
            "start_offset": 0.0
        }
        for seg_id, line in lines:
            body, offset = extract_offset_from_line(line)
            if offset is None:
                continue
            block_index = int(offset // 300)
            if block_index != current_block["block_index"]:
                if current_block["lines"]:
                    blocks.append(current_block.copy())
                current_block = {
                    "lines": [],
                    "block_index": block_index,
                    "start_offset": offset
                }
            current_block["lines"].append((seg_id, line))
        if current_block["lines"]:
            blocks.append(current_block)
        
        # 各ブロックに対してタイトルを生成し、ConversationSummaries に挿入
        for i, block in enumerate(blocks):
            lines_only = [line for _, line in block["lines"]]
            conversation_text = "\n".join(lines_only)
            title = generate_summary_title(conversation_text, i, len(blocks))
            
            # サマリ行を挿入
            cursor.execute("""
                INSERT INTO dbo.ConversationSummaries (
                    meeting_id, speaker, content, offset_seconds, is_summary,
                    inserted_datetime, updated_datetime
                ) VALUES (?, ?, ?, ?, ?, GETDATE(), GETDATE())
            """, (meeting_id, 0, title, block["start_offset"], 1))
            
            # 各セグメントも挿入
            for seg_id, line in block["lines"]:
                body, offset = extract_offset_from_line(line)
                speaker = int(line.split(":")[0].replace("Speaker", ""))
                content = line.split(":")[1].split("(")[0].strip()
                
                cursor.execute("""
                    INSERT INTO dbo.ConversationSummaries (
                        meeting_id, speaker, content, offset_seconds, is_summary,
                        inserted_datetime, updated_datetime
                    ) VALUES (?, ?, ?, ?, ?, GETDATE(), GETDATE())
                """, (meeting_id, speaker, content, offset, 0))
        
        # ステータス更新
        cursor.execute("""
            UPDATE dbo.Meetings
            SET status = 'summary_completed', updated_datetime = GETDATE()
            WHERE meeting_id = ?
        """, (meeting_id,))
        
        conn.commit()
        logging.info(f"✅ Summarization完了 → status=summary_completed (meeting_id={meeting_id})")
        
        # 次のキューにメッセージ送信
        send_queue_message("queue-export", {"meeting_id": meeting_id})
        
    except Exception as e:
        logging.exception(f"❌ QueueSummarizationFunc エラー (meeting_id={meeting_id if 'meeting_id' in locals() else 'unknown'}): {e}")
        log_trigger_error(
            event_type="error",
            table_name="ConversationSummaries",
            record_id=meeting_id if 'meeting_id' in locals() else -1,
            additional_info=f"[queue_summarization_func] {str(e)}"
        )
        
        # エラー時はステータスを failed に更新
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dbo.Meetings
                SET status = 'summary_failed', updated_datetime = GETDATE()
                WHERE meeting_id = ?
            """, (meeting_id,))
            conn.commit()
        except Exception as update_error:
            logging.error(f"❌ ステータス更新失敗: {update_error}")

@app.function_name(name="QueueExportFunc")
@app.queue_trigger(arg_name="message", queue_name="queue-export", connection="AzureWebJobsStorage")
def queue_export_func(message: func.QueueMessage):
    """
    ステップ8: ConversationSummaries から ConversationSegments にコピー
    """
    try:
        logging.info("=== QueueExportFunc 開始 ===")
        
        # メッセージから meeting_id を取得
        message_data = json.loads(message.get_body().decode('utf-8'))
        meeting_id = message_data.get("meeting_id")
        
        if not meeting_id:
            raise ValueError("メッセージに meeting_id が含まれていません")
        
        logging.info(f"🎯 処理対象: meeting_id={meeting_id}")
        
        # ステータスを export_in_progress に更新
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE dbo.Meetings
            SET status = 'export_in_progress', updated_datetime = GETDATE()
            WHERE meeting_id = ?
        """, (meeting_id,))
        
        # ConversationSummaries からデータ取得
        cursor.execute("""
            SELECT speaker, content, offset_seconds, is_summary
            FROM dbo.ConversationSummaries
            WHERE meeting_id = ?
            ORDER BY offset_seconds, is_summary DESC
        """, (meeting_id,))
        summaries = cursor.fetchall()
        
        if not summaries:
            logging.warning(f"⚠️ ConversationSummaries にデータがありません (meeting_id={meeting_id})")
            cursor.execute("""
                UPDATE dbo.Meetings
                SET status = 'AllStepCompleted', updated_datetime = GETDATE()
                WHERE meeting_id = ?
            """, (meeting_id,))
            conn.commit()
            return
        
        # Meetingsテーブルからユーザー・音声情報を取得
        cursor.execute("""
            SELECT user_id, file_name, file_path, file_size, duration_seconds
            FROM dbo.Meetings
            WHERE meeting_id = ?
        """, (meeting_id,))
        meeting_row = cursor.fetchone()
        if not meeting_row:
            logging.warning(f"⚠️ ミーティング情報取得失敗 meeting_id={meeting_id}")
            return
        
        meeting_user_id, file_name, file_path, file_size, duration_seconds = meeting_row
        
        # ConversationSegments にデータを挿入
        for speaker_raw, content, offset, is_summary in summaries:
            speaker_name = str(speaker_raw)
            
            # speaker_id を取得
            speaker_id = 0
            if not is_summary:
                cursor.execute("""
                    SELECT speaker_id FROM dbo.Speakers
                    WHERE meeting_id = ? AND speaker_name = ?
                """, (meeting_id, speaker_name))
                speaker_row = cursor.fetchone()
                speaker_id = speaker_row[0] if speaker_row else 0
            
            # ConversationSegments に挿入
            cursor.execute("""
                INSERT INTO dbo.ConversationSegments (
                    user_id, speaker_id, meeting_id, content, file_name, file_path, file_size,
                    duration_seconds, status, inserted_datetime, updated_datetime,
                    start_time, end_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', GETDATE(), GETDATE(), ?, NULL)
            """, (
                meeting_user_id if not is_summary else 0,
                speaker_id,
                meeting_id,
                content,
                file_name,
                file_path,
                file_size,
                duration_seconds,
                offset
            ))
        
        # ステータス更新
        cursor.execute("""
            UPDATE dbo.Meetings
            SET status = 'AllStepCompleted', updated_datetime = GETDATE()
            WHERE meeting_id = ?
        """, (meeting_id,))
        
        conn.commit()
        logging.info(f"✅ Export完了 → status=AllStepCompleted (meeting_id={meeting_id})")
        
    except Exception as e:
        logging.exception(f"❌ QueueExportFunc エラー (meeting_id={meeting_id if 'meeting_id' in locals() else 'unknown'}): {e}")
        log_trigger_error(
            event_type="error",
            table_name="ConversationSegments",
            record_id=meeting_id if 'meeting_id' in locals() else -1,
            additional_info=f"[queue_export_func] {str(e)}"
        )
        
        # エラー時はステータスを failed に更新
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE dbo.Meetings
                SET status = 'export_failed', updated_datetime = GETDATE()
                WHERE meeting_id = ?
            """, (meeting_id,))
            conn.commit()
        except Exception as update_error:
            logging.error(f"❌ ステータス更新失敗: {update_error}")