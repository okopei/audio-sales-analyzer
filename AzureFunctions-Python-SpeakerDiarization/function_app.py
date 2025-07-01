import azure.functions as func
import logging
import os
import tempfile
import uuid
import time
import re
from datetime import datetime, timezone, timedelta
from azure.identity import DefaultAzureCredential, ClientSecretCredential
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
from azure.eventgrid import EventGridEvent
from pathlib import Path
import isodate

# パスを追加してopenai_processingモジュールをインポート
sys.path.append(str(Path(__file__).parent))
from openai_processing import clean_and_complete_conversation, load_transcript_segments

# デバッグログの設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Azure Functions v2 - FunctionAppインスタンスの生成
app = func.FunctionApp(
    http_auth_level=func.AuthLevel.ANONYMOUS,
    # v2形式での追加設定
    enable_http_logging=True
)

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

# Azure Functions v2 - Event Grid Trigger
@app.function_name(name="TriggerTranscriptionJob")
@app.event_grid_trigger(arg_name="event")
def trigger_transcription_job(event: func.EventGridEvent) -> None:
    """
    Blobアップロード完了時に発火し、Speech-to-Text非同期ジョブを作成する関数
    
    Args:
        event (func.EventGridEvent): Event Gridイベント
        
    Returns:
        None: Event Grid Trigger関数は値を返さない
    """
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

# 定数の定義
MAX_LOG_LENGTH = 1000

def insert_trigger_log(meeting_id: Optional[int], event_type: str, additional_info: str) -> None:
    """
    TriggerLogテーブルに安全にログを挿入する
    
    Args:
        meeting_id (Optional[int]): 会議ID（record_idとして使用）
        event_type (str): イベントタイプ（'ERROR', 'INFO', 'SKIP'など）
        additional_info (str): 追加情報（エラーメッセージなど）
    """
    # meeting_idの厳密なチェック
    if meeting_id is None or not isinstance(meeting_id, int) or meeting_id <= 0:
        logger.warning(f"meeting_idが不正なためログをスキップします: {meeting_id}")
        return
    
    # パラメータの型チェック
    if not isinstance(event_type, str):
        logger.warning(f"event_typeが文字列でないためTriggerLogへの挿入をスキップします")
        return
        
    if additional_info is not None and not isinstance(additional_info, str):
        logger.warning(f"additional_infoが文字列でないためTriggerLogへの挿入をスキップします")
        return
        
    try:
        # 再帰エラー記録を防止
        if additional_info and (
            "TriggerLog" in additional_info and (
                "INSERT fails" in additional_info or
                "書き込み失敗" in additional_info or
                "IntegrityError" in additional_info
            )
        ):
            logger.warning("再帰的なTriggerLogエントリをスキップします")
            return
            
        # エラーメッセージを最大長で切り詰め
        truncated_info = additional_info[:MAX_LOG_LENGTH] if additional_info else None
        
        # record_idとして使用するmeeting_idを明示的にint型に変換
        record_id = int(meeting_id)
        
        # SQLクエリのパラメータ順序を明示的に指定
        execute_query(
            """
            INSERT INTO dbo.TriggerLog (
                event_type, 
                table_name, 
                record_id,
                event_time, 
                additional_info
            ) VALUES (?, ?, ?, GETDATE(), ?)
            """,
            (event_type, "Meetings", record_id, truncated_info)
        )
        logger.info(f"TriggerLogに正常に記録しました。record_id: {record_id}")
    except Exception as log_error:
        error_summary = str(log_error).split('\n')[0]
        logger.warning(f"TriggerLog書き込み失敗: {error_summary}")
        logger.warning(f"エラーの種類: {type(log_error)}")

def get_db_connection():
    """
    ローカル：ClientSecretCredential（pyodbc）
    本番環境：Microsoft Entra ID（Managed Identity）を使用して Azure SQL Database に接続する。
    ODBC Driver 17 for SQL Server + Authentication=ActiveDirectoryMsi を使用。
    """
    try:
        logger.info("[DB接続] 開始")

        server = os.getenv("SQL_SERVER")
        database = os.getenv("SQL_DATABASE")

        if not server or not database:
            raise ValueError("SQL_SERVER または SQL_DATABASE の環境変数が設定されていません")

        env = os.getenv("AZURE_ENVIRONMENT", "local")  # "local" or "production"
        is_local = env.lower() != "production"

        if is_local:
            # 🔐 ローカル用：ClientSecretCredential + pyodbc + アクセストークン
            logger.info("[DB接続] ローカル環境（pyodbc + Entra認証トークン）")

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
            # ☁️ 本番用：Managed Identity + pyodbc + MSI認証
            logger.info("[DB接続] Azure 環境（pyodbc + MSI）")

            conn_str = (
                f"Driver={{ODBC Driver 17 for SQL Server}};"
                f"Server=tcp:{server},1433;"
                f"Database={database};"
                "Authentication=ActiveDirectoryMsi;"
                "Encrypt=yes;TrustServerCertificate=no;"
            )
            conn = pyodbc.connect(conn_str, timeout=10)
        logger.info("[DB接続] 成功")
        return conn
    except Exception as e:
        logger.error("[DB接続] エラー発生")
        logger.exception("詳細:")
        raise

def get_client_info(meeting_id: int) -> Dict[str, Optional[str]]:
    """
    クライアント情報を取得する関数
    
    Args:
        meeting_id (int): 会議ID
        
    Returns:
        Dict[str, Optional[str]]: クライアント情報（企業名と担当者名）を含む辞書
        エラー時やデータが存在しない場合は、Noneを含む辞書を返す
    """
    try:
        result = execute_query(
            "SELECT client_company_name, client_contact_name FROM dbo.BasicInfo WHERE meeting_id = ?",
            (meeting_id,)
        )
        
        if result and result[0]["client_company_name"] is not None and result[0]["client_contact_name"] is not None:
            return {
                "client_company_name": str(result[0]["client_company_name"]).strip(),
                "client_contact_name": str(result[0]["client_contact_name"]).strip()
            }
        else:
            logger.warning(f"⚠ No client info found for meeting_id: {meeting_id}")
            return {
                "client_company_name": None,
                "client_contact_name": None
            }
    except Exception as e:
        logger.warning(f"⚠ Failed to retrieve client info: {str(e)}")
        logger.warning(f"Error type: {type(e)}")
        logger.warning(f"Error details: {traceback.format_exc()}")
        return {
            "client_company_name": None,
            "client_contact_name": None
        }

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
                return []
                
    except Exception as e:
        logger.error(f"クエリ実行エラー: {str(e)}")
        raise

def get_current_time():
    """現在時刻をUTCで取得し、SQLサーバー互換の形式で返す"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

def get_audio_duration(file_path: str) -> float:
    """
    WAVファイルの長さ（秒数）を取得する関数
    
    Args:
        file_path (str): WAVファイルのパス
        
    Returns:
        float: 音声の長さ（秒）。小数点以下3桁まで丸める
        
    Raises:
        FileNotFoundError: ファイルが存在しない場合
        wave.Error: WAVファイルの形式が不正な場合
        Exception: その他のエラー
    """
    try:
        logger.info(f"音声ファイルの長さを取得: {file_path}")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"音声ファイルが見つかりません: {file_path}")
            
        with wave.open(file_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            
            # 音声ファイルの詳細情報をログ出力
            logger.info(f"音声ファイルの詳細:")
            logger.info(f"- チャンネル数: {wav_file.getnchannels()}")
            logger.info(f"- サンプル幅: {wav_file.getsampwidth()} bytes")
            logger.info(f"- フレームレート: {rate} Hz")
            logger.info(f"- フレーム数: {frames}")
            logger.info(f"- 長さ: {duration:.3f} 秒")
            
            return round(duration, 3)
            
    except wave.Error as e:
        error_message = f"WAVファイルの形式が不正です: {str(e)}"
        logger.error(error_message)
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        raise
    except Exception as e:
        error_message = f"音声ファイルの長さ取得に失敗: {str(e)}"
        logger.error(error_message)
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        raise

# Azure Functions v2 - HTTP Trigger
@app.function_name(name="TranscriptionCallback")
@app.route(route="transcription-callback", methods=["POST"])
def transcription_callback(req: func.HttpRequest) -> func.HttpResponse:
    """
    Speech Service から transcription 完了通知を受け取る
    結果 JSON のダウンロード → 話者分離結果を整形 → Meetings テーブルに保存
    
    Args:
        req (func.HttpRequest): HTTPリクエストオブジェクト
        
    Returns:
        func.HttpResponse: 処理結果のHTTPレスポンス
    """
    meeting_id = None  # 関数の先頭で初期化
    user_id = None     # user_idも初期化
    temp_wav_path = None  # 一時ファイルパスを初期化
    loggable_meeting_id = None  # ログ記録用のmeeting_idを初期化
    
    try:
        logger.info("=== Transcription Callback Start ===")
        
        # リクエストボディの取得と検証
        try:
            data = req.get_json()
            logger.info(f"Received webhook data: {data}")
        except ValueError as e:
            error_message = f"Invalid JSON in request body: {str(e)}"
            logger.error(error_message)
            # meeting_idが未取得のため、TriggerLogへの記録は行わない
            return func.HttpResponse(error_message, status_code=400)
            
        # 必須フィールドの検証
        required_fields = ["self", "contentUrls", "resultsUrls", "status"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            error_message = f"Missing required fields: {', '.join(missing_fields)}"
            logger.error(error_message)
            # meeting_idが未取得のため、TriggerLogへの記録は行わない
            return func.HttpResponse(error_message, status_code=400)
            
        transcription_url = data["self"]
        content_urls = data["contentUrls"]
        results_url = data["resultsUrls"].get("channel_0")
        
        if not results_url:
            error_message = "Missing channel_0 in resultsUrls"
            logger.error(error_message)
            # meeting_idが未取得のため、TriggerLogへの記録は行わない
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
            # meeting_idが未取得のため、TriggerLogへの記録は行わない
            return func.HttpResponse(error_message, status_code=400)
            
        # meeting_idとuser_idの取得と検証（強化）
        try:
            meeting_id = int(match.group(1))
            user_id = int(match.group(2))
            loggable_meeting_id = meeting_id  # TriggerLog用のIDとして確保
            logger.info(f"[DEBUG] 抽出されたmeeting_id: {meeting_id} (type: {type(meeting_id)})")
            logger.info(f"[DEBUG] 抽出されたuser_id: {user_id} (type: {type(user_id)})")
            logger.info(f"[DEBUG] 設定されたloggable_meeting_id: {loggable_meeting_id} (type: {type(loggable_meeting_id)})")
            
            # meeting_idの有効性チェック
            if not meeting_id or meeting_id <= 0:
                error_message = f"Invalid meeting_id: {meeting_id}"
                logger.error(error_message)
                return func.HttpResponse(error_message, status_code=400)
                
            # user_idの有効性チェック
            if not user_id or user_id <= 0:
                error_message = f"Invalid user_id: {user_id}"
                logger.error(error_message)
                return func.HttpResponse(error_message, status_code=400)
                
        except ValueError as e:
            error_message = f"Failed to parse meeting_id or user_id: {str(e)}"
            logger.error(error_message)
            return func.HttpResponse(error_message, status_code=400)
            
        logger.info(f"Extracted meeting_id: {meeting_id}, user_id: {user_id}")

        # ここから先はmeeting_idが取得済みのため、TriggerLogへの記録が可能
        try:
            # BasicInfoからクライアント情報を取得（安全なアクセス）
            client_info = get_client_info(meeting_id)
            client_company_name = client_info.get("client_company_name") or "不明企業"
            client_contact_name = client_info.get("client_contact_name") or "不明担当者"
            
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
                insert_trigger_log(loggable_meeting_id, "WARNING", f"Transcription job status: {status_json['status']}")
                return func.HttpResponse(status_code=202)

            # 文字起こし結果の取得と検証
            logger.info(f"Fetching transcription results from: {results_url}")
            response = requests.get(results_url, headers=headers)
            response.raise_for_status()  # HTTPエラーのチェック
            
            if not response.content.strip():
                error_message = "❌ Speech-to-Text 結果のレスポンスが空です"
                logger.error(error_message)
                logger.error(f"Response status code: {response.status_code}")
                logger.error(f"Response headers: {response.headers}")
                insert_trigger_log(loggable_meeting_id, "ERROR", error_message)
                return func.HttpResponse("Empty transcription result", status_code=502)
                
            try:
                result_json = response.json()
                logger.info("Successfully retrieved and parsed transcription results")
            except json.JSONDecodeError as e:
                error_message = f"❌ Failed to parse transcription results as JSON: {str(e)}"
                logger.error(error_message)
                logger.error(f"Response content: {response.content[:1000]}...")  # 最初の1000文字だけログ出力
                insert_trigger_log(loggable_meeting_id, "ERROR", error_message)
                return func.HttpResponse("Invalid JSON in transcription result", status_code=502)

            transcript = []
            for phrase in result_json["recognizedPhrases"]:
                speaker = phrase.get("speaker", "Unknown")
                text = phrase["nBest"][0]["display"]
                
                # offsetフィールドから時刻を取得（ISO 8601形式）
                offset_str = phrase.get("offset", "PT0S")
                try:
                    # isodate.parse_durationで秒数に変換
                    duration_obj = isodate.parse_duration(offset_str)
                    offset_seconds = duration_obj.total_seconds()
                    # 小数第1位まで表示
                    offset_seconds = round(offset_seconds, 1)
                except Exception as e:
                    logger.warning(f"時刻の変換に失敗しました: {offset_str}, エラー: {str(e)}")
                    offset_seconds = 0.0
                
                transcript.append(f"(Speaker{speaker})[{text}]({offset_seconds})")

            transcript_text = " ".join(transcript)
            logger.info(f"Generated transcript text: {transcript_text[:100]}...")  # 最初の100文字だけログ出力

            # 文字起こしテキストの更新とストアドプロシージャの実行
            try:
                # 2. transcript_text の更新（MERGE）- meeting_idとuser_idを使用
                logger.info(f"Updating transcript_text for meeting_id: {meeting_id}, user_id: {user_id}")
                
                # ファイル名から日時を抽出してタイトルを生成
                datetime_match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3})", file_name)
                meeting_datetime = datetime.strptime(datetime_match.group(1), "%Y-%m-%dT%H-%M-%S-%f") if datetime_match else datetime.now(timezone.utc)
                title = f"会議 {meeting_datetime.strftime('%Y-%m-%d %H:%M')}"
                
                # WAVファイルを一時的にダウンロードして長さを取得
                logger.info(f"WAVファイルの長さを取得するため、一時的にダウンロードします: {file_path}")
                temp_wav_path = os.path.join(tempfile.gettempdir(), file_name)
                
                try:
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
                    
                except Exception as e:
                    # エラーメッセージを簡潔に保持
                    error_summary = str(e).split('\n')[0]  # 最初の行のみを使用
                    logger.error(f"音声ファイルの長さ取得に失敗: {error_summary}")
                    logger.error(f"Error type: {type(e)}")
                    # スタックトレースは詳細ログのみに記録
                    logger.debug(f"Error details: {traceback.format_exc()}")
                    
                    duration_seconds = 0  # エラー時は0秒として処理を継続
                    # エラーメッセージを簡潔に保持してTriggerLogに記録
                    insert_trigger_log(
                        loggable_meeting_id,
                        "WARNING",
                        f"音声ファイルの長さ取得に失敗: {error_summary}"
                    )

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
                        ? AS start_datetime,
                        GETDATE() AS inserted_datetime
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
                        source.inserted_datetime
                    );
                """
                
                # Blob Storageからファイル情報を取得
                blob_properties = blob_client.get_blob_properties()
                
                # パラメータを13個に調整（inserted_datetimeはGETDATE()で設定されるため除外）
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
                
                # デバッグログの追加
                logger.debug(f"[DEBUG] MERGE INTO実行 - meeting_id: {meeting_id}, user_id: {user_id}")
                logger.debug(f"[DEBUG] パラメータ数: {len(merge_params)} (inserted_datetimeはGETDATE()で設定)")
                
                # merge_sql実行
                execute_query(merge_sql, merge_params)
                logger.info(f"✅ Successfully updated transcript_text for meeting_id: {meeting_id}, user_id: {user_id}, title: {title}, file: {file_name}, duration: {duration_seconds}秒")
                
                # 成功ログを手動で記録（record_idを明示的に指定）
                if loggable_meeting_id:
                    insert_trigger_log(
                        loggable_meeting_id,  # 明示的にrecord_idとして使用
                        "INFO",
                        f"文字起こしテキストの更新が完了しました。文字数: {len(transcript_text)}"
                    )
                
                # OpenAI処理を実行して整形されたセグメントを取得
                try:
                    logger.info(f"🚀 OpenAI処理を開始します。meeting_id: {meeting_id}")
                    
                    # transcript_textがNoneでないことを確認
                    if not transcript_text or transcript_text.strip() == "":
                        logger.warning("⚠️ transcript_textが空のため、OpenAI処理をスキップします")
                        insert_trigger_log(loggable_meeting_id, "WARNING", "transcript_textが空のため、OpenAI処理をスキップしました")
                    else:
                        logger.info(f"📝 transcript_textの長さ: {len(transcript_text)} 文字")
                        logger.info(f"📝 transcript_textの先頭100文字: {transcript_text[:100]}...")
                        
                        # OpenAI処理を実行
                        logger.info("🔄 clean_and_complete_conversationを呼び出し中...")
                        openai_success = clean_and_complete_conversation(meeting_id)
                        
                        if openai_success:
                            logger.info("✅ OpenAI処理が完了しました")
                            insert_trigger_log(loggable_meeting_id, "INFO", "OpenAI処理完了。ステップ7とステップ8が正常に実行されました")
                        else:
                            logger.warning("⚠️ OpenAI処理が失敗しました")
                            insert_trigger_log(loggable_meeting_id, "WARNING", "OpenAI処理が失敗しました")
                            
                except Exception as openai_error:
                    error_message = f"OpenAI処理でエラーが発生: {str(openai_error)}"
                    logger.error(error_message)
                    logger.error(f"Error type: {type(openai_error)}")
                    logger.error(f"Error details: {traceback.format_exc()}")
                    
                    if loggable_meeting_id:
                        insert_trigger_log(loggable_meeting_id, "ERROR", f"OpenAI処理エラー: {error_message}")
                    
                    # OpenAI処理の失敗は致命的ではないため、処理を継続
                    logger.info("OpenAI処理の失敗により、元の文字起こし結果をそのまま使用します")
                
                return func.HttpResponse("Success", status_code=200)

            except Exception as db_error:
                error_message = f"Database operation failed: {str(db_error)}"
                logger.error(error_message)
                logger.error(f"Error type: {type(db_error)}")
                logger.error(f"Error details: {traceback.format_exc()}")
                
                # loggable_meeting_idの状態を確認してからログを記録
                logger.debug(f"[DEBUG] loggable_meeting_id: {loggable_meeting_id} (type: {type(loggable_meeting_id)})")
                if loggable_meeting_id:
                    insert_trigger_log(loggable_meeting_id, "ERROR", f"データベース操作エラー: {error_message}")
                else:
                    logger.warning("meeting_idが未取得のため、TriggerLogへの記録をスキップします")
                
                return func.HttpResponse(
                    "Error updating transcript",
                    status_code=500
                )

        except Exception as e:
            error_message = f"Error in webhook callback: {str(e)}"
            logger.error(error_message)
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {traceback.format_exc()}")
            
            # loggable_meeting_idの状態を確認してからログを記録
            logger.debug(f"[DEBUG] loggable_meeting_id: {loggable_meeting_id} (type: {type(loggable_meeting_id)})")
            if loggable_meeting_id:
                insert_trigger_log(loggable_meeting_id, "ERROR", error_message)
            else:
                logger.warning("meeting_idが未取得のため、TriggerLogへの記録をスキップします")
            
            return func.HttpResponse("Error", status_code=500)

    except Exception as e:
        error_message = f"Error in webhook callback: {str(e)}"
        logger.error(error_message)
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        
        # loggable_meeting_idの状態を確認してからログを記録
        logger.debug(f"[DEBUG] loggable_meeting_id: {loggable_meeting_id} (type: {type(loggable_meeting_id)})")
        if loggable_meeting_id:
            insert_trigger_log(loggable_meeting_id, "ERROR", error_message)
        else:
            logger.warning("meeting_idが未取得のため、TriggerLogへの記録をスキップします")
        
        return func.HttpResponse("Error", status_code=500)

    finally:
        # 一時ファイルの削除
        if temp_wav_path and os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
                logger.info(f"一時WAVファイルを削除しました: {temp_wav_path}")
            except Exception as e:
                logger.warning(f"一時WAVファイルの削除に失敗: {str(e)}")
                # loggable_meeting_idの状態を確認してからログを記録
                logger.debug(f"[DEBUG] loggable_meeting_id: {loggable_meeting_id} (type: {type(loggable_meeting_id)})")
                if loggable_meeting_id:
                    insert_trigger_log(loggable_meeting_id, "WARNING", f"一時ファイル削除失敗: {str(e)}")
                else:
                    logger.warning("meeting_idが未取得のため、TriggerLogへの記録をスキップします")
