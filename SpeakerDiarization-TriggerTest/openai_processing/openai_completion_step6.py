import re
import time
import traceback
from typing import List, Dict, Any, Tuple
from .openai_completion_core import client, log_token_usage
import os
import logging

logger = logging.getLogger(__name__)


def remove_fillers_from_text(text: str) -> str:
    """
    _remove_fillers_with_gpt() を使ってフィラーを除去（ラッパー）
    """
    try:
        cleaned, _ = _remove_fillers_with_gpt(text)
        return cleaned
    except Exception as e:
        logging.warning(f"フィラー削除失敗: {e}")
        return text  # フォールバック


def _remove_fillers_with_gpt(text: str, max_retries: int = 2) -> tuple[str, int]:
    """OpenAI APIを使用して単一テキストのフィラーを削除する

    Args:
        text (str): フィラーを削除するテキスト
        max_retries (int): 最大リトライ回数

    Returns:
        tuple[str, int]: (フィラー削除後のテキスト, 使用トークン数)
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

    for attempt in range(max_retries + 1):
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
                return result, tokens_used
            else:
                return text, tokens_used
                
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1)  # 1秒待機してリトライ
            else:
                return text, 0  # エラー時は元のテキストと0トークンを返す 

def step6_remove_fillers(segments: list) -> list:
    """
    ステップ6: フィラー削除
    """
    logger.info("ステップ6: フィラー削除を開始")
    
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
        
        # フィラー削除処理
        output_text = remove_fillers_from_text_with_offset(input_text)
        
        # テキストをセグメント形式に戻す
        processed_segments = []
        for line in output_text.splitlines():
            if ":" in line:
                # 行をパースしてセグメントに変換
                body, offset = extract_offset_from_line(line)
                if offset is not None:
                    speaker, text = body.strip().split(":", 1)
                    speaker_id = speaker.replace("Speaker", "").strip()
                    processed_segments.append({
                        "speaker": speaker_id,
                        "text": text.strip(),
                        "offset": offset
                    })
                else:
                    # offsetがない場合は従来の処理
                    speaker, text = line.strip().split(":", 1)
                    speaker_id = speaker.replace("Speaker", "").strip()
                    processed_segments.append({
                        "speaker": speaker_id,
                        "text": text.strip()
                    })
        
        logger.info("ステップ6: フィラー削除が完了")
        return processed_segments
        
    except Exception as e:
        logger.error(f"ステップ6でエラーが発生: {e}")
        return segments 