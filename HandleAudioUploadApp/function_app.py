import logging
import azure.functions as func
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta, timezone
import os
import requests

app = func.FunctionApp()

@app.function_name(name="HandleAudioUploadEvent")
@app.event_grid_trigger(arg_name="event")
def handle_audio_upload_event(event: func.EventGridEvent):
    try:
        logging.info("🔔 HandleAudioUploadEvent: Event received")

        event_json = event.get_json()
        blob_url = event_json.get("url")
        if not blob_url:
            raise ValueError("イベントデータに URL が含まれていません")
        logging.info(f"📦 Blob URL: {blob_url}")

        # 設定
        expected_container = "moc-audio"
        account_name = "audiosalesanalyzeraudio"
        account_key = os.environ["ACCOUNT_KEY"]
        flask_endpoint = os.environ.get("CONVERTER_ENDPOINT", "https://audio-converter-app.azurewebsites.net/convert")

        # URL からコンテナと blob 名を取得
        parts = blob_url.split('/')
        container_name = parts[-2]
        blob_name = parts[-1]

        if container_name != expected_container:
            logging.warning(f"⏭ 他コンテナからのイベント: {container_name} → スキップ")
            return

        # SAS URL を作成（1時間有効）
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        sas_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
        logging.info(f"🔑 SAS URL 生成成功")

        # Flask API に送信
        response = requests.post(flask_endpoint, json={"blob_url": sas_url}, timeout=60)
        logging.info(f"📤 Flask POST レスポンス: {response.status_code} - {response.text}")

    except Exception as e:
        logging.exception("❌ HandleAudioUploadEvent エラー")
