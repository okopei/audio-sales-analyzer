import re
import logging
import json
from .openai_completion_core import client, log_token_usage, _parse_gpt_response
import os

logger = logging.getLogger(__name__)

def evaluate_connection_naturalness_no_period(front_text: str, bracket_text: str, back_text: str) -> dict:
    """
    括弧内発話の前後接続の自然さをスコアリング評価する（句点削除・自然接続判定）

    Args:
        front_text (str): 前の文（句点なし）
        bracket_text (str): 括弧内の発話（句点なし）
        back_text (str): 後の文（句点なし）

    Returns:
        dict: 前接続スコアと後接続スコアを含む辞書
    """
    system_message = """
あなたは会話の自然さを判定する日本語特化の言語モデルです。
2つの文の自然さを比較し、それぞれスコア（0.0〜1.0）で評価してください。

評価基準：
- 1.0: 文法的に正しく、意味が通じる自然な会話
- 0.8-0.9: ほぼ自然で理解しやすい
- 0.6-0.7: やや不自然だが理解可能
- 0.4-0.5: 不自然で理解しにくい
- 0.2-0.3: 非常に不自然
- 0.0-0.1: 文法的に破綻している、意味不明

特に以下の点を重視してください：
- 文法的な正しさ
- 意味の通じやすさ
- 日本語として自然な語順
- 敬語や丁寧語の適切な使用

出力形式：
{
  "front_score": 0.0-1.0,
  "back_score": 0.0-1.0
}
"""

    user_message = f"""次の2つの文を比較してください：

1. 前文接続: {front_text}{bracket_text}
2. 後文接続: {bracket_text}{back_text}

各文について自然さを評価し、以下の形式で出力してください：
{{
  "front_score": 0.0-1.0,
  "back_score": 0.0-1.0
}}"""

    try:
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            max_tokens=200
        )

        result = response.choices[0].message.content.strip()
        log_token_usage(response.usage.total_tokens, "step2_no_period_scoring_evaluation")

        parsed_result = _parse_gpt_response(result)
        if parsed_result:
            return {
                "front_score": float(parsed_result.get("front_score", 0.0)),
                "back_score": float(parsed_result.get("back_score", 0.0))
            }
        else:
            return {"front_score": 0.5, "back_score": 0.5}

    except Exception as e:
        logger.error(f"句点削除版スコアリング評価エラー: {e}")
        return {"front_score": 0.5, "back_score": 0.5}
