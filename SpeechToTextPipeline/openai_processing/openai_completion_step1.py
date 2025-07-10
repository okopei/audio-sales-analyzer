import logging
from typing import List, Dict, Optional, Any
import re

logger = logging.getLogger(__name__)

def step1_process_transcript(transcript_text: str) -> Optional[List[Dict[str, Any]]]:
    if not transcript_text:
        logger.warning("⚠️ ステップ1：空のトランスクリプトを受信しました")
        return None
    
    # パース処理
    pattern = re.compile(r"\(Speaker(\d+)\)\[(.*?)\]\(([\d.]+)\)")
    segments = []
    for match in pattern.finditer(transcript_text):
        speaker = int(match.group(1))
        seg_text = match.group(2).strip()
        offset = float(match.group(3))
        segments.append({
            "speaker": speaker,
            "text": seg_text,
            "offset": offset
        })
    
    if not segments:
        logger.warning("⚠️ ステップ1：セグメントの抽出に失敗しました")
        return None

    # セグメントを整形して返す
    formatted_segments = []
    for seg in segments:
        text = seg.get("text", "").strip()
        if len(text) < 10:
            text = f'（{text}）'
        
        formatted_segments.append({
            "speaker": seg.get("speaker", 1),
            "text": text,
            "offset": seg.get("offset", 0.0)
        })
    
    logger.info("✅ ステップ1：整形結果（最初の5セグメント）:")
    for seg in formatted_segments[:5]:
        logger.info(f"    Speaker{seg['speaker']}: {seg['text']}({seg['offset']})")

    return formatted_segments
