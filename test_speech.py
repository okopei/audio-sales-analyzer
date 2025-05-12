import requests
import json

# テスト用のリクエストデータ
data = {
    "blob_name": "meeting_71_user_27_2025-04-30T02-11-30-801.webm",
    "container_name": "moc-audio"
}

# APIエンドポイントにリクエストを送信
response = requests.post(
    "http://localhost:7072/api/test-process-audio",
    headers={"Content-Type": "application/json"},
    data=json.dumps(data)
)

# レスポンスの表示
print(f"ステータスコード: {response.status_code}")
print("\nレスポンス内容:")
try:
    response_json = response.json()
    print(json.dumps(response_json, ensure_ascii=False, indent=2))
except json.JSONDecodeError:
    print(response.text) 