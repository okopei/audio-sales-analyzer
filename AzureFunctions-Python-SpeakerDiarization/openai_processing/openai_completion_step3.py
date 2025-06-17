import re
import logging
from typing import List, Dict, Any, Tuple

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

def has_common_fragment(last_text: str, bracket_text: str, min_match: int = 2) -> bool:
    """
    末尾の断片と括弧内の補完テキストに、句読点を除外した状態で
    2文字以上の連続した共通部分が存在するか判定する
    
    Args:
        last_text (str): 末尾の断片テキスト（削除対象）
        bracket_text (str): 括弧内の補完テキスト（完全版）
        min_match (int): 最小一致文字数
        
    Returns:
        bool: 断片が補完テキストに含まれている場合True
    """
    def normalize(text):
        return re.sub(r"[。、！？\s]", "", text)

    last_norm = normalize(last_text)
    bracket_norm = normalize(bracket_text)

    # 断片（last_norm）が補完テキスト（bracket_norm）に含まれているかチェック
    # 最小一致文字数以上の部分文字列を検索
    for i in range(len(last_norm) - min_match + 1):
        frag = last_norm[i:i + min_match]
        if frag in bracket_norm:
            return True
    return False

def _remove_fragment_from_line(line_text: str, target_text: str) -> tuple[str, bool]:
    """行テキストから補完材料の断片を削除する

    Args:
        line_text (str): 行テキスト
        target_text (str): 補完後の括弧内テキスト（句読点除去済み）

    Returns:
        tuple[str, bool]: (削除後のテキスト, 削除が実行されたかどうか)
    """
    try:
        # 行テキストから削除可能な断片を検索
        # 句読点で区切られた部分を個別にチェック
        fragments = []
        
        # 句読点で区切って各部分を抽出
        parts = re.split(r'[。、，]', line_text)
        
        for part in parts:
            part = part.strip()
            if len(part) >= 2:  # 2文字以上の部分のみ対象
                fragments.append(part)
        
        # 各断片について、補完後のテキストに含まれているかチェック
        for fragment in fragments:
            # 句読点付きの形で検索
            candidates = [
                f"{fragment}。",
                f"{fragment}、",
                f"{fragment}，",
                fragment  # 句読点なしも含める
            ]
            
            for candidate in candidates:
                if candidate in line_text:
                    # この断片が補完後のテキストに含まれているかチェック（句読点を考慮）
                    if has_common_fragment(fragment, target_text):
                        # 削除実行（1回のみ）
                        removed_text = line_text.replace(candidate, "", 1)
                        return removed_text, True
        
        return line_text, False
        
    except Exception as e:
        return line_text, False

def remove_completion_fragments_text(text: str) -> str:
    """ステップ2-②：補完材料の削除処理（文字列ベース）

    Args:
        text (str): 入力テキスト（改行区切りの行）

    Returns:
        str: 削除後のテキスト
    """
    if not text or not text.strip():
        return text
    
    lines = text.strip().split('\n')
    result_lines = []
    removal_count = 0
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            result_lines.append(line)
            continue
        
        # 本文とoffsetを分離
        body, offset = extract_offset_from_line(line)
        
        # 括弧付きセグメント（補完済み）かどうかをチェック
        if (body.startswith("（") and body.endswith("）")):
            
            # 括弧内のテキストを抽出（句読点を除去）
            bracket_content = body[1:-1]  # （）を除去
            target_text = bracket_content.rstrip('。、，')  # 句読点を除去
            
            # 前後の行を取得
            prev_line = lines[i - 1] if i > 0 else ""
            next_line = lines[i + 1] if i < len(lines) - 1 else ""
            
            # 前後の行から本文を抽出
            prev_body, prev_offset = extract_offset_from_line(prev_line)
            next_body, next_offset = extract_offset_from_line(next_line)
            
            # 前後の行で2文字以上の部分文字列を検索
            fragment_removed = False
            
            # 前の行をチェック
            if prev_body and not fragment_removed:
                removed_text, removed = _remove_fragment_from_line(prev_body, target_text)
                if removed:
                    # offsetを再付与
                    prev_final = removed_text + prev_offset if prev_offset else removed_text
                    result_lines[-1] = prev_final  # 前の行を更新
                    removal_count += 1
                    fragment_removed = True
            
            # 前の行で削除されなかった場合、次の行をチェック
            if next_body and not fragment_removed:
                removed_text, removed = _remove_fragment_from_line(next_body, target_text)
                if removed:
                    # 次の行を更新（次のループで処理される）
                    lines[i + 1] = removed_text + next_offset if next_offset else removed_text
                    removal_count += 1
                    fragment_removed = True
        
        # offsetを再付与
        final_line = body + offset if offset else body
        result_lines.append(final_line)

    return '\n'.join(result_lines)

def step3_remove_completion_materials(segments: list) -> list:
    """
    ステップ3: 補完材料の削除
    """
    logger.info("ステップ3: 補完材料の削除を開始")
    
    # セグメントリストを文字列に変換
    text_lines = []
    for segment in segments:
        speaker = segment.get("speaker", "Unknown")
        text = segment.get("text", "").strip()
        offset = segment.get("offset", 0.0)
        line = f"Speaker{speaker}: {text}({offset})"
        text_lines.append(line)
    
    text = '\n'.join(text_lines)
    
    # 文字列ベースの処理を実行
    processed_text = remove_completion_fragments_text(text)
    
    # 結果をセグメントリストに戻す
    result = []
    for line in processed_text.strip().split('\n'):
        if line.strip():
            # 行をパースしてセグメントに変換
            body, offset_str = extract_offset_from_line(line)
            if offset_str:
                offset = float(offset_str.strip('()'))
            else:
                offset = 0.0
            
            # Speaker部分を抽出
            speaker_match = re.match(r"Speaker(\d+): (.+)", body)
            if speaker_match:
                speaker = int(speaker_match.group(1))
                text = speaker_match.group(2).strip()
                result.append({
                    "speaker": speaker,
                    "text": text,
                    "offset": offset
                })
    
    logger.info("ステップ3: 補完材料の削除が完了")
    return result 