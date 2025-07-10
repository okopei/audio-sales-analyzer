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

def merge_backchannel_with_next_text(input_text: str) -> str:
    """括弧付きセグメントを直前の話者の発言に吸収する（文字列ベース、offset保持）

    Args:
        input_text (str): 入力テキスト

    Returns:
        str: 処理後のテキスト
    """
    try:
        lines = [line.strip() for line in input_text.splitlines() if line.strip()]

        # 括弧付きセグメントを検出する正規表現パターン
        pattern = r'^Speaker\d+:\s*（.*）\s*'
        
        # 処理結果を格納するリスト
        processed_lines = []
        i = 0
        absorbed_count = 0
        
        while i < len(lines):
            current_line = lines[i]
            
            # 現在の行が括弧付きセグメントかチェック
            if (i > 0 and  # 前の行が存在する
                re.match(pattern, current_line)):  # 括弧のみを含むSpeaker行
                
                # 前の行の話者を取得
                prev_line = lines[i-1]
                if prev_line.startswith("Speaker"):
                    # 前の行から本文とoffsetを抽出
                    prev_body, prev_offset = extract_offset_from_line(prev_line)
                    
                    # 括弧付きセグメントの内容を抽出
                    bracket_match = re.search(r'（.*）', current_line)
                    if bracket_match:
                        bracket_content = bracket_match.group(0)
                        
                        # 括弧付きセグメントを前の行に吸収
                        # offsetは前の行（吸収元）のものを維持
                        if prev_offset is not None:
                            merged_line = f"{prev_body}{bracket_content}({prev_offset})"
                        else:
                            merged_line = f"{prev_body}{bracket_content}"
                        
                        processed_lines[-1] = merged_line
                        absorbed_count += 1
                    else:
                        # 括弧が見つからない場合はそのまま追加
                        processed_lines.append(current_line)
                else:
                    # 前の行が話者行でない場合はそのまま追加
                    processed_lines.append(current_line)
            else:
                # 通常の行はそのまま追加
                processed_lines.append(current_line)

            i += 1

        # 結果を文字列として返す
        output_text = "\n".join(processed_lines)
        
        return output_text

    except Exception as e:
        raise  # エラーを上位に伝播させる

def merge_backchannel_with_next(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ステップ3：括弧付きセグメントの吸収処理（後方互換性のため残す）

    Args:
        segments (List[Dict[str, Any]]): セグメントリスト

    Returns:
        List[Dict[str, Any]]: 吸収後のセグメントリスト
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
        
        # 括弧付きセグメントの吸収処理
        output_text = merge_backchannel_with_next_text(input_text)
        
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

def absorb_bracket_segments(input_text: str) -> str:
    """括弧付きセグメントを直前の話者の発言に吸収する（後方互換性のため残す）

    Args:
        input_text (str): 入力テキスト

    Returns:
        str: 処理後のテキスト
    """
    return merge_backchannel_with_next_text(input_text)

def step4_merge_backchannel_with_next(segments: list) -> list:
    """
    ステップ4: 相槌と次の発話の統合
    """
    logger.info("ステップ4: 相槌と次の発話の統合を開始")
    
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
        
        # 括弧付きセグメントの吸収処理
        output_text = merge_backchannel_with_next_text(input_text)
        
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
        
        logger.info("ステップ4: 相槌と次の発話の統合が完了")
        return processed_segments
        
    except Exception as e:
        logger.error(f"ステップ4でエラーが発生: {e}")
        return segments 