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

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# テスト用コード開始 - EventGridTrigger実装
@app.function_name(name="ProcessAudioEventGrid")
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
def process_audio_event_grid(event: func.EventGridEvent, meetingsTable: func.Out[func.SqlRow], basicInfoQuery: func.SqlRowList) -> None:
    """
    EventGridTriggerを使用して音声ファイルを処理する関数
    """
    logging.info(f"--- EventGridTriggerによる音声ファイル処理開始 ---")
    logging.info(f"イベントデータ: {event.get_json()}")
    
    # イベントデータからBlobの情報を取得
    event_data = event.get_json()
    blob_url = event_data.get('url', '')
    
    # BlobのURLからパスを抽出
    # 例: https://storageaccount.blob.core.windows.net/moc-audio/file.wav
    if not blob_url:
        logging.error("Blob URLが見つかりません")
        return
    
    # BlobのURLからコンテナ名とBLOB名を抽出
    try:
        # URLからパスを抽出
        path_parts = blob_url.split('/')
        container_name = path_parts[-2]  # コンテナ名
        blob_name = path_parts[-1]       # Blobファイル名
        
        logging.info(f"コンテナ名: {container_name}, Blob名: {blob_name}")
        
        # Blobをダウンロードして処理
        process_blob(container_name, blob_name, meetingsTable, basicInfoQuery)
    except Exception as e:
        logging.error(f"Blob情報の抽出に失敗: {str(e)}")
        raise

def process_blob(container_name: str, blob_name: str, meetingsTable: func.Out[func.SqlRow], basicInfoQuery: func.SqlRowList) -> None:
    """
    Blobをダウンロードして音声認識処理を行う
    """
    logging.info(f"--- Blob処理開始: {container_name}/{blob_name} ---")
    temp_audio_path = None
    speech_recognizer = None
    
    # 変数の初期化
    file_name = blob_name
    file_base = os.path.splitext(blob_name)[0] if blob_name else None
    file_size = 0
    meeting_id = "2"  # デフォルト値
    DEFAULT_USER_ID = 27  # デフォルトユーザーID
    
    try:
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
            
        logging.info(f"一時ファイル作成完了: {temp_audio_path}")
        
        # ファイル名からmeeting_idを取得
        file_name = blob_name
        file_base = os.path.splitext(file_name)[0]
        
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
        
        # meeting_idを2で固定
        logging.info(f"meeting_idを固定値 {meeting_id} に設定しました")
            
        # BasicInfoテーブルから顧客情報を検索
        customer_found = False
        for row in basicInfoQuery:
            if str(row['meeting_id']) == meeting_id:
                client_company_name = row['client_company_name']
                client_contact_name = row['client_contact_name']
                customer_found = True
                logging.info(f"BasicInfoから顧客情報を取得: 企業名={client_company_name}, 担当者名={client_contact_name}")
                break
        
        if not customer_found:
            logging.warning(f"meeting_id {meeting_id} に対応する顧客情報が見つかりませんでした。デフォルト値を使用します。")

        # SQLバインディングを使用してデータを更新
        meeting_data = {
            "meeting_id": int(meeting_id),
            "file_name": file_name,
            "title": file_base,
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
            "user_id": DEFAULT_USER_ID,
        }
        
        meetingsTable.set(func.SqlRow(meeting_data))
        
        logging.info(f"Meetingsテーブル更新完了 - ファイル: {file_name}")
        
    except Exception as e:
        logging.error(f"エラー発生: {str(e)}")
        error_time = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
        if file_name:
            meetingsTable.set(func.SqlRow({
                "meeting_id": int(meeting_id),
                "file_name": file_name,
                "title": file_base,
                "file_path": f"{container_name}/{blob_name}",
                "file_size": file_size,
                "duration_seconds": 0,
                "status": "error",
                "error_message": str(e),
                "meeting_datetime": error_time,
                "start_datetime": error_time,
                "user_id": DEFAULT_USER_ID,
                "client_company_name": "不明企業",
                "client_contact_name": "不明担当者"
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
                    logging.info("一時ファイル削除完了")
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        logging.warning(f"一時ファイルの削除に失敗（{retry_count}回目）: {str(e)}")
                    time.sleep(0.5)
# テスト用コード終了

# 元のBlobStorageTrigger関数は残しておく
@app.function_name(name="ProcessAudio")
@app.blob_trigger(arg_name="myblob", 
                 path="moc-audio/{name}",
                 connection="AzureWebJobsStorage")
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
def process_audio(myblob: func.InputStream, meetingsTable: func.Out[func.SqlRow], basicInfoQuery: func.SqlRowList) -> None:
    logging.info(f"--- 音声ファイル処理開始: {myblob.name} ---")
    temp_audio_path = None
    speech_recognizer = None
    
    try:
        # 一時ファイルの作成
        audio_data = myblob.read()
        temp_audio_path = os.path.join(tempfile.gettempdir(), f"tmp{uuid.uuid4().hex}.wav")
        
        with open(temp_audio_path, "wb") as temp_file:
            temp_file.write(audio_data)
            
        logging.info(f"一時ファイル作成完了: {temp_audio_path}")
        
        # ファイル名からmeeting_idを取得
        file_name = myblob.name.split('/')[-1]
        file_base = os.path.splitext(file_name)[0]
        
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
        
        # デフォルトユーザーID
        DEFAULT_USER_ID = 27
        
        # BasicInfoテーブルから顧客情報を取得
        client_company_name = "不明企業"  # デフォルト値を設定
        client_contact_name = "不明担当者"  # デフォルト値を設定
        
        # meeting_idを2で固定
        meeting_id = "2"
        logging.info(f"meeting_idを固定値 {meeting_id} に設定しました")
            
        # BasicInfoテーブルから顧客情報を検索
        customer_found = False
        for row in basicInfoQuery:
            if str(row['meeting_id']) == meeting_id:
                client_company_name = row['client_company_name']
                client_contact_name = row['client_contact_name']
                customer_found = True
                logging.info(f"BasicInfoから顧客情報を取得: 企業名={client_company_name}, 担当者名={client_contact_name}")
                break
        
        if not customer_found:
            logging.warning(f"meeting_id {meeting_id} に対応する顧客情報が見つかりませんでした。デフォルト値を使用します。")

        # SQLバインディングを使用してデータを更新
        meeting_data = {
            "meeting_id": int(meeting_id),
            "file_name": file_name,
            "title": file_base,
            "file_path": myblob.name,
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
            "user_id": DEFAULT_USER_ID,
        }
        
        meetingsTable.set(func.SqlRow(meeting_data))
        
        logging.info(f"Meetingsテーブル更新完了 - ファイル: {file_name}")
        
    except Exception as e:
        logging.error(f"エラー発生: {str(e)}")
        error_time = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')
        if file_name:
            meetingsTable.set(func.SqlRow({
                "meeting_id": int(meeting_id),
                "file_name": file_name,
                "title": file_base,
                "file_path": myblob.name,
                "file_size": file_size,
                "duration_seconds": 0,
                "status": "error",
                "error_message": str(e),
                "meeting_datetime": error_time,
                "start_datetime": error_time,
                "user_id": DEFAULT_USER_ID,
                "client_company_name": "不明企業",
                "client_contact_name": "不明担当者"
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
                    logging.info("一時ファイル削除完了")
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        logging.warning(f"一時ファイルの削除に失敗（{retry_count}回目）: {str(e)}")
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
        logging.error(f"音声ファイル長の取得に失敗: {str(e)}")
        return 0

def format_transcript_with_speakers(transcription_results):
    """話者分離を含む文字起こし結果のフォーマット"""
    formatted_text = []
    for i, result in enumerate(transcription_results):
        speaker = f"Speaker{1 if i % 2 == 0 else 2}"
        text = result.get('text', '')
        formatted_text.append(f"({speaker})[{text}]")
    return " ".join(formatted_text)

def update_meeting_transcript(meeting_id: str, transcript_data: dict, temp_audio_path: str, error_message: str = None):
    """Meetingsテーブルを更新"""
    try:
        logging.info(f"テーブル更新開始 - Meeting ID: {meeting_id}")
        
        # Azure認証情報の取得
        credential = DefaultAzureCredential()
        
        # テーブルクライアントの作成
        endpoint = os.environ["AZURE_STORAGE_ENDPOINT"]
        table_client = TableClient(endpoint=endpoint, table_name="Meetings", credential=credential)
        
        # BasicInfoテーブルからの顧客情報取得用クライアント
        basic_info_client = TableClient(endpoint=endpoint, table_name="BasicInfo", credential=credential)
        
        # 現在時刻を取得
        current_time = datetime.now(UTC)
        
        # ファイルサイズを取得
        file_size = os.path.getsize(temp_audio_path)
        
        # 音声ファイルの長さを取得
        duration_seconds = get_audio_duration(temp_audio_path)
        
        # 話者分離を含む文字起こし結果のフォーマット
        formatted_transcript = format_transcript_with_speakers(transcript_data["segments"])
        
        # BasicInfoテーブルから顧客情報を取得
        client_company_name = "不明企業"  # デフォルト値を設定
        client_contact_name = "不明担当者"  # デフォルト値を設定
        try:
            # BasicInfoテーブルからmeeting_idに一致するレコードを検索
            filter_query = f"meeting_id eq {meeting_id}"
            basic_info_items = basic_info_client.query_entities(filter_query)
            
            # 最初のレコードを取得（存在する場合）
            customer_found = False
            for item in basic_info_items:
                client_company_name = item.get("client_company_name")
                client_contact_name = item.get("client_contact_name")
                customer_found = True
                logging.info(f"BasicInfoから顧客情報を取得: 企業名={client_company_name}, 担当者名={client_contact_name}")
                break
                
            if not customer_found:
                logging.warning(f"meeting_id {meeting_id} に対応する顧客情報が見つかりませんでした。デフォルト値を使用します。")
        except Exception as e:
            logging.warning(f"BasicInfoからの顧客情報取得に失敗: {str(e)}")
        
        # エンティティの更新
        entity = {
            "meeting_id": int(meeting_id),
            "transcript_text": formatted_transcript,
            "status": "error" if error_message else "completed",
            "error_message": error_message,
            "end_datetime": current_time.isoformat(),
            "updated_datetime": current_time.isoformat(),
            "file_size": file_size,
            "duration_seconds": duration_seconds,
            "client_company_name": client_company_name,
            "client_contact_name": client_contact_name
        }
        
        # エンティティの更新
        table_client.update_entity(entity=entity)
        
        logging.info(f"Meetingsテーブル更新完了 - ID: {meeting_id}")
        
    except Exception as e:
        logging.error(f"データベース更新エラー: {str(e)}")
        logging.error(f"エラーの詳細: {type(e).__name__}")
        raise
