from typing import List, Dict, Any

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