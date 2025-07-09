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
from openai_processing.openai_completion_step2 import evaluate_connection_naturalness_no_period
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
            WHERE status IN ('processing', 'transcribed','step1_completed','step2_completed','step3_completed','step4_completed','step5_completed','step6_completed','step7_completed')
        """)
        rows = cursor.fetchall()

        if not rows:
            logging.info("🎯 対象レコードなし（status = 'processing' または 'transcribed','step1_completed','step2_completed','step3_completed','step4_completed','step5_completed'）")
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
                        logging.info(f"🟡 filler セグメントなし → スキップ (meeting_id={meeting_id})")
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
                        logging.info(f"🟡 ステップ3: filler セグメントなし → スキップ (meeting_id={meeting_id})")
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
                # function_app.py の PollingTranscriptionResults 関数内、step3 完了直後に追加

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
                            SET status = 'step8_completed', updated_datetime = GETDATE()
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
                        SET status = 'step8_completed', updated_datetime = GETDATE()
                        WHERE meeting_id = ?
                    """, (meeting_id,))
                    logging.info(f"✅ ステップ8完了 → status=step8_completed に更新 (meeting_id={meeting_id})")

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




