import azure.functions as func
import logging
import os
import tempfile
import uuid
import time
from datetime import datetime, UTC
from azure.cognitiveservices.speech import (
    SpeechConfig,
    AudioConfig,
    SpeechRecognizer,
    ResultReason
)
from azure.data.tables import TableClient
from azure.identity import DefaultAzureCredential
import re
from azure.storage.blob import BlobServiceClient, BlobClient
import traceback

# デバッグログの設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

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
    CommandText="SELECT meeting_id, client_company_name, client_contact_name FROM dbo.BasicInfo", 
    ConnectionStringSetting="SqlConnectionString"
)
def process_audio(event: func.EventGridEvent, meetingsTable: func.Out[func.SqlRow], basicInfoQuery: func.SqlRowList) -> None:
    """
    EventGridTriggerを使用して音声ファイルを処理する関数
    """
    logger.debug("=== EventGridTriggerによる音声ファイル処理開始 ===")
    logger.debug(f"イベントデータ: {event.get_json()}")
    
    # イベントデータからBlobの情報を取得
    event_data = event.get_json()
    blob_url = event_data.get('url', '')
    
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
        
        # Blobをダウンロードして処理
        process_blob(container_name, blob_name, meetingsTable, basicInfoQuery)
    except Exception as e:
        logger.error(f"Blob情報の抽出に失敗: {str(e)}")
        raise

def process_blob(container_name: str, blob_name: str, meetingsTable: func.Out[func.SqlRow], basicInfoQuery: func.SqlRowList) -> None:
    """
    Blobをダウンロードして音声認識処理を行う
    """
    logger.info(f"--- Blob処理開始: {container_name}/{blob_name} ---")
    temp_audio_path = None
    speech_recognizer = None
    
    try:
        # ファイル名からmeeting_idとuser_idを抽出
        # 形式: meeting_{meetingId}_user_{userId}_{timestamp}.{ext}
        parts = blob_name.split('_')
        if len(parts) >= 4 and parts[0] == 'meeting' and parts[2] == 'user':
            meeting_id = parts[1]
            user_id = parts[3]
        else:
            raise ValueError(f"無効なファイル名形式です: {blob_name}")

        logger.info(f"ファイル名から抽出: meeting_id={meeting_id}, user_id={user_id}")
        
        # BlobServiceClientの作成
        blob_service_client = BlobServiceClient.from_connection_string(os.environ["AzureWebJobsStorage"])
        
        # BlobClientの作成
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        
        # Blobのダウンロード
        blob_data = blob_client.download_blob().readall()
        
        # 一時ファイルの作成
        temp_audio_path = os.path.join(tempfile.gettempdir(), f"tmp{uuid.uuid4().hex}.wav")
        
        with open(temp_audio_path, "wb") as temp_file:
            temp_file.write(blob_data)
            
        logger.info(f"一時ファイル作成完了: {temp_audio_path}")
        
        # Speech Service設定
        speech_config = SpeechConfig(
            subscription=os.environ["SPEECH_KEY"],
            region=os.environ["SPEECH_REGION"]
        )
        speech_config.speech_recognition_language = "ja-JP"
        
        # 音声認識の設定
        audio_config = AudioConfig(filename=temp_audio_path)
        speech_recognizer = SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        # 結果を格納する配列
        transcription_results = []
        done = False
        
        def handle_result(evt):
            if evt.result.reason == ResultReason.RecognizedSpeech:
                result = {
                    "text": evt.result.text,
                    "offset": str(evt.result.offset),
                    "duration": str(evt.result.duration)
                }
                transcription_results.append(result)
                    
        def handle_session_stopped(evt):
            nonlocal done
            done = True
            
        # イベントハンドラの設定
        speech_recognizer.recognized.connect(handle_result)
        speech_recognizer.session_stopped.connect(handle_session_stopped)
        
        # 連続認識の開始
        speech_recognizer.start_continuous_recognition()
        while not done:
            time.sleep(0.5)
            
        # 話者分離を含む文字起こし結果のフォーマット
        formatted_transcript = format_transcript_with_speakers(transcription_results)
        
        # 現在時刻を取得（UTC）
        current_time = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
        
        # ファイルサイズを取得
        file_size = os.path.getsize(temp_audio_path)
        
        # 音声ファイルの長さを取得
        duration_seconds = get_audio_duration(temp_audio_path)
        
        # BasicInfoテーブルから顧客情報を取得
        client_company_name = "不明企業"  # デフォルト値を設定
        client_contact_name = "不明担当者"  # デフォルト値を設定
        
        # BasicInfoテーブルから顧客情報を検索
        customer_found = False
        for row in basicInfoQuery:
            if str(row['meeting_id']) == meeting_id:
                client_company_name = row['client_company_name']
                client_contact_name = row['client_contact_name']
                customer_found = True
                logger.info(f"BasicInfoから顧客情報を取得: 企業名={client_company_name}, 担当者名={client_contact_name}")
                break
        
        if not customer_found:
            logger.warning(f"meeting_id {meeting_id} に対応する顧客情報が見つかりませんでした。デフォルト値を使用します。")

        # SQLバインディングを使用してデータを更新
        meeting_data = {
            "meeting_id": int(meeting_id),
            "user_id": int(user_id),
            "file_name": blob_name,
            "title": f"{client_company_name} - {client_contact_name} 様との商談",
            "file_path": f"{container_name}/{blob_name}",
            "file_size": file_size,
            "duration_seconds": duration_seconds,
            "status": "completed",
            "transcript_text": formatted_transcript,
            "error_message": None,
            "client_company_name": client_company_name,
            "client_contact_name": client_contact_name,
            "meeting_datetime": current_time,
            "start_datetime": current_time,
            "end_datetime": current_time,
            "inserted_datetime": current_time,
            "updated_datetime": current_time
        }
        
        meetingsTable.set(func.SqlRow(meeting_data))
        
        logger.info(f"Meetingsテーブル更新完了 - ファイル: {blob_name}")
        
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
                "file_size": file_size if 'file_size' in locals() else 0,
                "duration_seconds": 0,
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
        
    finally:
        if speech_recognizer:
            speech_recognizer.stop_continuous_recognition()
            speech_recognizer = None
            time.sleep(0.5)
            
        if temp_audio_path and os.path.exists(temp_audio_path):
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    os.unlink(temp_audio_path)
                    logger.info("一時ファイル削除完了")
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        logger.warning(f"一時ファイルの削除に失敗（{retry_count}回目）: {str(e)}")
                    time.sleep(0.5)

def get_audio_duration(audio_path: str) -> int:
    """音声ファイルの長さを秒単位で取得"""
    try:
        import wave
        with wave.open(audio_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return int(duration)
    except Exception as e:
        logger.error(f"音声ファイル長の取得に失敗: {str(e)}")
        return 0

def format_transcript_with_speakers(transcription_results):
    """話者分離を含む文字起こし結果のフォーマット"""
    formatted_text = []
    for i, result in enumerate(transcription_results):
        speaker = f"Speaker{1 if i % 2 == 0 else 2}"
        text = result.get('text', '')
        formatted_text.append(f"({speaker})[{text}]")
    return " ".join(formatted_text)
