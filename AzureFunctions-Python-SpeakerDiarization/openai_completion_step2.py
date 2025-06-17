from typing import List, Dict, Any
from openai_completion_core import client, log_token_usage, _parse_gpt_response
import os

def complete_utterance_with_openai(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ステップ2-①：括弧付きセグメントの補完処理

    Args:
        segments (List[Dict[str, Any]]): セグメントリスト

    Returns:
        List[Dict[str, Any]]: 補完後のセグメントリスト
    """
    result = []
    completion_count = 0
    i = 0
    
    while i < len(segments):
        current = segments[i]
        
        # 括弧付きセグメント（相槌）かどうかをチェック
        if (current.get("text", "").startswith("（") and 
            current.get("text", "").endswith("）")):
            
            # 前後のセグメントを取得
            prev_segment = segments[i - 1] if i > 0 else None
            next_segment = segments[i + 1] if i < len(segments) - 1 else None
            
            # 括弧の内容を抽出
            bracket_content = current.get("text", "")[1:-1]  # （）を除去
            
            # GPT-4oに補完を依頼
            system_message = """あなたは会話の文脈を理解し、括弧付きの断片的な発話を自然に補完するアシスタントです。

以下のルールに従って、前後の文脈を考慮しながら括弧内の内容を補完してください：

1. 括弧内の断片的な語句（例：「夫です。」）を文脈上最も自然な形に補完する
2. 前後の発話内容を参照して、最も適切な補完語を推定する
3. 例：「大丈。」「夫です。」→「大丈夫です。」
4. 補完が不確実な場合は元の内容をそのまま保持する
5. 会話の自然な流れを維持する

出力形式：
{
    "completed_text": "補完後の括弧内テキスト",
    "completion_confidence": 0.0-1.0  // 補完の確信度（0.8以上で補完実行）
}"""

            user_message = f"""前の文: {prev_segment.get('text', '') if prev_segment else ''}
括弧内: {bracket_content}
次の文: {next_segment.get('text', '') if next_segment else ''}

上記の会話に対して、括弧内の内容を補完してください。"""

            try:
                response = client.chat.completions.create(
                    model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.1
                )

                # トークン使用量を記録
                tokens = response.usage.total_tokens
                log_token_usage(tokens, "ステップ2-①補完")

                result_text = response.choices[0].message.content.strip()
                
                # JSONパースの試行
                parsed_result = _parse_gpt_response(result_text)
                
                if parsed_result:
                    completed_text = parsed_result.get("completed_text", bracket_content)
                    confidence = parsed_result.get("completion_confidence", 0.0)
                    
                    # 確信度が0.8以上の場合のみ補完を実行
                    if confidence >= 0.8:
                        current["text"] = f"（{completed_text}）"
                        completion_count += 1
                    
            except Exception as e:
                # エラーは上位で処理
                pass
        
        result.append(current)
        i += 1

    return result 