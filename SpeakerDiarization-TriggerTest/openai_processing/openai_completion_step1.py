import re
from pathlib import Path
from typing import List, Dict, Optional

def parse_transcript(text: str) -> List[Dict[str, any]]:
    """
    transcript_textから厳密な形式で会話セグメントを抽出して辞書のリストに変換します。
    
    Args:
        text (str): 入力テキスト
        
    Returns:
        List[Dict[str, any]]: パースされたセグメントのリスト
    """
    pattern = re.compile(r"Speaker(\d+):\s*(.*?)\s*(?:\(([\d.]+)\))?$")
    segments = []
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if match:
            speaker = int(match.group(1))
            segment_text = match.group(2).strip()
            offset = float(match.group(3)) if match.group(3) is not None else 0.0
            segments.append({
                "speaker": speaker,
                "text": segment_text,
                "offset": offset
            })
    return segments

def process_segments(segments: List[Dict[str, any]]) -> List[str]:
    """
    セグメントを1つずつ処理し、10文字未満の発話だけ括弧でくくって出力
    発話のマージは一切しない
    """
    if not segments:
        return []

    formatted_lines = []
    for seg in segments:
        text = seg["text"].strip()
        if len(text) < 10:  # 10文字未満は括弧
            text = f'（{text}）'
        line = f'Speaker{seg["speaker"]}: {text}({seg["offset"]})'
        formatted_lines.append(line)

    return formatted_lines

def process_transcript(transcript_text: str) -> Optional[str]:
    """
    トランスクリプトを処理してフォーマットされたテキストを生成します
    
    Args:
        transcript_text (str): 入力トランスクリプト
        
    Returns:
        Optional[str]: フォーマットされたテキスト、エラー時はNone
    """
    if not transcript_text:
        return None
        
    segments = parse_transcript(transcript_text)
    if not segments:
        return None
    
    formatted_lines = process_segments(segments)
    result = "\n".join(formatted_lines)
    return result

if __name__ == "__main__":
    sample_text = "(Speaker1)[えっと、40分。はい、大丈夫です。](0.4)(Speaker2)[ありがとうございます。](2.0)"
    result = process_transcript(sample_text)
    if result:
        print("処理結果:")
        print(result) 