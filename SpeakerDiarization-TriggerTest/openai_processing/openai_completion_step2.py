import re
import logging
import json
from .openai_completion_core import client, log_token_usage, _parse_gpt_response
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def extract_offset_from_line(line: str) -> tuple[str, str]:
    """行から本文とoffsetを分離する

    Args:
        line (str): 入力行（例：'Speaker1: こんにちは。(12.5)'）

    Returns:
        tuple[str, str]: (本文, offset) または (元の行, '') のタプル
    """
    match = re.match(r"(Speaker\d+: .*?)\s*\((\d+(\.\d+)?)\)$", line)
    if match:
        body = match.group(1).rstrip()    # ex. 'Speaker1: こんにちは。'
        offset = f"({match.group(2)})"    # ex. '(12.5)'
        return body, offset
    else:
        return line, ""  # offsetなし行

def extract_last_sentence(text: str) -> str:
    """
    テキストから最後の文（句点で終わる部分）を抽出する
    
    Args:
        text (str): 入力テキスト
        
    Returns:
        str: 最後の文（句点で終わる部分）
    """
    if not text:
        return ""
    
    # Speaker部分を除去
    if ":" in text:
        text = text.split(":", 1)[-1].strip()
    
    # 句点で分割して最後の文を取得
    sentences = text.split("。")
    if len(sentences) > 1:
        # 最後の文（句点を含む）
        last_sentence = sentences[-2] + "。" if sentences[-2] else ""
        return last_sentence
    else:
        # 句点がない場合は全体を返す
        return text

def extract_first_sentence(text: str) -> str:
    """
    テキストから最初の文（最初の句点まで）を抽出する
    
    Args:
        text (str): 入力テキスト
        
    Returns:
        str: 最初の文（句点で終わる部分）
    """
    if not text:
        return ""
    
    # Speaker部分を除去
    if ":" in text:
        text = text.split(":", 1)[-1].strip()
    
    # 最初の句点までを取得
    if "。" in text:
        first_sentence = text.split("。")[0] + "。"
        return first_sentence
    else:
        # 句点がない場合は全体を返す
        return text

def extract_last_complete_sentence(text: str) -> str:
    """
    文末の句点「。」まで含む最後の文を抽出
    
    Args:
        text (str): 入力テキスト
        
    Returns:
        str: 最後の完全な文（句点を含む）
    """
    if not text:
        return ""
    
    # Speaker部分を除去
    if ":" in text:
        text = text.split(":", 1)[-1].strip()
    
    # 句点で終わる文を正規表現で抽出
    sentences = re.findall(r"[^。]*?。", text)
    return sentences[-1].strip() if sentences else text.strip()

def extract_last_sentence_no_period(text: str) -> str:
    """
    テキストから最後の文を抽出し、句点を削除する
    
    Args:
        text (str): 入力テキスト
        
    Returns:
        str: 最後の文（句点なし）
    """
    if not text:
        return ""

    if ":" in text:
        text = text.split(":", 1)[-1].strip()

    sentences = text.split("。")
    if len(sentences) > 1:
        # 最後の文（句点を削除）
        last_sentence = sentences[-2] if sentences[-2] else ""
        return last_sentence
    else:
        # 句点がない場合は全体を返す（句点があれば削除）
        return text.strip("。")

def extract_first_sentence_no_period(text: str) -> str:
    """
    テキストから最初の文を抽出し、句点を削除する
    
    Args:
        text (str): 入力テキスト
        
    Returns:
        str: 最初の文（句点なし）
    """
    if not text:
        return ""
    
    # Speaker部分を除去
    if ":" in text:
        text = text.split(":", 1)[-1].strip()
    
    # 最初の句点までを取得（句点を削除）
    if "。" in text:
        first_sentence = text.split("。")[0]
        return first_sentence
    else:
        # 句点がない場合は全体を返す
        return text

def step2_complete_incomplete_sentences(segments: list) -> list:
    """
    ステップ2: 括弧内発話の前後接続自然さスコアリング評価（句点削除・自然接続判定）
    
    Args:
        segments (list): 文字列リスト（各行が "SpeakerX: 本文(offset)" 形式）
        
    Returns:
        list: 処理済みの文字列リスト（スコア付き）
    """
    logger.info("ステップ2: 括弧内発話の前後接続自然さスコアリング評価（句点削除・自然接続判定）を開始")
    logger.info(f"入力セグメント数: {len(segments)}")
    
    if not segments:
        return segments
    
    result_segments = []
    processed_count = 0
    bracket_count = 0
    
    # 出力ファイルの準備
    output_path = Path("outputs/completion_result_step2.txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    for i, segment in enumerate(segments):
        if not isinstance(segment, str) or not segment.strip():
            result_segments.append(segment)
            continue
        
        segment = segment.strip()
        logger.debug(f"処理中: {i+1}/{len(segments)} - {segment}")
        
        # 括弧内発話かどうかを最初にチェック
        if segment.startswith("Speaker") and "（" in segment and "）" in segment:
            bracket_count += 1
            logger.info(f"括弧内発話を発見: {segment}")
            
            body, offset = extract_offset_from_line(segment)
            
            # 括弧内だけの発話であることを確認
            body_without_speaker = body.split(":", 1)[-1].strip()
            if body_without_speaker.startswith("（") and body_without_speaker.endswith("）"):
                logger.info(f"括弧内だけの発話を確認: {body_without_speaker}")
                
                # 前後の行を取得
                prev_segment = segments[i - 1] if i > 0 else ""
                next_segment = segments[i + 1] if i < len(segments) - 1 else ""
                
                # 前後の行から本文を抽出
                prev_body, _ = extract_offset_from_line(prev_segment)
                next_body, _ = extract_offset_from_line(next_segment)
                
                # 括弧の内容を抽出
                bracket_content = body_without_speaker[1:-1]  # （）を除去
                
                # 前の発話の最後の完全な文を抽出
                front_complete_sentence = extract_last_complete_sentence(prev_body)
                # 句点を削除した前文を取得
                front_sentence = extract_last_sentence_no_period(prev_body)
                # 句点を削除した後文を取得
                back_sentence = extract_first_sentence_no_period(next_body)
                bracket_no_period = bracket_content.strip("。")
                
                logger.info(f"前の完全文: {front_complete_sentence}")
                logger.info(f"前の文（句点なし）: {front_sentence}")
                logger.info(f"括弧内（句点なし）: {bracket_no_period}")
                logger.info(f"後の文（句点なし）: {back_sentence}")
                
                # スコアリング評価を実行
                score_result = evaluate_connection_naturalness_no_period(front_sentence, bracket_no_period, back_sentence)
                
                # 結果を適用
                front_score = score_result.get("front_score", 0.0)
                back_score = score_result.get("back_score", 0.0)
                
                logger.info(f"前接続スコア: {front_score}, 後接続スコア: {back_score}")
                
                # スコア付きの結果行を作成
                speaker_prefix = body.split(':', 1)[0]
                scored_segment = f"{speaker_prefix}: （{bracket_content}）{offset} [前:{front_score:.1f} 後:{back_score:.1f}]"
                
                # 結果を追加
                result_segments.append(scored_segment)
                processed_count += 1
                
                # ファイルに追記出力
                with open(output_path, "a", encoding="utf-8") as f:
                    f.write(scored_segment + "\n")
                
                logger.info(f"スコアリング完了: {segment} → {scored_segment}")
                
            else:
                # 括弧内だけの発話でない場合はそのまま
                logger.debug(f"括弧内だけの発話ではないためスキップ: {body_without_speaker}")
                result_segments.append(segment)
        else:
            # 括弧付きでない場合はそのまま
            result_segments.append(segment)
    
    logger.info(f"括弧を含むセグメント数: {bracket_count}")
    logger.info(f"ステップ2完了: {processed_count}件の括弧内発話をスコアリング評価")
    
    # トークン使用量のサマリーを出力
    from .openai_completion_core import total_tokens_used
    logger.info(f"🧾 Step2 Total Token Usage: {total_tokens_used}")
    
    return result_segments

def complete_utterance_with_openai(text: str) -> str:
    """
    OpenAIを使用して不完全な発話を補完する
    """
    if not text.strip():
        return text
    
    prompt = f"""
以下の不完全な発話を自然に補完してください。補完する際は以下のルールに従ってください：

1. 元の文の意味を変えない
2. 自然な日本語になるように補完
3. 補完部分は【】で囲む
4. 元の文が既に完全な場合は補完しない

不完全な発話: {text}

補完結果:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは日本語の会話を自然に補完する専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        result = response.choices[0].message.content.strip()
        log_token_usage(response.usage, "step2_complete")
        
        # 補完結果を解析
        parsed_result = _parse_gpt_response(result)
        if parsed_result and "completed_text" in parsed_result:
            return parsed_result["completed_text"]
        else:
            return text
        
    except Exception as e:
        logger.error(f"OpenAI補完エラー: {e}")
        return text

def complete_utterance_with_openai_text(text: str) -> str:
    """ステップ2-①：括弧付きセグメントの補完処理（文字列ベース）

    Args:
        text (str): 入力テキスト（改行区切りの行）

    Returns:
        str: 補完後のテキスト
    """
    if not text or not text.strip():
        return text
    
    lines = text.strip().split('\n')
    result_lines = []
    completion_count = 0
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            result_lines.append(line)
            continue
        
        # 本文とoffsetを分離
        body, offset = extract_offset_from_line(line)
        
        # 括弧付きセグメント（相槌）かどうかをチェック
        if (body.startswith("（") and body.endswith("）")):
            
            # 前後の行を取得
            prev_line = lines[i - 1] if i > 0 else ""
            next_line = lines[i + 1] if i < len(lines) - 1 else ""
            
            # 前後の行から本文を抽出
            prev_body, _ = extract_offset_from_line(prev_line)
            next_body, _ = extract_offset_from_line(next_line)
            
            # 括弧の内容を抽出
            bracket_content = body[1:-1]  # （）を除去
            
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

            user_message = f"""前の文: {prev_body}
括弧内: {bracket_content}
次の文: {next_body}

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
                        completed_body = f"（{completed_text}）"
                        completion_count += 1
                    else:
                        completed_body = body
                else:
                    completed_body = body
                    
            except Exception as e:
                # エラーが発生した場合は元の内容を保持
                completed_body = body
        
        else:
            # 括弧付きでない場合はそのまま
            completed_body = body
        
        # offsetを付けて結果行を作成
        result_line = f"{completed_body}{offset}"
        result_lines.append(result_line)
    
    logger.info(f"ステップ2-①完了: {completion_count}件の括弧付きセグメントを補完")
    return "\n".join(result_lines)

def complete_utterance_with_openai(segments: list) -> list:
    """
    ステップ2-②：不完全な発話の補完処理（セグメントベース）
    """
    logger.info("ステップ2-②: 不完全な発話の補完を開始")
    
    result_segments = []
    completion_count = 0
    
    for segment in segments:
        if not isinstance(segment, dict):
            result_segments.append(segment)
            continue
        
        text = segment.get("text", "")
        if not text:
            result_segments.append(segment)
            continue
        
        # 不完全な発話の補完
        completed_text = complete_utterance_with_openai(text)
        
        if completed_text != text:
            segment["text"] = completed_text
            completion_count += 1
        
        result_segments.append(segment)
    
    logger.info(f"ステップ2-②完了: {completion_count}件の発話を補完")
    return result_segments

def evaluate_connection_naturalness(prev_text: str, bracket_text: str, next_text: str) -> dict:
    """
    括弧内発話の前後接続の自然さをスコアリング評価する
    
    Args:
        prev_text (str): 前の発話
        bracket_text (str): 括弧内の発話
        next_text (str): 次の発話
        
    Returns:
        dict: 前接続スコアと後接続スコアを含む辞書
    """
    system_message = """
あなたは会話の自然さを評価する言語モデルです。
与えられた2つの文を比較し、どちらが日本語の会話としてより自然かを判断し、それぞれに 0.0〜1.0 のスコアを与えてください。

評価基準：
- 1.0: 非常に自然で自然な会話
- 0.8-0.9: 自然で理解しやすい
- 0.6-0.7: やや不自然だが理解可能
- 0.4-0.5: 不自然で理解しにくい
- 0.2-0.3: 非常に不自然
- 0.0-0.1: 文法的に破綻している

出力形式：
{
  "front_score": 0.0-1.0,
  "back_score": 0.0-1.0
}"""

    user_message = f"""次の2つの文を比較してください：

1. 前文接続: {prev_text}{bracket_text}
2. 後文接続: {bracket_text}{next_text}

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
        
        # トークン使用量のデバッグ出力
        total_tokens = response.usage.total_tokens
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        
        logger.debug(f"🧾 Step2 Scoring Token Usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
        
        result = response.choices[0].message.content.strip()
        log_token_usage(response.usage.total_tokens, "step2_scoring_evaluation")
        
        # JSONパース
        parsed_result = _parse_gpt_response(result)
        if parsed_result:
            return {
                "front_score": float(parsed_result.get("front_score", 0.0)),
                "back_score": float(parsed_result.get("back_score", 0.0))
            }
        else:
            # パース失敗時はデフォルトスコア
            return {
                "front_score": 0.5,
                "back_score": 0.5
            }
            
    except Exception as e:
        logger.error(f"スコアリング評価エラー: {e}")
        return {
            "front_score": 0.5,
            "back_score": 0.5
        }

def evaluate_connection_naturalness_sentence(front_sentence: str, bracket_text: str, back_sentence: str) -> dict:
    """
    括弧内発話の前後接続の自然さをスコアリング評価する（文単位対応）
    
    Args:
        front_sentence (str): 前の文（句点で終わる）
        bracket_text (str): 括弧内の発話
        back_sentence (str): 後の文（句点で終わる）
        
    Returns:
        dict: 前接続スコアと後接続スコアを含む辞書
    """
    system_message = """
あなたは会話の自然さを評価する日本語専門の言語モデルです。
与えられた2つの文について、それぞれの自然さを0.0〜1.0で評価してください。

評価基準：
- 1.0: 非常に自然で自然な会話
- 0.8-0.9: 自然で理解しやすい
- 0.6-0.7: やや不自然だが理解可能
- 0.4-0.5: 不自然で理解しにくい
- 0.2-0.3: 非常に不自然
- 0.0-0.1: 文法的に破綻している

出力形式：
{
  "front_score": 0.0-1.0,
  "back_score": 0.0-1.0
}"""

    user_message = f"""次の2つの文を比較してください：

1. 前文接続: {front_sentence}{bracket_text}
2. 後文接続: {bracket_text}{back_sentence}

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
        
        # トークン使用量のデバッグ出力
        total_tokens = response.usage.total_tokens
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        
        logger.debug(f"🧾 Step2 Sentence Scoring Token Usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
        
        result = response.choices[0].message.content.strip()
        log_token_usage(response.usage.total_tokens, "step2_sentence_scoring_evaluation")
        
        # JSONパース
        parsed_result = _parse_gpt_response(result)
        if parsed_result:
            return {
                "front_score": float(parsed_result.get("front_score", 0.0)),
                "back_score": float(parsed_result.get("back_score", 0.0))
            }
        else:
            # パース失敗時はデフォルトスコア
            return {
                "front_score": 0.5,
                "back_score": 0.5
            }
            
    except Exception as e:
        logger.error(f"文単位スコアリング評価エラー: {e}")
        return {
            "front_score": 0.5,
            "back_score": 0.5
        }

def evaluate_connection_naturalness_no_period(front_sentence: str, bracket_text: str, back_sentence: str) -> dict:
    """
    括弧内発話の前後接続の自然さをスコアリング評価する（句点削除・自然接続判定）
    
    Args:
        front_sentence (str): 前の文（句点なし）
        bracket_text (str): 括弧内の発話（句点なし）
        back_sentence (str): 後の文（句点なし）
        
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
}"""

    user_message = f"""次の2つの文を比較してください：

1. 前文接続: {front_sentence}{bracket_text}
2. 後文接続: {bracket_text}{back_sentence}

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
        
        # トークン使用量のデバッグ出力
        total_tokens = response.usage.total_tokens
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        
        logger.debug(f"🧾 Step2 No Period Scoring Token Usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
        
        result = response.choices[0].message.content.strip()
        log_token_usage(response.usage.total_tokens, "step2_no_period_scoring_evaluation")
        
        # JSONパース
        parsed_result = _parse_gpt_response(result)
        if parsed_result:
            return {
                "front_score": float(parsed_result.get("front_score", 0.0)),
                "back_score": float(parsed_result.get("back_score", 0.0))
            }
        else:
            # パース失敗時はデフォルトスコア
            return {
                "front_score": 0.5,
                "back_score": 0.5
            }
            
    except Exception as e:
        logger.error(f"句点削除版スコアリング評価エラー: {e}")
        return {
            "front_score": 0.5,
            "back_score": 0.5
        } 