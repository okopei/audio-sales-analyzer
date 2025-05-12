import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
import json

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定数設定
SPEECH_KEY = "5wzRZyDpp2lnndHds4qmJLu1dh5jYglgShJVRl6XxRllmyfuiGFOJQQJ99BBACi0881XJ3w3AAAYACOGRwGf"
SPEECH_REGION = "japaneast"
TRANSCRIPTION_ID = "b5fdea33-3ead-400e-b7b3-80073cbb182e"

def get_transcription_files() -> Optional[List[Dict]]:
    """
    Speech-to-Text APIから文字起こし結果ファイルの一覧を取得する
    
    Returns:
        Optional[List[Dict]]: ファイル情報のリスト、エラー時はNone
    """
    try:
        # APIエンドポイント
        url = f"https://{SPEECH_REGION}.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions/{TRANSCRIPTION_ID}/files"
        
        headers = {
            "Ocp-Apim-Subscription-Key": SPEECH_KEY
        }
        
        logger.info(f"APIリクエスト実行: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json().get("values", [])
        
    except requests.exceptions.RequestException as e:
        logger.error(f"APIリクエストエラー: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"レスポンス内容: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"予期せぬエラー: {str(e)}")
        return None

def format_file_info(file: Dict) -> str:
    """
    ファイル情報を整形して表示用の文字列を生成する
    
    Args:
        file (Dict): ファイル情報
        
    Returns:
        str: 整形されたファイル情報
    """
    kind = file.get('kind', 'Unknown')
    name = file.get('name', 'Unknown')
    url = file.get('links', {}).get('contentUrl', 'No URL')
    
    # URLの有効期限を確認
    if 'se=' in url:
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        expiration = query_params.get("se", [None])[0]
        
        if expiration:
            try:
                expiration_time = datetime.strptime(expiration, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                if expiration_time < now:
                    url += " (⚠️ 有効期限切れ)"
                else:
                    url += f" (有効期限: {expiration_time.strftime('%Y-%m-%d %H:%M:%S')} UTC)"
            except Exception as e:
                logger.warning(f"SAS期限のパースに失敗: {str(e)}")
    
    return f"""
種類: {kind}
名前: {name}
URL : {url}"""

def main():
    """メイン処理"""
    logger.info("=== Speech-to-Text API 文字起こし結果ファイル取得 ===")
    logger.info(f"Transcription ID: {TRANSCRIPTION_ID}")
    
    files = get_transcription_files()
    if not files:
        logger.error("ファイル情報の取得に失敗しました")
        return
        
    print("\n=== 文字起こし結果ファイル一覧 ===")
    for file in files:
        print(format_file_info(file))
        print("-" * 50)
    
    logger.info("=== 処理完了 ===")

if __name__ == "__main__":
    main() 