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

def extract_offset_from_line(line: str) -> tuple[str, float]:
    """行から本文とoffsetを分離する

    Args:
        line (str): 入力行（例：'Speaker1: こんにちは。(12.5)'）

    Returns:
        tuple[str, float]: (本文, offset) または (元の行, None) のタプル
    """
    match = re.match(r"(Speaker\d+: .+?)\(([\d.]+)\)$", line)
    if match:
        body = match.group(1).rstrip()    # ex. 'Speaker1: こんにちは。'
        offset = float(match.group(2))    # ex. 12.5
        return body, offset
    else:
        return line, None  # offsetなし行

def generate_summary_title(conversation_text: str, block_index: int, total_blocks: int) -> str:
    """OpenAI APIを使用して会話ブロックのタイトルを生成する

    Args:
        conversation_text (str): 会話テキスト
        block_index (int): ブロックのインデックス
        total_blocks (int): 総ブロック数

    Returns:
        str: 生成されたタイトル
    """
    try:
        # 最初と最後のブロックの推奨タイトル
        if block_index == 0:
            suggested_title = "アイスブレイク"
        elif block_index == total_blocks - 1:
            suggested_title = "アポ取り"
        else:
            suggested_title = ""

        system_message = """以下の会話ブロックの内容を分析し、20文字以内の適切なタイトルを生成してください。

タイトル生成のルール：
- 20文字以内で簡潔に
- 会話の主要なテーマや目的を表現
- 最初のブロックは「アイスブレイク」、最後のブロックは「アポ取り」を推奨
- ただし、内容に合わない場合は別の適切なタイトルを生成
- 出力はタイトルのみ（説明不要）

出力例：
アイスブレイク
業界紹介
商品説明
アポ取り"""

        user_message = f"""会話ブロック（{block_index + 1}/{total_blocks}）：
{conversation_text}

推奨タイトル：{suggested_title}

タイトル："""

        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=50
        )

        # トークン使用量を記録
        try:
            tokens_used = response.usage.total_tokens
            log_token_usage(tokens_used, "会話要約タイトル生成")
        except (AttributeError, KeyError):
            pass

        title = response.choices[0].message.content.strip()
        
        # 推奨タイトルが適切な場合は使用
        if block_index == 0 and "アイスブレイク" in title:
            return "アイスブレイク"
        elif block_index == total_blocks - 1 and "アポ取り" in title:
            return "アポ取り"
        else:
            return title[:20]  # 20文字以内に制限
            
    except Exception as e:
        logger.error(f"タイトル生成中にエラーが発生: {e}")
        # エラー時はデフォルトタイトルを返す
        if block_index == 0:
            return "アイスブレイク"
        elif block_index == total_blocks - 1:
            return "アポ取り"
        else:
            return f"会話ブロック{block_index + 1}" 