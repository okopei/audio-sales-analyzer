import traceback
from typing import List, Dict, Any

def merge_same_speaker_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ステップ4：同一話者の発言連結処理

    Args:
        segments (List[Dict[str, Any]]): セグメントリスト

    Returns:
        List[Dict[str, Any]]: 連結後のセグメントリスト
    """
    try:
        # セグメントをテキスト形式に変換
        text_lines = []
        for seg in segments:
            if seg.get("text", "").strip():
                speaker = f"Speaker{seg.get('speaker', '?')}"
                text_lines.append(f"{speaker}: {seg['text']}")
        
        input_text = "\n".join(text_lines)
        
        # 同一話者の発言連結処理
        output_text = merge_consecutive_speaker_lines(input_text)
        
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

def merge_consecutive_speaker_lines(input_text: str) -> str:
    """同一話者の連続行を結合する

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