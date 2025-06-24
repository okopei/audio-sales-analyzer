import azure.functions as func
from azure.functions import EventGridEvent
import logging
import os
import tempfile
import uuid
import time
import re
from datetime import datetime, timezone, timedelta
from azure.identity import DefaultAzureCredential
import traceback
from azure.storage.blob import BlobServiceClient, BlobClient, BlobSasPermissions, generate_blob_sas
import subprocess
import wave
import requests
import pyodbc
from typing import Optional, Dict, List, Any, Union, Tuple
import sys
import struct
import json
import base64
from pathlib import Path
import isodate
sys.path.append(str(Path(__file__).parent.parent))
from openai_processing import clean_and_complete_conversation, load_transcript_segments

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

# FunctionAppインスタンスの生成（1回のみ）
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

def convert_to_wav(input_path: str) -> str:
    """
    m4a / webm ファイルを wav に変換。wav はそのまま返す。
    
    Args:
        input_path (str): 入力ファイルのパス
        
    Returns:
        str: 変換後のWAVファイルのパス（入力がWAVの場合はそのまま）
        
    Raises:
        ValueError: サポートされていない音声形式の場合
    """
    ext = os.path.splitext(input_path)[1].lower()
    
    if ext == ".wav":
        logger.info(f"✅ WAVファイルは変換不要: {input_path}")
        return input_path
    
    elif ext in [".webm", ".m4a"]:
        output_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
        logger.info(f"🔄 {ext} → WAV変換開始: {input_path}")
        
        try:
            result = subprocess.run([
                'ffmpeg', '-i', input_path,
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-y',
                output_path
            ], check=True, capture_output=True, text=True)
            
            logger.info(f"✅ {ext} → WAV変換完了: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ 変換エラー: {e.stderr}")
            raise ValueError(f"音声ファイルの変換に失敗しました: {e.stderr}")
            
    else:
        raise ValueError(f"サポートされていない音声形式です: {ext}")

# 本番用エンドポイント
@app.function_name(name="TriggerTranscriptionJob")
@app.event_grid_trigger(arg_name="event")
def trigger_transcription_job(event: EventGridEvent):
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
        
        # 音声ファイルをWAV形式に変換
        temp_wav_path = convert_to_wav(temp_webm_path)
        
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
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
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