import azure.functions as func
import logging
import os
import tempfile
import uuid
import time
import re
from datetime import datetime, UTC, timedelta
from azure.cognitiveservices.speech import (
    SpeechConfig,
    AudioConfig,
    SpeechRecognizer,
    ResultReason,
    PropertyId
)
from azure.data.tables import TableClient
from azure.identity import DefaultAzureCredential, ClientSecretCredential
import traceback
from azure.storage.blob import BlobServiceClient, BlobClient, BlobSasPermissions, generate_blob_sas
import subprocess
import shutil
import wave
import requests
import pyodbc
from typing import Optional, Dict, List, Any
import sys
import struct
import json
import base64
from azure.eventgrid import EventGridEvent

# Base64デコード用のヘルパー関数
def safe_base64_decode(data: str) -> bytes:
    """
    Base64デコードを安全に行う関数
    Args:
        data (str): デコードするBase64文字列
    Returns:
        bytes: デコードされたバイト列
    """
    # 余分な空白や改行を削除
    data = data.strip()
    # パディングを補正
    padding = '=' * (4 - len(data) % 4)
    return base64.b64decode(data + padding)

# デバッグログの設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# 環境変数の確認
def check_environment_variables():
    required_env_vars = ["SPEECH_KEY", "SPEECH_REGION", "AzureWebJobsStorage"]
    for var in required_env_vars:
        if not os.environ.get(var):
            logger.error(f"Missing required environment variable: {var}")
        else:
            logger.info(f"Environment variable {var} is set")

# Speech Serviceの設定確認
def configure_speech_service():
    try:
        logger.info("=== Speech Service Configuration Start ===")
        speech_key = os.environ["SPEECH_KEY"]
        speech_region = os.environ["SPEECH_REGION"]
        
        logger.info(f"Using region: {speech_region}")
        
        # SpeechConfigの作成
        speech_config = SpeechConfig(
            subscription=speech_key,
            region=speech_region
        )
        
        # 話者分離機能を有効化（set_property_by_nameを使用）
        logger.info("Attempting to enable diarization")
        speech_config.set_property_by_name(
            "SpeechServiceConnection.EnableDiarization",
            "true"
        )
        speech_config.set_property_by_name(
            "SpeechServiceConnection.SpeakerCount",
            "2"
        )
        
        # 設定の確認（get_property_by_nameを使用）
        diarization_enabled = speech_config.get_property_by_name("SpeechServiceConnection.EnableDiarization")
        speaker_count = speech_config.get_property_by_name("SpeechServiceConnection.SpeakerCount")
        logger.info(f"Diarization enabled: {diarization_enabled}")
        logger.info(f"Speaker count: {speaker_count}")
        
        logger.info("=== Speech Service Configuration Complete ===")
        return speech_config
    except Exception as e:
        logger.error(f"Failed to configure Speech Service: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        raise

# 音声ファイルの処理確認
def check_audio_file(file_path):
    logger.info(f"=== Audio File Check Start ===")
    logger.info(f"Processing audio file: {file_path}")
    logger.info(f"File exists: {os.path.exists(file_path)}")
    if os.path.exists(file_path):
        logger.info(f"File size: {os.path.getsize(file_path)} bytes")
        try:
            with wave.open(file_path, 'rb') as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                frames = wav_file.getnframes()
                duration = frames / float(frame_rate)
                logger.info(f"Audio file details:")
                logger.info(f"- Channels: {channels}")
                logger.info(f"- Sample width: {sample_width} bytes")
                logger.info(f"- Frame rate: {frame_rate} Hz")
                logger.info(f"- Duration: {duration:.2f} seconds")
        except Exception as e:
            logger.error(f"Failed to read audio file: {str(e)}")
    logger.info(f"=== Audio File Check Complete ===")

# データベース接続確認
def check_database_connection(meetingsTable):
    logger.info("=== Database Connection Check Start ===")
    try:
        # テスト用のデータを挿入
        test_data = {
            "meeting_id": 0,
            "user_id": 0,
            "title": "Test Connection",
            "status": "test",
            "inserted_datetime": datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
        }
        meetingsTable.set(func.SqlRow(test_data))
        logger.info("Database connection test successful")
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
    logger.info("=== Database Connection Check Complete ===")

def convert_webm_to_wav(webm_path: str) -> str:
    """
    WebMファイルをWAVファイルに変換する
    """
    try:
        logger.info(f"Converting WebM to WAV: {webm_path}")
        wav_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
        
        # ffmpegを使用してWebMからWAVに変換
        result = subprocess.run([
            'ffmpeg', '-i', webm_path,
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-ar', '16000',          # 16kHz
            '-ac', '1',              # モノラル
            '-y',                    # 上書き
            wav_path
        ], check=True, capture_output=True, text=True)
        
        logger.info(f"ffmpeg conversion completed. Output: {result.stdout}")
        
        # 変換後のファイルを確認
        if os.path.exists(wav_path):
            logger.info(f"Successfully converted to WAV: {wav_path}")
            # 変換後のWAVファイルの情報を確認
            with wave.open(wav_path, 'rb') as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                frames = wav_file.getnframes()
                duration = frames / float(frame_rate)
                logger.info(f"Converted WAV file details:")
                logger.info(f"- Channels: {channels} (should be 1 for mono)")
                logger.info(f"- Sample width: {sample_width} bytes (should be 2 for 16-bit)")
                logger.info(f"- Frame rate: {frame_rate} Hz (should be 16000)")
                logger.info(f"- Duration: {duration:.2f} seconds")
                logger.info(f"- File size: {os.path.getsize(wav_path)} bytes")
            
            return wav_path
        else:
            raise RuntimeError("WAV conversion failed: output file not found")
            
    except subprocess.CalledProcessError as e:
        error_message = f"Failed to convert WebM to WAV: {e.stderr}"
        logger.error(error_message)
        raise RuntimeError(error_message)
    except Exception as e:
        error_message = f"Error in convert_webm_to_wav: {str(e)}"
        logger.error(error_message)
        raise RuntimeError(error_message)

@app.function_name(name="TriggerTranscriptionJob")
@app.event_grid_trigger(arg_name="event")
def trigger_transcription_job(event: func.EventGridEvent):
    """Blobアップロード完了時に発火し、Speech-to-Text非同期ジョブを作成する関数"""
    try:
        logger.info("=== Transcription Job Trigger Start ===")
        
        # event.get_json() or event自体がdict
        body = event.get_json() if hasattr(event, "get_json") else event
        logger.debug(f"Event body: {body}")

        # イベントが配列の場合は最初のイベントを使用
        if isinstance(body, list):
            body = body[0]
            
        data = body.get("data", body)  # fallback対応
        blob_url = data["url"]
        logger.info(f"Received blob URL: {blob_url}")

        if not blob_url:
            raise ValueError("Blob URL not found in event data")

        # BlobのURLからコンテナ名とBLOB名を抽出
        path_parts = blob_url.split('/')
        container_name = path_parts[-2]  # コンテナ名
        blob_name = path_parts[-1]       # Blobファイル名
        
        logger.info(f"コンテナ名: {container_name}, Blob名: {blob_name}")

        # BlobServiceClientの作成
        blob_service_client = BlobServiceClient.from_connection_string(os.environ["AzureWebJobsStorage"])
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        
        # 一時ファイルの作成
        temp_webm_path = os.path.join(tempfile.gettempdir(), blob_name)
        with open(temp_webm_path, "wb") as temp_file:
            blob_data = blob_client.download_blob()
            blob_data.readinto(temp_file)
        
        # WebMからWAVに変換
        temp_wav_path = convert_webm_to_wav(temp_webm_path)
        
        # 変換したWAVファイルを新しいBlobとしてアップロード
        wav_blob_name = f"{os.path.splitext(blob_name)[0]}.wav"
        wav_blob_client = blob_service_client.get_blob_client(container=container_name, blob=wav_blob_name)
        
        # アップロード前の存在確認ログ
        logger.info(f"アップロード前のWAVファイル存在チェック: {os.path.exists(temp_wav_path)} / サイズ: {os.path.getsize(temp_wav_path) if os.path.exists(temp_wav_path) else 'N/A'}")
        
        with open(temp_wav_path, "rb") as wav_file:
            wav_blob_client.upload_blob(wav_file, overwrite=True)
            logger.info(f"WAVファイルをBlobにアップロードしました: {wav_blob_name}")
            logger.info(f"アップロード先URL: {wav_blob_client.url}")
        
        # SASトークンの生成
        connection_string = os.environ["AzureWebJobsStorage"]
        
        # より安全な方法でaccount_keyを抽出
        account_key = None
        for part in connection_string.split(';'):
            if part.startswith('AccountKey='):
                account_key = part.replace('AccountKey=', '').strip()
                break
        
        if not account_key:
            raise ValueError("AccountKey not found in connection string")
            
        # Base64の検証
        try:
            key_bytes = safe_base64_decode(account_key)
            logger.info("✅ Base64として正しい形式です")
            logger.info(f"account_key: {account_key}")  # デバッグ用に出力
        except Exception as e:
            logger.error(f"❌ Base64エラー: {e}")
            logger.error(f"account_key: {account_key}")
            raise
        
        # account_nameの抽出も同様に安全に
        account_name = None
        for part in connection_string.split(';'):
            if part.startswith('AccountName='):
                account_name = part.replace('AccountName=', '')
                break
                
        if not account_name:
            raise ValueError("AccountName not found in connection string")
            
        logger.info(f"Generating SAS token for account: {account_name}")
        
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=wav_blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )
        
        # SASトークン付きのURLを生成
        wav_blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{wav_blob_name}?{sas_token}"
        logger.info(f"WAV file uploaded successfully with SAS token: {wav_blob_url}")
        
        # 一時ファイルの削除
        try:
            if os.path.exists(temp_webm_path):
                try:
                    os.remove(temp_webm_path)
                    logger.info(f"一時WebMファイルを削除しました: {temp_webm_path}")
                except Exception as e:
                    logger.warning(f"一時WebMファイルの削除に失敗: {str(e)}")
            
            if os.path.exists(temp_wav_path):
                try:
                    os.remove(temp_wav_path)
                    logger.info(f"一時WAVファイルを削除しました: {temp_wav_path}")
                except Exception as e:
                    logger.warning(f"一時WAVファイルの削除に失敗: {str(e)}")
        except Exception as e:
            logger.error(f"一時ファイルの削除中にエラーが発生: {str(e)}")

        # Speech-to-Text APIの設定
        speech_key = os.environ["SPEECH_KEY"]
        region = os.environ["SPEECH_REGION"]
        endpoint = f"https://{region}.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions"
        callback_url = os.environ.get("TRANSCRIPTION_CALLBACK_URL")
        
        # 環境変数の確認ログ
        logger.info(f"環境変数 TRANSCRIPTION_CALLBACK_URL: {callback_url}")
        
        if not callback_url:
            error_message = "TRANSCRIPTION_CALLBACK_URL is not set in environment variables"
            logger.error(error_message)
            return
            
        logger.info(f"Using callback URL: {callback_url}")

        # リクエストペイロードの作成
        payload = {
            "contentUrls": [wav_blob_url],
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

        # リクエスト内容のログ出力
        logger.info("Sending request to Speech-to-Text API")
        logger.info("Request payload:")
        logger.info(json.dumps(payload, indent=2, ensure_ascii=False))
        
        response = requests.post(endpoint, headers=headers, json=payload)
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response content: {response.text}")
        response.raise_for_status()
        
        # ジョブ作成レスポンスのログ出力
        logger.info("=== Transcription Job Response ===")
        logger.info(json.dumps(response.json(), indent=2))
        
        # レスポンスの解析
        response_data = response.json()
        job_id = response_data.get("self", "").split("/")[-1]
        logger.info(f"Transcription job created successfully. Job ID: {job_id}")
        logger.info(f"Job details: {response_data}")
        
        # Event Grid Trigger 関数は値を返してはいけない
        return

    except requests.exceptions.RequestException as e:
        error_message = f"Failed to create transcription job: {str(e)}"
        logger.error(error_message)
        if hasattr(e, 'response') and e.response:
            logger.error(f"Response content: {e.response.text}")
        # Event Grid Trigger 関数は値を返してはいけない
        return
        
    except Exception as e:
        error_message = f"Error in trigger_transcription_job: {str(e)}"
        logger.error(error_message)
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        # Event Grid Trigger 関数は値を返してはいけない
        return
        
    finally:
        logger.info("=== Transcription Job Trigger End ===")

# 定数の定義
MAX_LOG_LENGTH = 1000

def insert_trigger_log(meeting_id: int, event_type: str, additional_info: str) -> None:
    """
    TriggerLogテーブルに安全にログを挿入する
    
    Args:
        meeting_id (int): 会議ID
        event_type (str): イベントタイプ（'ERROR', 'INFO', 'SKIP'など）
        additional_info (str): 追加情報（エラーメッセージなど）
    """
    if meeting_id is None:
        logger.warning("⚠ meeting_id is None – TriggerLog insert skipped.")
        return
        
    try:
        # エラーメッセージを最大長で切り詰め
        truncated_info = additional_info[:MAX_LOG_LENGTH] if additional_info else ""
        
        execute_query(
            """
            INSERT INTO dbo.TriggerLog (
                event_type, table_name, record_id, event_time, additional_info
            ) VALUES (?, ?, ?, GETDATE(), ?)
            """,
            (event_type, "Meetings", meeting_id, truncated_info)
        )
        logger.info(f"✅ TriggerLog inserted successfully for meeting_id: {meeting_id}")
    except Exception as e:
        logger.error(f"❌ Failed to insert TriggerLog: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")

@app.function_name(name="TranscriptionCallback")
@app.route(route="transcription-callback", methods=["POST"])
def transcription_callback(req: func.HttpRequest) -> func.HttpResponse:
    """
    Speech Service から transcription 完了通知を受け取る
    結果 JSON のダウンロード → 話者分離結果を整形 → Meetings テーブルに保存
    """
    meeting_id = None  # 関数の先頭で初期化
    user_id = None     # user_idも初期化
    temp_wav_path = None  # 一時ファイルパスを初期化
    try:
        logger.info("=== Transcription Callback Start ===")
        
        # リクエストボディの取得と検証
        try:
            data = req.get_json()
            logger.info(f"Received webhook data: {data}")
        except ValueError as e:
            error_message = f"Invalid JSON in request body: {str(e)}"
            logger.error(error_message)
            insert_trigger_log(meeting_id, "ERROR", error_message)
            return func.HttpResponse(error_message, status_code=400)
            
        # 必須フィールドの検証
        required_fields = ["self", "contentUrls", "resultsUrls", "status"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            error_message = f"Missing required fields: {', '.join(missing_fields)}"
            logger.error(error_message)
            insert_trigger_log(meeting_id, "ERROR", error_message)
            return func.HttpResponse(error_message, status_code=400)
            
        transcription_url = data["self"]
        content_urls = data["contentUrls"]
        results_url = data["resultsUrls"].get("channel_0")
        
        if not results_url:
            error_message = "Missing channel_0 in resultsUrls"
            logger.error(error_message)
            insert_trigger_log(meeting_id, "ERROR", error_message)
            return func.HttpResponse(error_message, status_code=400)
            
        logger.info(f"Webhook called. Transcription job URL: {transcription_url}")
        
        # 1. ファイル名からmeeting_idとuser_idを抽出（先に実行）
        file_name = content_urls[0].split('/')[-1]
        file_path = f"{content_urls[0].split('/')[-2]}/{file_name}"
        logger.info(f"Processing file: {file_name}")
        logger.info(f"File path: {file_path}")
        
        match = re.search(r"meeting_(\d+)_user_(\d+)", file_name)
        if not match:
            error_message = f"Invalid file name format: {file_name}"
            logger.error(error_message)
            insert_trigger_log(meeting_id, "ERROR", error_message)
            return func.HttpResponse(error_message, status_code=400)
            
        meeting_id = int(match.group(1))
        user_id = int(match.group(2))
        logger.info(f"Extracted meeting_id: {meeting_id}, user_id: {user_id}")

        # BasicInfoからクライアント情報を取得（pyodbc方式）
        client_info = get_client_info(meeting_id)
        if not client_info:
            logger.warning(f"No client info found for meeting_id: {meeting_id}")
            client_company_name = "不明企業"
            client_contact_name = "不明担当者"
        else:
            client_company_name = client_info["client_company_name"]
            client_contact_name = client_info["client_contact_name"]
            logger.info(f"Found client info - Company: {client_company_name}, Contact: {client_contact_name}")

        headers = {
            "Ocp-Apim-Subscription-Key": os.environ["SPEECH_KEY"]
        }

        # transcription status を取得
        logger.info(f"Fetching transcription status from: {transcription_url}")
        status_resp = requests.get(transcription_url, headers=headers)
        status_resp.raise_for_status()
        status_json = status_resp.json()
        logger.info(f"Transcription status: {status_json['status']}")

        if status_json["status"] != "Succeeded":
            logger.warning(f"Transcription job not succeeded: {status_json['status']}")
            return func.HttpResponse(status_code=202)

        # 文字起こし結果の取得と検証
        logger.info(f"Fetching transcription results from: {results_url}")
        response = requests.get(results_url, headers=headers)
        response.raise_for_status()  # HTTPエラーのチェック
        
        if not response.content.strip():
            logger.error("❌ Speech-to-Text 結果のレスポンスが空です")
            logger.error(f"Response status code: {response.status_code}")
            logger.error(f"Response headers: {response.headers}")
            return func.HttpResponse("Empty transcription result", status_code=502)
            
        try:
            result_json = response.json()
            logger.info("Successfully retrieved and parsed transcription results")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse transcription results as JSON: {str(e)}")
            logger.error(f"Response content: {response.content[:1000]}...")  # 最初の1000文字だけログ出力
            return func.HttpResponse("Invalid JSON in transcription result", status_code=502)

        transcript = []
        for phrase in result_json["recognizedPhrases"]:
            speaker = phrase.get("speaker", "Unknown")
            text = phrase["nBest"][0]["display"]
            transcript.append(f"(Speaker{speaker})[{text}]")

        transcript_text = " ".join(transcript)
        logger.info(f"Generated transcript text: {transcript_text[:100]}...")  # 最初の100文字だけログ出力

        # ファイル名から日時を抽出
        datetime_match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3})", file_name)
        meeting_datetime = datetime.strptime(datetime_match.group(1), "%Y-%m-%dT%H-%M-%S-%f") if datetime_match else datetime.now(UTC)

        # Blob Storageからファイル情報を取得
        blob_service_client = BlobServiceClient.from_connection_string(os.environ["AzureWebJobsStorage"])
        container_name = file_path.split('/')[0]
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)
        blob_properties = blob_client.get_blob_properties()

        meeting_data = {
            "meeting_id": meeting_id,
            "user_id": user_id,
            "title": f"会議 {meeting_datetime.strftime('%Y-%m-%d %H:%M')}",
            "file_name": file_name,
            "file_path": file_path,
            "file_size": blob_properties.size,
            "duration_seconds": 0,  # TODO: 音声ファイルの長さを取得
            "status": "completed",
            "transcript_text": transcript_text,
            "error_message": None,
            "client_company_name": client_company_name,
            "client_contact_name": client_contact_name,
            "meeting_datetime": meeting_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            "start_datetime": meeting_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            "end_datetime": meeting_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            "inserted_datetime": datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S'),
            "updated_datetime": datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
        }

        # 文字起こしテキストの更新とストアドプロシージャの実行
        try:
            # 2. transcript_text の更新（MERGE）- meeting_idとuser_idを使用
            logger.info(f"Updating transcript_text for meeting_id: {meeting_id}, user_id: {user_id}")
            
            # ファイル名から日時を抽出してタイトルを生成
            datetime_match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3})", file_name)
            meeting_datetime = datetime.strptime(datetime_match.group(1), "%Y-%m-%dT%H-%M-%S-%f") if datetime_match else datetime.now(UTC)
            title = f"会議 {meeting_datetime.strftime('%Y-%m-%d %H:%M')}"
            
            # WAVファイルを一時的にダウンロードして長さを取得
            logger.info(f"WAVファイルの長さを取得するため、一時的にダウンロードします: {file_path}")
            temp_wav_path = os.path.join(tempfile.gettempdir(), file_name)
            
            # Blob Storageからファイルをダウンロード
            blob_service_client = BlobServiceClient.from_connection_string(os.environ["AzureWebJobsStorage"])
            container_name = file_path.split('/')[0]
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)
            
            with open(temp_wav_path, "wb") as temp_file:
                blob_data = blob_client.download_blob()
                blob_data.readinto(temp_file)
            
            # 音声ファイルの長さを取得
            duration_seconds = get_audio_duration(temp_wav_path)
            logger.info(f"音声ファイルの長さ: {duration_seconds}秒")
            
            merge_sql = """
            MERGE INTO dbo.Meetings AS target
            USING (
                SELECT 
                    ? AS meeting_id, 
                    ? AS user_id, 
                    ? AS transcript_text, 
                    ? AS title,
                    ? AS file_name,
                    ? AS file_path,
                    ? AS file_size,
                    ? AS duration_seconds,
                    ? AS status,
                    ? AS client_company_name,
                    ? AS client_contact_name,
                    ? AS meeting_datetime,
                    ? AS start_datetime
                ) AS source
            ON (target.meeting_id = source.meeting_id AND target.user_id = source.user_id)
            WHEN MATCHED THEN
                UPDATE SET 
                    transcript_text = source.transcript_text,
                    updated_datetime = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (
                    meeting_id, 
                    user_id, 
                    transcript_text, 
                    title, 
                    file_name,
                    file_path,
                    file_size,
                    duration_seconds,
                    status,
                    client_company_name,
                    client_contact_name,
                    meeting_datetime,
                    start_datetime,
                    inserted_datetime
                ) VALUES (
                    source.meeting_id, 
                    source.user_id, 
                    source.transcript_text, 
                    source.title,
                    source.file_name,
                    source.file_path,
                    source.file_size,
                    source.duration_seconds,
                    source.status,
                    source.client_company_name,
                    source.client_contact_name,
                    source.meeting_datetime,
                    source.start_datetime,
                    GETDATE()
                );
            """
            
            # Blob Storageからファイル情報を取得
            blob_properties = blob_client.get_blob_properties()
            
            merge_params = (
                meeting_id, 
                user_id, 
                transcript_text, 
                title,
                file_name,
                file_path,
                blob_properties.size,  # file_size
                duration_seconds,  # 取得した音声ファイルの長さを設定
                'completed',  # status
                client_company_name,
                client_contact_name,
                meeting_datetime.strftime('%Y-%m-%d %H:%M:%S'),  # meeting_datetime
                meeting_datetime.strftime('%Y-%m-%d %H:%M:%S')   # start_datetime
            )
            
            execute_query(merge_sql, merge_params)
            logger.info(f"✅ Successfully updated transcript_text for meeting_id: {meeting_id}, user_id: {user_id}, title: {title}, file: {file_name}, duration: {duration_seconds}秒")
            
            # 3. ストアドプロシージャの実行
            logger.info(f"Executing sp_ExtractSpeakersAndSegmentsFromTranscript for meeting_id: {meeting_id}")
            execute_query(
                "EXEC dbo.sp_ExtractSpeakersAndSegmentsFromTranscript ?", 
                (meeting_id,)
            )
            logger.info(f"✅ Successfully executed sp_ExtractSpeakersAndSegmentsFromTranscript for meeting_id: {meeting_id}")
            
            # 成功ログの記録
            insert_trigger_log(
                meeting_id,
                "INFO",
                f"文字起こしテキストの更新と話者・セグメント抽出が完了しました。文字数: {len(transcript_text)}"
            )
            
        except Exception as db_error:
            error_message = f"Database operation failed: {str(db_error)}"
            logger.error(error_message)
            logger.error(f"Error type: {type(db_error)}")
            logger.error(f"Error details: {traceback.format_exc()}")
            
            # エラーログの記録
            insert_trigger_log(
                meeting_id,
                "ERROR",
                f"データベース操作エラー: {error_message}"
            )
            
            return func.HttpResponse(
                "Error updating transcript or extracting speakers",
                status_code=500
            )

        return func.HttpResponse("Success", status_code=200)

    except Exception as e:
        error_message = f"Error in webhook callback: {str(e)}"
        logger.error(error_message)
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        
        insert_trigger_log(meeting_id, "ERROR", error_message)
        return func.HttpResponse("Error", status_code=500)

    finally:
        # 一時ファイルの削除
        if temp_wav_path and os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
                logger.info(f"一時WAVファイルを削除しました: {temp_wav_path}")
            except Exception as e:
                logger.warning(f"一時WAVファイルの削除に失敗: {str(e)}")

def get_client_info(meeting_id: int) -> Optional[Dict[str, str]]:
    """
    クライアント情報を取得する関数
    
    Args:
        meeting_id (int): 会議ID
        
    Returns:
        Optional[Dict[str, str]]: クライアント情報（企業名と担当者名）を含む辞書、またはNone
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
        
        query = """
            SELECT client_company_name, client_contact_name
            FROM dbo.BasicInfo
            WHERE meeting_id = ?
        """

        with pyodbc.connect(conn_str, attrs_before={1256: access_token}) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (meeting_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        "client_company_name": row.client_company_name,
                        "client_contact_name": row.client_contact_name
                    }
                return None
    except Exception as e:
        logger.error(f"Failed to fetch client info: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        return None

@app.function_name(name="TestProcessAudio")
@app.route(route="test-process-audio", methods=["POST"])
def test_process_audio(req: func.HttpRequest) -> func.HttpResponse:
    try:
        logger.info("=== Test Process Audio Start ===")
        
        # リクエストボディからパラメータを取得
        req_body = req.get_json()
        blob_name = req_body.get('blob_name')
        container_name = req_body.get('container_name')
        
        if not blob_name or not container_name:
            return func.HttpResponse(
                "Please provide both blob_name and container_name in the request body",
                status_code=400
            )
            
        # BlobServiceClientの作成
        blob_service_client = BlobServiceClient.from_connection_string(os.environ["AzureWebJobsStorage"])
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        
        # BlobのURLを取得
        blob_url = blob_client.url
        
        # 一時ファイルの作成
        temp_webm_path = os.path.join(tempfile.gettempdir(), blob_name)
        with open(temp_webm_path, "wb") as temp_file:
            blob_data = blob_client.download_blob()
            blob_data.readinto(temp_file)
        
        # WebMからWAVに変換
        temp_wav_path = convert_webm_to_wav(temp_webm_path)
        
        # Speech Serviceの設定
        speech_config = configure_speech_service()
        
        # 認識処理は非同期APIに委ねることを記録
        logger.info("認識処理は非同期ジョブ（Speech-to-Text API v3.0）にて別途実行されます")
        
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "message": "音声ファイルの変換が完了しました。認識処理は非同期ジョブで実行されます。"
            }, ensure_ascii=False),
            status_code=200,
            mimetype="application/json"
        )
            
    except Exception as e:
        logger.error(f"テスト処理中にエラーが発生: {str(e)}")
        logger.error(f"エラーの詳細: {traceback.format_exc()}")
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": f"エラーが発生しました: {str(e)}"
            }, ensure_ascii=False),
            status_code=500,
            mimetype="application/json"
        )
    finally:
        # 一時ファイルの削除
        try:
            if os.path.exists(temp_webm_path):
                try:
                    os.remove(temp_webm_path)
                    logger.info(f"一時WebMファイルを削除しました: {temp_webm_path}")
                except Exception as e:
                    logger.warning(f"一時WebMファイルの削除に失敗: {str(e)}")
            
            if os.path.exists(temp_wav_path):
                try:
                    os.remove(temp_wav_path)
                    logger.info(f"一時WAVファイルを削除しました: {temp_wav_path}")
                except Exception as e:
                    logger.warning(f"一時WAVファイルの削除に失敗: {str(e)}")
        except Exception as e:
            logger.error(f"一時ファイルの削除中にエラーが発生: {str(e)}")

def get_audio_duration(audio_path: str) -> int:
    """音声ファイルの長さを秒単位で取得"""
    try:
        # ファイル形式の検証
        with open(audio_path, 'rb') as f:
            header = f.read(4)
            if header != b'RIFF':
                error_message = f"Invalid audio file format in get_audio_duration. Expected WAV file (RIFF header), but got: {header}"
                logging.error(error_message)
                return 0

        import wave
        with wave.open(audio_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return int(duration)
    except Exception as e:
        logger.error(f"音声ファイル長の取得に失敗: {str(e)}")
        return 0

def format_transcript(transcript_text, speaker_name="Speaker1"):
    """文字起こし結果を整形する"""
    return f"({speaker_name})[{transcript_text}]"

def format_transcript_with_speakers(transcription_results):
    """話者分離を含む文字起こし結果のフォーマット"""
    formatted_text = []
    for result in transcription_results:
        speaker = f"Speaker{result['speaker_id']}"
        text = result['text']
        formatted_text.append(f"({speaker})[{text}]")
    return " ".join(formatted_text)

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
                logger.info(f"paramsの型: {type(params)}")
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
                logger.info("✅ コミット完了（execute_query）")
                return []
                
    except Exception as e:
        logger.error(f"クエリ実行エラー: {str(e)}")
        raise

def get_current_time():
    """
    現在時刻をUTCで取得し、SQLサーバー互換の形式で返す
    """
    return datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')

def test_insert_meeting() -> None:
    """
    dbo.Meetingsテーブルへのテスト用INSERTを実行する関数
    テストデータを挿入し、SELECTで確認する
    """
    try:
        logger.info("=== Meetingsテーブル INSERTテスト開始 ===")
        
        # テストデータの準備
        from datetime import datetime, UTC
        now = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
        
        # INSERTクエリ
        insert_query = """
        INSERT INTO dbo.Meetings (
            meeting_id, user_id, title, file_name, file_path, file_size, duration_seconds,
            status, transcript_text, error_message, client_company_name, client_contact_name,
            meeting_datetime, start_datetime, end_datetime, inserted_datetime, updated_datetime
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # パラメータの設定（既存のmeeting_idとuser_idを使用）
        params = (
            65,  # meeting_id（既存）
            27,  # user_id（既存）
            'テスト会議 2025-05-12',  # title
            'test_meeting_65_2025-05-12T12-00-00-000.wav',  # file_name
            'moc-audio/test_meeting_65_2025-05-12T12-00-00-000.wav',  # file_path
            123456,  # file_size
            180,  # duration_seconds (3分)
            'completed',  # status
            '(Speaker1)[これはテスト用の文字起こしです。] (Speaker2)[はい、確認できました。]',  # transcript_text
            None,  # error_message
            'テスト株式会社',  # client_company_name
            'テスト 太郎',  # client_contact_name
            now,  # meeting_datetime
            now,  # start_datetime
            now,  # end_datetime
            now,  # inserted_datetime
            now   # updated_datetime
        )
        
        # パラメータの型をログ出力
        logger.info(f"INSERTパラメータの型: {type(params)}")
        logger.info(f"INSERTパラメータの内容: {params}")
        
        # INSERT実行
        logger.info("INSERTクエリを実行します")
        execute_query(insert_query, params)
        logger.info("✅ INSERT成功")
        
        # 確認用SELECTクエリ
        select_query = """
        SELECT 
            meeting_id, user_id, title, file_name, status,
            client_company_name, client_contact_name,
            meeting_datetime, inserted_datetime
        FROM dbo.Meetings
        WHERE meeting_id = ? AND user_id = ?
        """
        
        # SELECTパラメータも既存の値を使用
        select_params = (65, 27)
        logger.info(f"SELECTパラメータの型: {type(select_params)}")
        logger.info(f"SELECTパラメータの内容: {select_params}")
        
        # SELECT実行
        logger.info("SELECTクエリを実行して確認します")
        results = execute_query(select_query, select_params)
        
        if results:
            logger.info("=== 挿入されたデータ ===")
            for row in results:
                logger.info(f"meeting_id: {row['meeting_id']}")
                logger.info(f"user_id: {row['user_id']}")
                logger.info(f"title: {row['title']}")
                logger.info(f"file_name: {row['file_name']}")
                logger.info(f"status: {row['status']}")
                logger.info(f"client_company_name: {row['client_company_name']}")
                logger.info(f"client_contact_name: {row['client_contact_name']}")
                logger.info(f"meeting_datetime: {row['meeting_datetime']}")
                logger.info(f"inserted_datetime: {row['inserted_datetime']}")
        else:
            logger.warning("❌ データが見つかりませんでした")

        # INSERT成功後に、sp_ExtractSpeakersAndSegmentsFromTranscriptを呼び出す
        meeting_id = params[0]
        execute_query("EXEC dbo.sp_ExtractSpeakersAndSegmentsFromTranscript ?", (meeting_id,))
        logger.info(f"✅ sp_ExtractSpeakersAndSegmentsFromTranscript 実行完了: meeting_id = {meeting_id}")
            
    except Exception as e:
        logger.error(f"❌ テスト実行中にエラーが発生: {str(e)}")
        logger.error(f"エラーの詳細: {traceback.format_exc()}")
    finally:
        logger.info("=== Meetingsテーブル INSERTテスト終了 ===")

@app.function_name(name="TestInsertMeeting")
@app.route(route="test/insert-meeting", methods=["GET"])
def test_insert_meeting_func(req: func.HttpRequest) -> func.HttpResponse:
    """
    Meetingsテーブルへのテスト用INSERTを実行する簡易HTTPエンドポイント
    GETメソッドでブラウザから直接アクセス可能
    """
    try:
        logger.info("=== テストエンドポイント /test/insert-meeting が呼び出されました ===")
        test_insert_meeting()
        
        # レスポンスヘッダーにContent-Typeとcharsetを明示的に指定
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        
        response_data = {
            "status": "success",
            "message": "テスト会議レコードの挿入に成功しました",
            "endpoint": "GET /api/test/insert-meeting",
            "timestamp": datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            status_code=200,
            headers=headers
        )
    except Exception as e:
        error_message = f"エラーが発生しました: {str(e)}"
        logger.error(error_message)
        logger.error(f"エラーの詳細: {traceback.format_exc()}")
        
        # エラーレスポンスも同様にヘッダーを設定
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        
        response_data = {
            "status": "error",
            "message": error_message,
            "endpoint": "GET /api/test/insert-meeting",
            "timestamp": datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            status_code=500,
            headers=headers
        )

@app.function_name(name="DbInfo")
@app.route(route="test/db-info", methods=["GET"])
def get_db_info(req: func.HttpRequest) -> func.HttpResponse:
    """
    現在接続しているSQL Serverとデータベース名を取得するエンドポイント
    """
    try:
        logger.info("=== データベース接続情報確認エンドポイント /test/db-info が呼び出されました ===")
        
        # データベース情報を取得
        result = execute_query("SELECT DB_NAME() AS db_name, @@SERVERNAME AS server_name")
        
        if not result:
            raise ValueError("データベース情報の取得に失敗しました")
            
        # レスポンスヘッダーの設定
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        
        response_data = {
            "status": "success",
            "result": result[0],  # 単一レコードなので最初の要素を取得
            "endpoint": "GET /api/test/db-info",
            "timestamp": datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        logger.info(f"データベース接続情報: {response_data}")
        
        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            status_code=200,
            headers=headers
        )
        
    except Exception as e:
        error_message = f"データベース接続情報の取得中にエラーが発生: {str(e)}"
        logger.error(error_message)
        logger.error(f"エラーの詳細: {traceback.format_exc()}")
        
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        
        response_data = {
            "status": "error",
            "message": error_message,
            "endpoint": "GET /api/test/db-info",
            "timestamp": datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False),
            status_code=500,
            headers=headers
        )
    finally:
        logger.info("=== データベース接続情報確認エンドポイント終了 ===")
