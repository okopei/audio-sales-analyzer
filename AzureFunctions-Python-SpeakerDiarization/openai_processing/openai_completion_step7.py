import re
import time
import traceback
from typing import List, Dict, Any, Tuple
from .openai_completion_core import client, log_token_usage
import os
import logging

logger = logging.getLogger(__name__)

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

def group_conversation_by_time(input_text: str, block_duration: int = 300) -> List[Dict[str, Any]]:
    """会話を時間単位でグループ化する

    Args:
        input_text (str): 入力テキスト
        block_duration (int): ブロック時間（秒）

    Returns:
        List[Dict[str, Any]]: グループ化された会話ブロック
    """
    try:
        lines = [line.strip() for line in input_text.splitlines() if line.strip()]
        
        blocks = []
        current_block = {
            "start_time": 0,
            "end_time": block_duration,
            "lines": [],
            "block_index": 0
        }
        
        for line in lines:
            if line.startswith("Speaker"):
                body, offset = extract_offset_from_line(line)
                if offset is not None:
                    # どのブロックに属するかを決定
                    block_index = int(offset // block_duration)
                    
                    # 新しいブロックが必要な場合
                    if block_index != current_block["block_index"]:
                        # 現在のブロックを保存（空でない場合）
                        if current_block["lines"]:
                            blocks.append(current_block.copy())
                        
                        # 新しいブロックを開始
                        current_block = {
                            "start_time": block_index * block_duration,
                            "end_time": (block_index + 1) * block_duration,
                            "lines": [],
                            "block_index": block_index
                        }
                    
                    current_block["lines"].append(line)
        
        # 最後のブロックを追加（空でない場合）
        if current_block["lines"]:
            blocks.append(current_block)
        
        return blocks
        
    except Exception as e:
        logger.error(f"会話のグループ化中にエラーが発生: {e}")
        return []

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

def step7_summarize_conversation(segments: list) -> str:
    """
    ステップ7: 会話の分割・要約
    """
    logger.info("ステップ7: 会話の分割・要約を開始")
    
    try:
        # セグメントをテキスト形式に変換
        text_lines = []
        for seg in segments:
            if seg.get("text", "").strip():
                speaker = f"Speaker{seg.get('speaker', '?')}"
                text = seg.get("text", "").strip()
                offset = seg.get("offset", 0.0)
                text_lines.append(f"{speaker}: {text}({offset})")
        
        input_text = "\n".join(text_lines)
        
        # 会話を5分単位でグループ化
        blocks = group_conversation_by_time(input_text, block_duration=300)
        
        if not blocks:
            logger.warning("グループ化されたブロックが見つかりませんでした")
            return input_text
        
        logger.info(f"会話を{len(blocks)}個のブロックに分割しました")
        
        # 各ブロックを処理
        output_lines = []
        for i, block in enumerate(blocks):
            # ブロック内の会話テキストを作成
            conversation_text = "\n".join(block["lines"])
            
            # タイトルを生成
            title = generate_summary_title(conversation_text, i, len(blocks))
            
            # 出力形式で追加
            output_lines.append(f"Summary:{title}")
            output_lines.extend(block["lines"])
        
        # 結果を文字列として返す
        output_text = "\n".join(output_lines)
        
        logger.info("ステップ7: 会話の分割・要約が完了")
        return output_text
        
    except Exception as e:
        logger.error(f"ステップ7でエラーが発生: {e}")
        logger.error(traceback.format_exc())
        # エラー時は元のテキストを返す
        text_lines = []
        for seg in segments:
            if seg.get("text", "").strip():
                speaker = f"Speaker{seg.get('speaker', '?')}"
                text = seg.get("text", "").strip()
                offset = seg.get("offset", 0.0)
                text_lines.append(f"{speaker}: {text}({offset})")
        return "\n".join(text_lines) 