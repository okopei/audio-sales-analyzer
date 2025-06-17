import re
import logging
from .openai_completion_core import client, log_token_usage, _parse_gpt_response
import os

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

def step2_complete_incomplete_sentences(segments: list) -> list:
    """
    ステップ2: 不完全な文を補完する
    """
    logger.info("ステップ2: 不完全な文の補完を開始")
    
    for i, segment in enumerate(segments):
        if not segment.get('text', '').strip():
            continue
            
        original_text = segment['text']
        completed_text = complete_utterance_with_openai(original_text)
        
        if completed_text != original_text:
            logger.info(f"補完: {original_text} -> {completed_text}")
            segments[i]['text'] = completed_text
    
    logger.info("ステップ2: 不完全な文の補完が完了")
    return segments

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
        
        # offsetを再付与
        final_line = completed_body + offset if offset else completed_body
        result_lines.append(final_line)

    return '\n'.join(result_lines)

def complete_utterance_with_openai(segments: list) -> list:
    """ステップ2-①：括弧付きセグメントの補完処理（後方互換性のため残す）

    Args:
        segments (List[Dict[str, Any]]): セグメントリスト

    Returns:
        List[Dict[str, Any]]: 補完後のセグメントリスト
    """
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
    processed_text = complete_utterance_with_openai_text(text)
    
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
    
    return result 