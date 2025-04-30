import azure.functions as func
import logging
import os
import tempfile
import uuid
import time
import re
from datetime import datetime, UTC
from azure.cognitiveservices.speech import (
    SpeechConfig,
    AudioConfig,
    SpeechRecognizer,
    ResultReason,
    PropertyId
)
from azure.data.tables import TableClient
from azure.identity import DefaultAzureCredential
import traceback
from azure.storage.blob import BlobServiceClient, BlobClient
import subprocess
import shutil
import wave
import requests

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
    """
    Blob アップロード完了時に発火し、Speech-to-Text 非同期ジョブを REST API で作成する
    """
    try:
        blob_url = event.get_json().get("url")
        logger.info(f"Received blob URL: {blob_url}")

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
        
        with open(temp_wav_path, "rb") as wav_file:
            wav_blob_client.upload_blob(wav_file, overwrite=True)
        
        # WAVファイルのURLを取得
        wav_blob_url = wav_blob_client.url
        
        # 一時ファイルの削除
        os.remove(temp_webm_path)
        os.remove(temp_wav_path)

        speech_key = os.environ["SPEECH_KEY"]
        region = os.environ["SPEECH_REGION"]
        endpoint = f"https://{region}.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions"

        # Webhook 用の Function URL
        callback_url = os.environ["TRANSCRIPTION_CALLBACK_URL"]

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

        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        logger.info("Transcription job successfully created")
        return func.HttpResponse("Transcription job created", status_code=200)

    except Exception as e:
        logger.error(f"Error in trigger_transcription_job: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)

@app.function_name(name="TranscriptionCallback")
@app.route(route="transcription-callback", methods=["POST"])
@app.generic_output_binding(
    arg_name="meetingsTable",
    type="sql",
    CommandText="dbo.Meetings",
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_input_binding(
    arg_name="basicInfoQuery",
    type="sql",
    CommandText="SELECT client_company_name, client_contact_name FROM dbo.BasicInfo WHERE meeting_id = @meeting_id",
    ConnectionStringSetting="SqlConnectionString"
)
def transcription_callback(req: func.HttpRequest, meetingsTable: func.Out[func.SqlRow], basicInfoQuery: func.SqlRowList) -> func.HttpResponse:
    """
    Speech Service から transcription 完了通知を受け取る
    結果 JSON のダウンロード → 話者分離結果を整形 → Meetings テーブルに保存
    """
    try:
        data = req.get_json()
        transcription_url = data.get("self")
        logger.info(f"Webhook called. Transcription job URL: {transcription_url}")

        # ファイル名とパスを取得
        content_urls = data.get("contentUrls", [])
        if not content_urls:
            logger.error("No content URLs found in webhook data")
            return func.HttpResponse("No content URLs found", status_code=400)

        # URLからファイル名を抽出
        file_url = content_urls[0]
        file_name = file_url.split('/')[-1]
        file_path = '/'.join(file_url.split('/')[-2:])  # コンテナ名/ファイル名
        logger.info(f"Processing file: {file_name}")
        logger.info(f"File path: {file_path}")
        
        # 正規表現でmeeting_idとuser_idを抽出
        match = re.match(r"meeting_(\d+)_user_(\d+)_.*\.webm", file_name)
        if not match:
            logger.error(f"Invalid file name format: {file_name}")
            return func.HttpResponse("Invalid file name format", status_code=400)
            
        meeting_id = int(match.group(1))
        user_id = int(match.group(2))
        logger.info(f"Extracted meeting_id: {meeting_id}, user_id: {user_id}")

        # BasicInfoからクライアント情報を取得
        client_info = None
        for row in basicInfoQuery:
            if row["meeting_id"] == meeting_id:
                client_info = row
                break

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
        status_resp = requests.get(transcription_url, headers=headers)
        status_resp.raise_for_status()
        status_json = status_resp.json()

        if status_json["status"] != "Succeeded":
            logger.warning(f"Transcription job not succeeded: {status_json['status']}")
            return func.HttpResponse(status_code=202)

        results_url = status_json["resultsUrls"]["channel_0"]
        result_json = requests.get(results_url, headers=headers).json()

        transcript = []
        for phrase in result_json["recognizedPhrases"]:
            speaker = phrase.get("speaker", "Unknown")
            text = phrase["nBest"][0]["display"]
            transcript.append(f"(Speaker{speaker})[{text}]")

        transcript_text = " ".join(transcript)

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

        meetingsTable.set(func.SqlRow(meeting_data))
        logger.info("Webhook transcription result saved to DB")
        return func.HttpResponse("Success", status_code=200)

    except Exception as e:
        logger.error(f"Error in webhook callback: {str(e)}")
        return func.HttpResponse("Error", status_code=500)

@app.function_name(name="TestProcessAudio")
@app.route(route="test-process-audio", methods=["POST"])
@app.generic_output_binding(
    arg_name="meetingsTable",
    type="sql",
    CommandText="dbo.Meetings",
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_input_binding(
    arg_name="basicInfoQuery", 
    type="sql", 
    CommandText="SELECT meeting_id, client_company_name, client_contact_name, meeting_datetime FROM dbo.BasicInfo", 
    ConnectionStringSetting="SqlConnectionString"
)
def test_process_audio(req: func.HttpRequest, meetingsTable: func.Out[func.SqlRow], basicInfoQuery: func.SqlRowList) -> func.HttpResponse:
    """
    HTTPトリガーを使用してEventGridイベントをシミュレートする関数
    """
    try:
        # リクエストボディからURLを取得
        data = req.get_json()
        blob_url = data.get('url')
        
        # EventGridイベントオブジェクトを作成
        event = func.EventGridEvent(
            id=str(uuid.uuid4()),
            topic='/subscriptions/{subscription-id}/resourceGroups/Storage/providers/Microsoft.Storage/storageAccounts/audiosalesanalyzeraudio',
            subject=f'/blobServices/default/containers/moc-audio/blobs/{blob_url.split("/")[-1]}',
            event_type='Microsoft.Storage.BlobCreated',
            event_time=datetime.now(UTC).isoformat(),
            data_version='1.0',
            data={
                'url': blob_url
            }
        )
        
        # trigger_transcription_jobを呼び出し
        return trigger_transcription_job(event)
        
    except Exception as e:
        logger.error(f"テスト処理中にエラーが発生: {str(e)}")
        logger.error(f"エラーの詳細: {traceback.format_exc()}")
        return func.HttpResponse(
            f"エラーが発生しました: {str(e)}",
            status_code=500
        )

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
