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

def remove_fillers_from_text_with_offset(input_text: str) -> str:
    """OpenAI APIを使用してフィラーを削除する（文字列ベース、offset保持）

    Args:
        input_text (str): 入力テキスト

    Returns:
        str: フィラー削除後のテキスト
    """
    try:
        lines = [line.strip() for line in input_text.splitlines() if line.strip()]

        # 処理結果を格納するリスト
        processed_lines = []
        removed_filler_count = 0
        total_tokens_used = 0  # トータルトークン使用量をカウント
        
        for i, line in enumerate(lines):
            # 話者行かチェック
            if line.startswith("Speaker"):
                try:
                    # 行から本文とoffsetを分離
                    body, offset = extract_offset_from_line(line)
                    
                    # 話者部分と会話内容を分離
                    speaker_part = body.split(":", 1)[0] + ":"
                    conversation_text = body.split(":", 1)[1] if ":" in body else ""
                    
                    if conversation_text.strip():
                        # OpenAI APIでフィラー削除を実行
                        cleaned_text, tokens_used = _remove_fillers_with_gpt(conversation_text.strip())
                        
                        # トークン使用量を加算
                        total_tokens_used += tokens_used
                        
                        # フィラーが削除されたかチェック
                        if cleaned_text != conversation_text.strip():
                            removed_filler_count += 1
                        
                        # 話者部分と結合
                        processed_body = f"{speaker_part} {cleaned_text}"
                        
                        # offsetを再付与
                        if offset is not None:
                            processed_line = f"{processed_body}({offset})"
                        else:
                            processed_line = processed_body
                    else:
                        # 会話内容が空の場合はそのまま
                        processed_line = line
                    
                    processed_lines.append(processed_line)
                    
                except Exception as e:
                    # エラー時は元の行をそのまま追加
                    processed_lines.append(line)
            else:
                # 話者行でない場合はそのまま追加
                processed_lines.append(line)

        # 結果を文字列として返す
        output_text = "\n".join(processed_lines)
        
        return output_text

    except Exception as e:
        raise  # エラーを上位に伝播させる

def remove_fillers_with_openai(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ステップ5：フィラー削除処理（後方互換性のため残す）

    Args:
        segments (List[Dict[str, Any]]): セグメントリスト

    Returns:
        List[Dict[str, Any]]: フィラー削除後のセグメントリスト
    """
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
        
        return processed_segments
        
    except Exception as e:
        return segments

def remove_fillers_from_text(input_text: str) -> str:
    """OpenAI APIを使用してフィラーを削除する（後方互換性のため残す）

    Args:
        input_text (str): 入力テキスト

    Returns:
        str: フィラー削除後のテキスト
    """
    return remove_fillers_from_text_with_offset(input_text)

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