import re
import logging
from typing import List, Dict, Any, Union

logger = logging.getLogger(__name__)

def _is_short_acknowledgment(segment: Dict[str, Any]) -> bool:
    """短い相槌かどうかを判定する

    Args:
        segment (Dict[str, Any]): セグメントデータ

    Returns:
        bool: 短い相槌の場合True
    """
    # 3秒未満（30,000,000 ticks）かつ10文字未満
    duration = float(segment.get("durationInTicks", 0))
    text = segment.get("text", "").strip()
    return duration < 30000000 and len(text) < 10

def add_brackets_to_short_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """短い相槌を括弧で囲む処理

    Args:
        segments (List[Dict[str, Any]]): 元のセグメントリスト

    Returns:
        List[Dict[str, Any]]: 処理後のセグメントリスト
    """
    if not segments:
        return []

    result = []
    i = 0
    
    while i < len(segments):
        current = segments[i]
        
        # 次のセグメントが存在し、異なる話者で短い相槌の場合
        if (i < len(segments) - 1 and 
            current.get("speaker") != segments[i + 1].get("speaker") and 
            _is_short_acknowledgment(segments[i + 1])):
            
            # 現在のセグメントをそのまま追加
            result.append(current)
            
            # 次のセグメント（相槌）を括弧で囲んで追加
            ack_segment = segments[i + 1].copy()
            ack_segment["text"] = f"（{ack_segment['text']}）"
            result.append(ack_segment)
            i += 2
        else:
            result.append(current)
            i += 1

    return result

def parse_transcript_text(transcript_text: str) -> List[Dict[str, Any]]:
    """Meetings.transcript_textをパースしてセグメントリストに変換する

    Args:
        transcript_text (str): Meetings.transcript_textの文字列
        (Speaker1)[こんにちは、よろしくお願いします。](12.5) (Speaker2)[ありがとうございます。](17.2)

    Returns:
        List[Dict[str, Any]]: パースされたセグメントリスト
    """
    if not transcript_text or not transcript_text.strip():
        return []
    
    segments = []
    # 正規表現でセグメントを抽出
    pattern = r"\(Speaker(\d+)\)\[(.+?)\]\(([\d.]+)\)"
    
    for match in re.finditer(pattern, transcript_text):
        speaker = int(match.group(1))
        text = match.group(2).strip()
        offset = float(match.group(3))
        
        segments.append({
            "speaker": speaker,
            "text": text,
            "offset": offset
        })
    
    return segments

def format_segments_with_offset(segments: List[Dict[str, Any]]) -> str:
    """セグメントリストをoffset表記付きの形式に整形する

    Args:
        segments (List[Dict[str, Any]]): セグメントリスト

    Returns:
        str: 整形された文字列
        Speaker1: こんにちは、よろしくお願いします。(12.5)
        Speaker2: ありがとうございます。(17.2)
    """
    if not segments:
        return ""
    
    formatted_lines = []
    for segment in segments:
        speaker = segment.get("speaker", "Unknown")
        text = segment.get("text", "").strip()
        offset = segment.get("offset", 0.0)
        
        # 話者は括弧なし、会話文は : 区切り、末尾に offset を () で保持
        formatted_line = f"Speaker{speaker}: {text}({offset})"
        formatted_lines.append(formatted_line)
    
    return "\n".join(formatted_lines)

def step1_format_with_offset(segments: list) -> list:
    """
    ステップ1: セグメントリストをoffset表記付きの形式に整形する
    """
    logger.info("ステップ1: フォーマットとオフセット処理を開始")
    
    if not segments:
        return []
    
    # セグメントリストをそのまま返す（既に適切な形式になっている）
    # 必要に応じて、ここでフォーマット処理を追加
    
    logger.info("ステップ1: フォーマットとオフセット処理が完了")
    return segments 