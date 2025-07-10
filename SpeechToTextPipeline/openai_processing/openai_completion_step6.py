import re
import time
import traceback
from typing import List, Dict, Any, Tuple
import os
import logging
import openai

logger = logging.getLogger(__name__)

# OpenAIクライアントの初期化
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def log_token_usage(tokens: int, operation: str):
    """トークン使用量を記録する"""
    try:
        logging.info(f"🔢 トークン使用量: {tokens} ({operation})")
    except Exception as e:
        logging.warning(f"トークン使用量記録エラー: {e}")

def remove_fillers_from_text(text: str) -> str:
    """
    OpenAI APIを使用して単一テキストのフィラーを削除する
    """
    system_message = """以下の発話から、自然な会話の流れを崩さずに「えっと」「あの」「まあ」「その」「ですけど」などのフィラーを削除してください。

削除対象のフィラー例：
- えっと（最も一般的）
- あの（会話の冒頭など）
- まあ（話のつなぎによく使われる）
- その（内容が曖昧なとき）
- ですけど（文末に多用されるが曖昧な接続語）

注意事項：
- 会話の意味や意図は変更しない
- 自然な日本語の流れを維持する
- フィラーを削除した結果、不自然になる場合は削除しない
- 出力は修正後のテキストのみを返す（説明不要）
- 出力時に「」は使用しない"""

    user_message = f"""元の発話：
{text}

修正後："""

    try:
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,  # 低い温度で一貫性を保つ
            max_tokens=200    # 短い応答に制限
        )

        # トークン使用量を取得（エラーハンドリング付き）
        try:
            tokens_used = response.usage.total_tokens
        except (AttributeError, KeyError):
            tokens_used = 0

        # トークン使用量を記録
        log_token_usage(tokens_used, "フィラー削除")

        result = response.choices[0].message.content.strip()
        
        # 「」を削除する処理
        result = result.strip('「」')
        
        # 結果が空でない場合は返す
        if result:
            return result
        else:
            return text
            
    except Exception as e:
        logging.warning(f"フィラー削除失敗: {e}")
        return text  # フォールバック 