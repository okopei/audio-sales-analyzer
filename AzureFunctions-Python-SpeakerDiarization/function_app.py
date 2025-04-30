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

@app.function_name(name="ProcessAudio")
@app.event_grid_trigger(arg_name="event")
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
def process_audio(event: func.EventGridEvent, meetingsTable: func.Out[func.SqlRow], basicInfoQuery: func.SqlRowList) -> None:
    """
    EventGridTriggerを使用して音声ファイルを処理する関数
    """
    logger.info("=== EventGridTriggerによる音声ファイル処理開始 ===")
    
    # 環境変数の確認
    check_environment_variables()
    
    # イベントデータからBlobの情報を取得
    event_data = event.get_json()
    blob_url = event_data.get('url', '')
    logger.info(f"Received blob URL: {blob_url}")
    
    # BlobのURLからパスを抽出
    # 例: https://storageaccount.blob.core.windows.net/moc-audio/file.wav
    if not blob_url:
        logger.error("Blob URLが見つかりません")
        return
    
    # BlobのURLからコンテナ名とBLOB名を抽出
    try:
        # URLからパスを抽出
        path_parts = blob_url.split('/')
        container_name = path_parts[-2]  # コンテナ名
        blob_name = path_parts[-1]       # Blobファイル名
        
        logger.info(f"コンテナ名: {container_name}, Blob名: {blob_name}")
        
        # ファイル名からmeeting_idとuser_idを抽出
        pattern = r'^meeting_(\d+)_user_(\d+)_[\d\-T:Z]+\.[^.]+$'
        match = re.match(pattern, blob_name)
        if not match:
            error_message = f"Invalid file name format: {blob_name}. Expected format: meeting_[meetingId]_user_[userId]_[timestamp].[ext]"
            logger.error(error_message)
            raise ValueError(error_message)
            
        meeting_id = int(match.group(1))
        user_id = int(match.group(2))
        logger.info(f"Successfully extracted meeting_id: {meeting_id} and user_id: {user_id} from blob name")
        
        # BlobServiceClientの作成
        try:
            blob_service_client = BlobServiceClient.from_connection_string(os.environ["AzureWebJobsStorage"])
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            blob_data = blob_client.download_blob()
            logging.info(f"Successfully downloaded blob: {blob_name}")
            logging.info(f"Blob size: {blob_data.size} bytes")
            logging.info(f"Blob properties: {blob_data.properties}")
        except Exception as e:
            error_message = f"Failed to download blob {blob_name}: {str(e)}"
            logging.error(error_message)
            raise RuntimeError(error_message)

        # 一時音声ファイルの作成
        try:
            temp_audio_path = os.path.join(tempfile.gettempdir(), blob_name)
            with open(temp_audio_path, "wb") as temp_file:
                bytes_written = blob_data.readinto(temp_file)
            logging.info(f"Successfully created temporary audio file: {temp_audio_path}")
            logging.info(f"Bytes written: {bytes_written}")
            logging.info(f"File size: {os.path.getsize(temp_audio_path)}")
            
            # ファイルの先頭を確認
            with open(temp_audio_path, 'rb') as f:
                header = f.read(4)
                logging.info(f"File header: {header.hex()}")
            
            # WebM形式の場合、WAVに変換
            if header.hex() == '1a45dfa3':  # WebM形式のヘッダー
                logging.info("WebM format detected, converting to WAV...")
                temp_wav_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
                
                # ffmpegを使用してWebMからWAVに変換
                try:
                    logging.info(f"Starting ffmpeg conversion from {temp_audio_path} to {temp_wav_path}")
                    result = subprocess.run([
                        'ffmpeg', '-i', temp_audio_path,
                        '-acodec', 'pcm_s16le',  # 16-bit PCM
                        '-ar', '16000',          # 16kHz
                        '-ac', '1',              # モノラル
                        '-y',                    # 上書き
                        temp_wav_path
                    ], check=True, capture_output=True, text=True)
                    
                    logging.info(f"ffmpeg conversion completed. Output: {result.stdout}")
                    
                    # 変換後のファイルを確認
                    if os.path.exists(temp_wav_path):
                        logging.info(f"Successfully converted to WAV: {temp_wav_path}")
                        # 変換後のWAVファイルの情報を確認
                        with wave.open(temp_wav_path, 'rb') as wav_file:
                            channels = wav_file.getnchannels()
                            sample_width = wav_file.getsampwidth()
                            frame_rate = wav_file.getframerate()
                            frames = wav_file.getnframes()
                            duration = frames / float(frame_rate)
                            logging.info(f"Converted WAV file details:")
                            logging.info(f"- Channels: {channels} (should be 1 for mono)")
                            logging.info(f"- Sample width: {sample_width} bytes (should be 2 for 16-bit)")
                            logging.info(f"- Frame rate: {frame_rate} Hz (should be 16000)")
                            logging.info(f"- Duration: {duration:.2f} seconds")
                            logging.info(f"- File size: {os.path.getsize(temp_wav_path)} bytes")
                        
                        # 元のファイルを削除
                        os.remove(temp_audio_path)
                        # 変換後のファイルを元のパスに移動
                        shutil.move(temp_wav_path, temp_audio_path)
                        logging.info(f"Moved converted WAV file to {temp_audio_path}")
                    else:
                        raise RuntimeError("WAV conversion failed: output file not found")
                        
                except subprocess.CalledProcessError as e:
                    error_message = f"Failed to convert WebM to WAV: {e.stderr}"
                    logging.error(error_message)
                    raise RuntimeError(error_message)
            
            # 音声ファイルの形式を確認
            with wave.open(temp_audio_path, 'rb') as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                frame_rate = wav_file.getframerate()
                logging.info(f"Audio file format: {channels} channels, {sample_width} bytes per sample, {frame_rate} Hz")
                
                if channels != 1:
                    logging.warning("Audio file is not mono. Converting to mono...")
                    # TODO: モノラルへの変換処理を実装
                
                if frame_rate != 16000:
                    logging.warning("Audio file is not 16kHz. Converting to 16kHz...")
                    # TODO: 16kHzへの変換処理を実装
        except Exception as e:
            error_message = f"Failed to create temporary audio file {temp_audio_path}: {str(e)}"
            logging.error(error_message)
            raise RuntimeError(error_message)

        # 音声ファイルの処理確認
        check_audio_file(temp_audio_path)

        # Speech Serviceの設定
        try:
            # SpeechConfigの作成と設定
            speech_config = configure_speech_service()
            
            # AudioConfigの作成
            audio_config = AudioConfig(filename=temp_audio_path)
            
            # SpeechRecognizerの作成
            speech_recognizer = SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            logger.info("Successfully configured Speech Service with diarization")
        except Exception as e:
            logger.error(f"Failed to configure Speech Service: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {traceback.format_exc()}")
            raise

        # 話者分離を含む文字起こし結果を格納するリスト
        transcription_results = []

        # 連続認識のコールバック
        def handle_result(evt):
            if evt.result.reason == ResultReason.RecognizedSpeech:
                # 話者IDとテキストを取得
                speaker_id = evt.result.speaker_id
                text = evt.result.text
                transcription_results.append({
                    'speaker_id': speaker_id,
                    'text': text
                })
                logging.info(f"Recognized speech from Speaker{speaker_id}: {text}")

        # コールバックの登録
        speech_recognizer.recognized.connect(handle_result)

        # 連続認識の開始
        speech_recognizer.start_continuous_recognition()
        # 音声ファイルの長さに応じて待機
        time.sleep(get_audio_duration(temp_audio_path) + 1)
        # 連続認識の停止
        speech_recognizer.stop_continuous_recognition()

        # 話者分離結果の整形
        formatted_transcript = format_transcript_with_speakers(transcription_results)
        logging.info(f"Formatted transcript with speakers: {formatted_transcript}")

        # BasicInfoテーブルからの情報取得
        try:
            basic_info = list(basicInfoQuery)
            if not basic_info:
                error_message = f"No basic info found for meeting_id: {meeting_id}"
                logging.error(error_message)
                raise ValueError(error_message)
            
            client_company_name = basic_info[0]["client_company_name"]
            client_contact_name = basic_info[0]["client_contact_name"]
            meeting_datetime = basic_info[0]["meeting_datetime"]
            logging.info(f"Successfully retrieved basic info for meeting_id: {meeting_id}")
        except Exception as e:
            error_message = f"Failed to retrieve basic info: {str(e)}"
            logging.error(error_message)
            raise RuntimeError(error_message)

        # Meetingsテーブルへのデータ挿入
        try:
            logger.info("=== Attempting to insert data into Meetings table ===")
            current_time = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
            meeting_data = {
                "meeting_id": meeting_id,
                "user_id": user_id,
                "title": f"{client_company_name} - {client_contact_name}様との商談",
                "file_name": blob_name,
                "file_path": f"{container_name}/{blob_name}",
                "file_size": blob_data.size,
                "duration_seconds": get_audio_duration(temp_audio_path),
                "status": "completed",
                "transcript_text": formatted_transcript,
                "error_message": None,
                "client_company_name": client_company_name,
                "client_contact_name": client_contact_name,
                "meeting_datetime": meeting_datetime,
                "start_datetime": current_time,
                "end_datetime": current_time,
                "inserted_datetime": current_time,
                "updated_datetime": current_time,
                "deleted_datetime": None
            }
            meetingsTable.set(func.SqlRow(meeting_data))
            logger.info("Successfully inserted data into Meetings table")
        except Exception as e:
            logger.error(f"Failed to insert into Meetings table: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {traceback.format_exc()}")
            raise

        finally:
            # 一時ファイルの削除
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                    logging.info(f"Successfully deleted temporary audio file: {temp_audio_path}")
                except Exception as e:
                    logging.warning(f"Failed to delete temporary audio file {temp_audio_path}: {str(e)}")

    except Exception as e:
        logger.error(f"エラー発生: {str(e)}")
        error_time = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
        if 'meeting_id' in locals() and 'user_id' in locals() and 'file_name' in locals():
            meetingsTable.set(func.SqlRow({
                "meeting_id": int(meeting_id),
                "user_id": int(user_id),
                "file_name": blob_name,
                "title": blob_name,
                "file_path": f"{container_name}/{blob_name}",
                "file_size": blob_data.size if 'blob_data' in locals() else 0,
                "duration_seconds": 0,  # エラー時は0を設定
                "status": "error",
                "error_message": str(e),
                "meeting_datetime": error_time,
                "start_datetime": error_time,
                "client_company_name": "不明企業",
                "client_contact_name": "不明担当者",
                "inserted_datetime": error_time,
                "updated_datetime": error_time
            }))
        raise

    logger.info("=== EventGridTriggerによる音声ファイル処理完了 ===")

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
        # リクエストボディからEventGridイベントデータを取得
        event_data = req.get_json()
        
        # EventGridイベントオブジェクトを作成
        event = func.EventGridEvent(
            id=str(uuid.uuid4()),
            topic=event_data.get('topic', '/subscriptions/{subscription-id}/resourceGroups/Storage/providers/Microsoft.Storage/storageAccounts/audiosalesanalyzeraudio'),
            subject=event_data.get('subject', ''),
            event_type=event_data.get('eventType', ''),
            event_time=datetime.now(UTC).isoformat(),
            data_version=event_data.get('dataVersion', '1.0'),
            data=event_data.get('data', {})
        )
        
        # 既存のprocess_audio関数を呼び出し
        process_audio(event, meetingsTable, basicInfoQuery)
        
        return func.HttpResponse(
            "EventGridイベントの処理が完了しました",
            status_code=200
        )
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
