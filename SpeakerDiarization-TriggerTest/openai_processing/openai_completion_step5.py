import re
import logging
import traceback
from typing import List, Dict, Any

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

def merge_consecutive_speaker_lines_text(input_text: str) -> str:
    """同一話者の連続行を結合する（文字列ベース、offset保持）

    Args:
        input_text (str): 入力テキスト

    Returns:
        str: 処理後のテキスト
    """
    try:
        lines = [line.strip() for line in input_text.splitlines() if line.strip()]

        # 処理結果を格納するリスト
        processed_lines = []
        i = 0
        merged_count = 0
        
        while i < len(lines):
            current_line = lines[i]
            
            # 現在の行が話者行かチェック
            if current_line.startswith("Speaker"):
                # 次の行も同じ話者かチェック
                merged_text = current_line
                j = i + 1
                
                # 連続する同じ話者の行を結合
                while j < len(lines) and lines[j].startswith("Speaker"):
                    next_line = lines[j]
                    # 話者部分を除去してテキスト部分のみを取得
                    current_speaker = current_line.split(":", 1)[0]
                    next_speaker = next_line.split(":", 1)[0]
                    
                    if current_speaker == next_speaker:
                        # 同じ話者の場合、テキスト部分を結合
                        next_text = next_line.split(":", 1)[1] if ":" in next_line else next_line
                        merged_text += " " + next_text
                        merged_count += 1
                        j += 1
                    else:
                        break
                
                processed_lines.append(merged_text)
                i = j  # 処理済みの行をスキップ
            else:
                # 話者行でない場合はそのまま追加
                processed_lines.append(current_line)
                i += 1

        # 結果を文字列として返す
        output_text = "\n".join(processed_lines)
        
        return output_text

    except Exception as e:
        raise  # エラーを上位に伝播させる

def merge_same_speaker_segments_text(input_text: str) -> str:
    """同一話者の発言連結処理（文字列ベース、offset保持）

    Args:
        input_text (str): 入力テキスト

    Returns:
        str: 処理後のテキスト
    """
    try:
        lines = [line.strip() for line in input_text.splitlines() if line.strip()]

        # 処理結果を格納するリスト
        processed_lines = []
        i = 0
        merged_count = 0
        
        while i < len(lines):
            current_line = lines[i]
            
            # 現在の行が話者行かチェック
            if current_line.startswith("Speaker"):
                # 現在の行から本文とoffsetを抽出
                current_body, current_offset = extract_offset_from_line(current_line)
                
                # 次の行も同じ話者かチェック
                merged_body = current_body
                merged_offset = current_offset  # 先頭行（吸収元）のoffsetを保持
                j = i + 1
                
                # 連続する同じ話者の行を結合
                while j < len(lines) and lines[j].startswith("Speaker"):
                    next_line = lines[j]
                    # 話者部分を除去してテキスト部分のみを取得
                    current_speaker = current_line.split(":", 1)[0]
                    next_speaker = next_line.split(":", 1)[0]
                    
                    if current_speaker == next_speaker:
                        # 同じ話者の場合、テキスト部分を結合
                        next_body, _ = extract_offset_from_line(next_line)  # offsetは破棄
                        next_text = next_body.split(":", 1)[1] if ":" in next_body else next_body
                        merged_body += " " + next_text
                        merged_count += 1
                        j += 1
                    else:
                        break
                
                # offsetを再付与
                if merged_offset is not None:
                    merged_line = f"{merged_body}({merged_offset})"
                else:
                    merged_line = merged_body
                
                processed_lines.append(merged_line)
                i = j  # 処理済みの行をスキップ
            else:
                # 話者行でない場合はそのまま追加
                processed_lines.append(current_line)
                i += 1

        # 結果を文字列として返す
        output_text = "\n".join(processed_lines)
        
        return output_text

    except Exception as e:
        raise  # エラーを上位に伝播させる

def step5_merge_same_speaker_segments(segments: list) -> list:
    """
    ステップ5: 同一話者の連続セグメントの統合
    """
    logger.info("ステップ5: 同一話者の連続セグメントの統合を開始")
    
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
        
        # 同一話者の発言連結処理
        output_text = merge_same_speaker_segments_text(input_text)
        
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
        
        logger.info("ステップ5: 同一話者の連続セグメントの統合が完了")
        return processed_segments
        
    except Exception as e:
        logger.error(f"ステップ5でエラーが発生: {e}")
        return segments

def merge_consecutive_speaker_lines(input_text: str) -> str:
    """同一話者の連続行を結合する（後方互換性のため残す）

    Args:
        input_text (str): 入力テキスト

    Returns:
        str: 処理後のテキスト
    """
    return merge_consecutive_speaker_lines_text(input_text) 