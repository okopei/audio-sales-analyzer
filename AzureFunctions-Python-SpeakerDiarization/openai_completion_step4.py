import re
import traceback
from typing import List, Dict, Any

def merge_backchannel_with_next(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ステップ3：括弧付きセグメントの吸収処理

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
                text_lines.append(f"{speaker}: {seg['text']}")
        
        input_text = "\n".join(text_lines)
        
        # 括弧付きセグメントの吸収処理
        output_text = absorb_bracket_segments(input_text)
        
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

def absorb_bracket_segments(input_text: str) -> str:
    """括弧付きセグメントを直前の話者の発言に吸収する

    Args:
        input_text (str): 入力テキスト

    Returns:
        str: 処理後のテキスト
    """
    try:
        lines = [line.strip() for line in input_text.splitlines() if line.strip()]

        # 括弧付きセグメントを検出する正規表現パターン（修正版）
        # Speaker行で始まり、括弧のみを含む行を検出
        pattern = r'^Speaker\d+:\s*（.*）\s*$'
        
        # 処理結果を格納するリスト
        processed_lines = []
        i = 0
        absorbed_count = 0
        
        while i < len(lines):
            current_line = lines[i]
            
            # 現在の行が括弧付きセグメントかチェック（修正版）
            if (i > 0 and  # 前の行が存在する
                re.match(pattern, current_line)):  # 括弧のみを含むSpeaker行
                
                # 前の行の話者を取得
                prev_line = lines[i-1]
                if prev_line.startswith("Speaker"):
                    # 括弧付きセグメントの内容を抽出
                    bracket_match = re.search(r'（.*）', current_line)
                    if bracket_match:
                        bracket_content = bracket_match.group(0)
                        # 括弧付きセグメントを前の行に吸収
                        processed_lines[-1] = f"{prev_line}{bracket_content}"
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