from azure.storage.blob import BlobServiceClient
import os

# local.settings.json に設定済みの接続文字列を使用
connection_str = os.environ["AzureWebJobsStorage"]
container_name = "moc-audio"
blob_name = "meeting_71_user_27_2025-04-30T02-11-30-801.webm"

try:
    service_client = BlobServiceClient.from_connection_string(connection_str)
    blob_client = service_client.get_blob_client(container=container_name, blob=blob_name)

    # Blobをダウンロードしてサイズを確認（成功すれば接続もOK）
    blob_data = blob_client.download_blob().readall()
    print(f"✔ ダウンロード成功: {len(blob_data)} bytes")

except Exception as e:
    print(f"❌ エラー: {e}") 