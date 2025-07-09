import requests
import subprocess
import uuid
import os
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient

UPLOAD_ACCOUNT_NAME = "passrgmoc83cf"
UPLOAD_CONTAINER_NAME = "meeting-audio"

# 🔧 ffmpeg 実行パス
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_PATH = os.path.join(THIS_DIR, "../bin/ffmpeg")

def convert_to_wav(blob_url):
    """SAS付きURLからDL → WAV変換 → Managed Identityでアップロード"""
    print("🧪 convert_to_wav() 開始")
    print(f"🔗 入力 blob_url: {blob_url}")

    temp_input = f"/tmp/{uuid.uuid4()}.input"
    temp_output = f"/tmp/{uuid.uuid4()}.wav"
    print(f"📄 一時ファイル: {temp_input}, {temp_output}")

    # 🎧 ダウンロード
    print("⬇️ 音声データをダウンロード開始")
    r = requests.get(blob_url, stream=True)
    print(f"🌐 ダウンロードステータス: {r.status_code}")
    if r.status_code != 200:
        raise Exception(f"❌ ダウンロード失敗: {r.status_code}")
    with open(temp_input, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    print("✅ ダウンロード完了")

    # 🔄 ffmpeg 変換
    print("🎬 ffmpeg 変換開始")
    print(f"🛠️ 実行パス: {FFMPEG_PATH}")
    print(f"⚙️ コマンド: {FFMPEG_PATH} -y -i {temp_input} -ar 16000 -ac 1 -c:a pcm_s16le {temp_output}")
    result = subprocess.run([
        FFMPEG_PATH, "-y", "-i", temp_input,
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", temp_output
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    print(f"🎞️ ffmpeg 標準出力:\n{result.stdout}")
    print(f"⚠️ ffmpeg 標準エラー:\n{result.stderr}")

    if result.returncode != 0:
        raise Exception(f"❌ ffmpeg 変換失敗: return code {result.returncode}")

    print("✅ ffmpeg 変換完了")

    # 🆙 アップロード先 blob 名
    # 🆙 アップロード先 blob 名を入力ファイル名に基づいて作成
    original_name = os.path.basename(blob_url.split('?')[0])  # クエリパラメータを除去
    output_blob_name = original_name.rsplit('.', 1)[0] + ".wav"
    print(f"🗃️ アップロード先 blob 名: {output_blob_name}")

    # 📤 Managed Identity を使って BlobClient 作成
    print("🪪 DefaultAzureCredential を取得")
    credential = DefaultAzureCredential()

    blob_url = f"https://{UPLOAD_ACCOUNT_NAME}.blob.core.windows.net/{UPLOAD_CONTAINER_NAME}/{output_blob_name}"
    print(f"🚀 アップロード先 URL: {blob_url}")

    blob_client = BlobClient.from_blob_url(blob_url, credential=credential)

    # ⬆️ アップロード実行
    print("📤 WAV をアップロード中...")
    with open(temp_output, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    print("✅ アップロード完了")

    return blob_url
