import re
from typing import List, Dict, Any, Tuple

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

def remove_completion_fragments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ステップ2-②：補完材料の削除処理

    Args:
        segments (List[Dict[str, Any]]): セグメントリスト

    Returns:
        List[Dict[str, Any]]: 削除後のセグメントリスト
    """
    result = []
    removal_count = 0
    i = 0
    
    while i < len(segments):
        current = segments[i]
        
        # 括弧付きセグメント（補完済み）かどうかをチェック
        if (current.get("text", "").startswith("（") and 
            current.get("text", "").endswith("）")):
            
            # 括弧内のテキストを抽出（句読点を除去）
            bracket_content = current.get("text", "")[1:-1]  # （）を除去
            target_text = bracket_content.rstrip('。、，')  # 句読点を除去
            
            # 前後のセグメントを取得
            prev_segment = segments[i - 1] if i > 0 else None
            next_segment = segments[i + 1] if i < len(segments) - 1 else None
            
            # 前後の行で2文字以上の部分文字列を検索
            fragment_removed = False
            
            # 前の行をチェック
            if prev_segment and not fragment_removed:
                prev_text = prev_segment.get("text", "")
                removed_text, removed = _remove_fragment_from_line(prev_text, target_text)
                if removed:
                    prev_segment["text"] = removed_text
                    removal_count += 1
                    fragment_removed = True
            
            # 前の行で削除されなかった場合、次の行をチェック
            if next_segment and not fragment_removed:
                next_text = next_segment.get("text", "")
                removed_text, removed = _remove_fragment_from_line(next_text, target_text)
                if removed:
                    next_segment["text"] = removed_text
                    removal_count += 1
                    fragment_removed = True
        
        result.append(current)
        i += 1

    return result 