import re
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

def extract_offset_from_line(line: str) -> tuple[str, str]:
    """行から本文とoffsetを分離する

    Args:
        line (str): 入力行（例：'Speaker1: こんにちは。(12.5)'）

    Returns:
        tuple[str, str]: (本文, offset) または (元の行, '') のタプル
    """
    match = re.match(r"(Speaker\d+: .+?)(\(\d+(\.\d+)?\))$", line)
    if match:
        body = match.group(1).rstrip()    # ex. 'Speaker1: こんにちは。'
        offset = match.group(2)           # ex. '(12.5)'
        return body, offset
    else:
        return line, ""  # offsetなし行

def extract_speaker_from_line(line: str) -> str:
    """行から発話者を抽出する

    Args:
        line (str): 入力行（例：'Speaker1: こんにちは。(12.5)'）

    Returns:
        str: 発話者（例：'Speaker1'）または空文字列
    """
    match = re.match(r"(Speaker\d+):", line)
    return match.group(1) if match else ""

def get_front_sentence(lines: list, current_index: int, current_speaker: str) -> str:
    """
    定義ルールに従って前の文（front）を抽出する
    
    Args:
        lines (list): 全行のリスト
        current_index (int): 現在の行インデックス
        current_speaker (str): 現在の発話者
        
    Returns:
        str: 前の文（最終文）または空文字列
    """
    # 直前の行から遡って別の発話者による発話を探す
    for i in range(current_index - 1, -1, -1):
        line = lines[i].strip()
        if not line:
            continue
            
        speaker = extract_speaker_from_line(line)
        if speaker and speaker != current_speaker:
            # 別の発話者による発話が見つかった
            body, _ = extract_offset_from_line(line)
            text_part = extract_text_part(body)
            
            # 句点で区切って最終文を取得
            sentences = re.split(r'[。、，]', text_part)
            # 空文字列を除去して最終文を取得
            valid_sentences = [s.strip() for s in sentences if s.strip()]
            if valid_sentences:
                return valid_sentences[-1]  # 最終文
            break
    
    return ""

def get_back_sentence(lines: list, current_index: int, current_speaker: str) -> str:
    """
    定義ルールに従って後ろの文（back）を抽出する
    
    Args:
        lines (list): 全行のリスト
        current_index (int): 現在の行インデックス
        current_speaker (str): 現在の発話者
        
    Returns:
        str: 後ろの文（先頭文）または空文字列
    """
    # 直後の行から順に別の発話者による発話を探す
    for i in range(current_index + 1, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
            
        speaker = extract_speaker_from_line(line)
        if speaker and speaker != current_speaker:
            # 別の発話者による発話が見つかった
            body, _ = extract_offset_from_line(line)
            text_part = extract_text_part(body)
            
            # 句点で区切って先頭文を取得
            sentences = re.split(r'[。、，]', text_part)
            # 空文字列を除去して先頭文を取得
            valid_sentences = [s.strip() for s in sentences if s.strip()]
            if valid_sentences:
                return valid_sentences[0]  # 先頭文
            break
    
    return ""

def step3_finalize_completion(segments: List[str]) -> List[str]:
    """
    ステップ3: 会話補完の確定処理（ファイル保存なし／ログ出力のみ）
    
    Args:
        segments (List[str]): ステップ2で整形されたセグメント文字列リスト
        
    Returns:
        List[str]: 処理後の最終セグメント
    """
    try:
        result_lines = []
        processed_count = 0

        for i, line in enumerate(segments):
            line = line.strip()
            if not line:
                continue

            score_match = re.search(r'\[前:([0-9.]+) 後:([0-9.]+)\]$', line)

            if score_match:
                front_score = float(score_match.group(1))
                back_score = float(score_match.group(2))
                original_line = line[:line.find('[')].strip()

                bracket_match = re.search(r'Speaker(\d+): （(.+?)）\(([0-9.]+)\)', original_line)

                if bracket_match:
                    speaker = bracket_match.group(1)
                    bracket_content = bracket_match.group(2)
                    offset = bracket_match.group(3)

                    current_speaker = f"Speaker{speaker}"
                    front_sentence = get_front_sentence(segments, i, current_speaker)
                    back_sentence = get_back_sentence(segments, i, current_speaker)

                    if front_score > back_score:
                        completed_text = get_completed_bracket(bracket_content, front_sentence, back_sentence, "front")
                    else:
                        completed_text = get_completed_bracket(bracket_content, front_sentence, back_sentence, "back")

                    result_line = f"Speaker{speaker}: （{completed_text}）({offset})"
                    result_lines.append(result_line)
                    processed_count += 1
                else:
                    result_lines.append(original_line)
            else:
                result_lines.append(line)

        logger.info(f"✅ ステップ3完了: {processed_count} 件の括弧内発話を補完しました")
        logger.info("📝 ステップ3の出力例（最初の5行）:")
        for idx, line in enumerate(result_lines[:5]):
            logger.info(f"{idx+1}: {line}")

        return result_lines

    except Exception as e:
        logger.error(f"ステップ3処理中にエラーが発生: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def get_completed_bracket(original_bracket: str, prev_body: str, next_body: str, connection_type: str) -> str:
    """
    括弧内テキストを補完する（前後文と結合）
    
    Args:
        original_bracket (str): 元の括弧内内容
        prev_body (str): 前の発話（補完用文脈）
        next_body (str): 後の発話（補完用文脈）
        connection_type (str): "front" または "back"
        
    Returns:
        str: 補完後の括弧内内容
    """
    # 句点などを除去
    bracket = original_bracket.strip("（）。、，")
    front = extract_text_part(prev_body).strip("。、，") if prev_body else ""
    back = extract_text_part(next_body).strip("。、，") if next_body else ""

    if connection_type == "front" and front:
        return front + bracket + "。"
    elif connection_type == "back" and back:
        return bracket + back + "。"
    else:
        return original_bracket

def get_deletion_candidates(original_bracket: str, completed_bracket: str, adopted_text: str, connection_type: str) -> tuple[list, str]:
    """
    削除候補を生成し、削除処理を実行する
    
    Args:
        original_bracket (str): 元の括弧内内容
        completed_bracket (str): 補完後の括弧内内容
        adopted_text (str): 採用された発話
        connection_type (str): "front" または "back"
        
    Returns:
        tuple[list, str]: (削除候補のリスト, 削除後のテキスト)
    """
    deletion_candidates = []

    # ① 補完前の括弧内語（括弧を除去）を常に削除候補に追加
    deletion_candidates.append(original_bracket.strip("（）"))

    # ② adopted_text（接続された発話）から、接続方向に応じて対象文を抽出
    adopted_text_part = extract_text_part(adopted_text)
    split_sentences = re.split(r'[。．]', adopted_text_part)
    split_sentences = [s.strip() for s in split_sentences if s.strip()]

    if connection_type == "front" and split_sentences:
        # 末尾文
        deletion_candidates.append(split_sentences[-1])
    elif connection_type == "back" and split_sentences:
        # 先頭文
        deletion_candidates.append(split_sentences[0])

    # 削除対象候補をその場で適用
    removed_text = adopted_text
    for candidate in deletion_candidates:
        if candidate in adopted_text:
            removed_text = removed_text.replace(candidate, "", 1)  # 1回のみ削除
    
    # 空白を整理
    if ":" in removed_text:
        speaker_part = removed_text.split(":", 1)[0]
        text_part = removed_text.split(":", 1)[-1].strip()
        text_part = re.sub(r'\s+', ' ', text_part).strip()
        removed_text = f"{speaker_part}: {text_part}"
    else:
        removed_text = re.sub(r'\s+', ' ', removed_text).strip()

    return deletion_candidates, removed_text

def extract_text_part(body: str) -> str:
    """
    発話からテキスト部分を抽出する
    
    Args:
        body (str): 発話本文
        
    Returns:
        str: テキスト部分
    """
    if ":" in body:
        return body.split(":", 1)[-1].strip()
    return body 