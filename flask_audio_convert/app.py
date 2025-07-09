from flask import Flask, request, jsonify
from converters.convert_audio import convert_to_wav
from threading import Thread

app = Flask(__name__)

def background_convert(blob_url):
    print("🚀 [background_convert] スレッド開始")
    print(f"🧾 [background_convert] 処理対象 blob_url: {blob_url}")
    try:
        output_url = convert_to_wav(blob_url)
        print(f"✅ [background_convert] 変換完了: {output_url}")
    except Exception as e:
        print(f"❌ [background_convert] エラー発生: {str(e)}")

@app.route("/convert", methods=["POST"])
def convert():
    print("✅ /convert エンドポイントが呼び出されました")

    try:
        data = request.get_json(force=True)
        print(f"📥 リクエストデータ: {data}")
    except Exception as e:
        print("❌ JSONのパースに失敗しました")
        return jsonify({"error": "Invalid JSON"}), 400

    blob_url = data.get("blob_url")

    if not blob_url:
        print("❌ 'blob_url' がリクエストに含まれていません")
        return jsonify({"error": "blob_url is required"}), 400

    print(f"🔔 blob_url を受信: {blob_url}")

    # バックグラウンド処理を開始するが、ログだけは返す
    Thread(target=background_convert, args=(blob_url,)).start()

    return jsonify({
        "message": "Conversion started",
        "log": "✅ convert 受信済、変換スレッド起動"
    }), 202
