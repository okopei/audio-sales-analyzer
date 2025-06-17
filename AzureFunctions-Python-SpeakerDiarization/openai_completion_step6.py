import time
import traceback
from typing import List, Dict, Any, Tuple
from openai_completion_core import client, log_token_usage
import os

def remove_fillers_with_openai(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ステップ5：フィラー削除処理

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
                text_lines.append(f"{speaker}: {seg['text']}")
        
        input_text = "\n".join(text_lines)
        
        # フィラー削除処理
        output_text = remove_fillers_from_text(input_text)
        
        # テキストをセグメント形式に戻す
        processed_segments = []
        for line in output_text.splitlines():
            if ":" in line:
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
    """OpenAI APIを使用してフィラーを削除する"""
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
                    # 話者部分と会話内容を分離
                    speaker_part = line.split(":", 1)[0] + ":"
                    conversation_text = line.split(":", 1)[1] if ":" in line else ""
                    
                    if conversation_text.strip():
                        # OpenAI APIでフィラー削除を実行
                        cleaned_text, tokens_used = _remove_fillers_with_gpt(conversation_text.strip())
                        
                        # トークン使用量を加算
                        total_tokens_used += tokens_used
                        
                        # フィラーが削除されたかチェック
                        if cleaned_text != conversation_text.strip():
                            removed_filler_count += 1
                        
                        # 話者部分と結合
                        processed_line = f"{speaker_part} {cleaned_text}"
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