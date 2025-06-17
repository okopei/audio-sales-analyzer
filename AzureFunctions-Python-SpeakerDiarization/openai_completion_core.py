import os
import json
import re
from openai import OpenAI
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import demjson3
import traceback

# Azure関連のimportを条件付きで行う
try:
    import pyodbc
    from azure.identity import DefaultAzureCredential
    import struct
    AZURE_AVAILABLE = True
except ImportError as e:
    print('ImportError:', e)
    AZURE_AVAILABLE = False
    pyodbc = None
    DefaultAzureCredential = None
    struct = None

# グローバル変数でトークン使用量を追跡
total_tokens_used = 0

def log_token_usage(tokens: int, operation: str) -> None:
    """トークン使用量を記録する

    Args:
        tokens (int): 使用トークン数
        operation (str): 操作の説明（例：'相槌吸収'）
    """
    global total_tokens_used
    total_tokens_used += tokens

def load_local_settings():
    """local.settings.jsonから環境変数を読み込む

    Returns:
        bool: 読み込みが成功したかどうか
    """
    try:
        # 既に環境変数が設定されている場合はスキップ
        if os.environ.get("OPENAI_API_KEY") and os.environ.get("OPENAI_MODEL"):
            return True

        settings_path = Path(__file__).parent / "local.settings.json"
        if not settings_path.exists():
            return False

        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
            if "Values" not in settings:
                return False

            # 環境変数の設定
            for key, value in settings["Values"].items():
                if key.startswith("OPENAI_"):
                    os.environ[key] = value

            # 必須の環境変数が設定されているか確認
            if not os.environ.get("OPENAI_API_KEY"):
                return False
            if not os.environ.get("OPENAI_MODEL"):
                return False

            return True

    except Exception as e:
        return False

# 環境変数の読み込み（モジュール読み込み時に1回だけ実行）
if not os.environ.get("OPENAI_API_KEY"):
    load_local_settings()

# クライアント初期化（OpenAI本家API用）
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)

@dataclass
class ConversationSegment:
    """会話セグメントのデータクラス"""
    speaker_id: int
    text: str
    duration: float
    offset: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationSegment':
        """辞書からConversationSegmentを生成

        Args:
            data (Dict[str, Any]): セグメントデータ

        Returns:
            ConversationSegment: 生成されたセグメント
        """
        speaker = data.get('speaker', data.get('speakerId', 1))
        text = data.get('text', '')
        if not text and 'nBest' in data:
            text = data['nBest'][0].get('display', '')
        
        duration = float(data.get('durationInTicks', 0)) / 10000000  # 100-nanosecond単位を秒に変換
        offset = float(data.get('offsetInTicks', 0)) / 10000000

        return cls(
            speaker_id=int(speaker),
            text=text.strip(),
            duration=duration,
            offset=offset
        )

def save_step_output(segments: List[Dict[str, Any]], step_num: int) -> None:
    """各ステップの中間結果をファイルに出力する

    Args:
        segments (List[Dict[str, Any]]): 処理済みセグメントリスト
        step_num (int): ステップ番号（1-5、または"2_phase1"、"2_phase2"）
    """
    try:
        # セグメントをテキスト形式に変換
        text = ""
        for seg in segments:
            if seg["text"].strip():  # 空のセグメントはスキップ
                speaker = f"Speaker{seg.get('speaker', '?')}"
                text += f"{speaker}: {seg['text']}\n"

        # ファイルに出力
        if isinstance(step_num, str):
            # 2段階処理の中間結果の場合
            output_path = f"completion_result_step{step_num}.txt"
        else:
            # 通常のステップの場合
            output_path = f"completion_result_step{step_num}.txt"
            
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        pass

def _remove_duplicate_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """重複する発話を除去する

    Args:
        segments (List[Dict[str, Any]]): セグメントリスト

    Returns:
        List[Dict[str, Any]]: 重複を除去したセグメントリスト
    """
    if not segments:
        return []

    result = []
    prev_segment = None

    for current in segments:
        # 前のセグメントと比較
        if (prev_segment and 
            prev_segment.get("speaker") == current.get("speaker") and 
            prev_segment.get("text") == current.get("text")):
            # 重複している場合はスキップ
            continue

        result.append(current)
        prev_segment = current

    return result

def _extract_json_from_response(response_text: str) -> Optional[str]:
    """GPTの応答からJSONを抽出する

    Args:
        response_text (str): GPTの応答テキスト

    Returns:
        Optional[str]: 抽出されたJSON文字列。抽出できない場合はNone
    """
    try:
        # Markdown形式のコードブロックからJSONを抽出
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", response_text)
        if match:
            cleaned_json = match.group(1).strip()
            return cleaned_json
        
        # 通常のJSON形式の場合
        if response_text.strip().startswith("{") and response_text.strip().endswith("}"):
            return response_text.strip()
        
        # その他の形式の場合
        return None

    except Exception as e:
        return None

def _parse_gpt_response(response_text: str) -> Optional[Dict[str, Any]]:
    """GPTの応答をパースする

    Args:
        response_text (str): GPTの応答テキスト

    Returns:
        Optional[Dict[str, Any]]: パース結果。失敗時はNone
    """
    try:
        # JSON文字列の抽出
        json_str = _extract_json_from_response(response_text)
        if not json_str:
            return None

        # 通常のJSONパースを試行
        try:
            parsed = json.loads(json_str)
            return parsed
        except json.JSONDecodeError as e:
            # demjson3による緩和されたパースを試行
            try:
                parsed = demjson3.decode(json_str)
                return parsed
            except Exception as e2:
                return None

    except Exception as e:
        return None

def clean_and_complete_conversation(segments: List[Dict[str, Any]]) -> Optional[str]:
    """会話セグメントを整形・補完する

    Args:
        segments (List[Dict[str, Any]]): 会話セグメントのリスト

    Returns:
        Optional[str]: 整形済みテキスト。エラー時はNone
    """
    try:
        # 各ステップのモジュールをインポート
        from openai_completion_step1 import add_brackets_to_short_segments
        from openai_completion_step2 import complete_utterance_with_openai
        from openai_completion_step3 import remove_completion_fragments
        from openai_completion_step4 import merge_backchannel_with_next
        from openai_completion_step5 import merge_same_speaker_segments
        from openai_completion_step6 import remove_fillers_with_openai
        
        # ステップ1: 短い相槌を括弧で囲む
        processed_segments = add_brackets_to_short_segments(segments)
        processed_segments = _remove_duplicate_segments(processed_segments)
        
        # ステップ2-①: OpenAIによる補完
        processed_segments = complete_utterance_with_openai(processed_segments)
        
        # ステップ2-②: 補完材料の削除
        processed_segments = remove_completion_fragments(processed_segments)
        save_step_output(processed_segments, "2_phase2")
        
        # ステップ3: 括弧付きセグメントの吸収
        processed_segments = merge_backchannel_with_next(processed_segments)
        
        # ステップ4: 同一話者の発言連結
        processed_segments = merge_same_speaker_segments(processed_segments)
        
        # ステップ5: フィラー削除
        processed_segments = remove_fillers_with_openai(processed_segments)
        save_step_output(processed_segments, 5)
        
        # 最終結果をテキスト形式で返す
        result_lines = []
        for seg in processed_segments:
            if seg.get("text", "").strip():
                speaker = f"Speaker{seg.get('speaker', '?')}"
                result_lines.append(f"{speaker}: {seg['text']}")
        
        result_text = "\n".join(result_lines)
        
        return result_text

    except Exception as e:
        traceback.print_exc()
        return None 

def load_transcript_segments(meeting_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    meeting_idを指定してDBからtranscript_textを取得し、セグメント化する。
    Returns:
        List[Dict[str, Any]]: セグメントリスト
    """
    if meeting_id is None:
        return []
    
    if not AZURE_AVAILABLE:
        return []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT transcript_text FROM dbo.Meetings WHERE meeting_id = ?", (meeting_id,))
        row = cursor.fetchone()
        
        if row and row[0]:
            transcript_text = row[0]
            
            # transcript_textをセグメント化
            segments = []
            
            # (Speaker1)[...]形式のパターンを検索
            import re
            pattern = r'\(Speaker(\d+)\)\[([^\]]*)\]'
            matches = re.findall(pattern, transcript_text)
            
            if matches:
                # マッチしたセグメントを処理
                for speaker_id, text in matches:
                    if text.strip():  # 空のテキストはスキップ
                        segments.append({
                            "speaker": int(speaker_id),
                            "text": text.strip(),
                            "duration": 0,
                            "offset": 0
                        })
            else:
                # 従来の行単位処理を試行
                lines = transcript_text.splitlines()
                
                for i, line in enumerate(lines):
                    if line.strip():  # 空行をスキップ
                        m = re.match(r"Speaker(\d+):(.+)", line)
                        if not m:
                            m = re.match(r"\(Speaker(\d+)\)\[(.+?)\]", line)
                        if m:
                            segments.append({
                                "speaker": int(m.group(1)),
                                "text": m.group(2).strip(),
                                "duration": 0,
                                "offset": 0
                            })
            
            if segments:
                return segments
            else:
                return []
        else:
            return []
            
    except Exception as e:
        return []
    finally:
        try:
            if 'conn' in locals():
                conn.close()
        except Exception:
            pass

# get_db_connection関数をopenai_completion_core.py内に直接実装
def get_db_connection():
    """
    Entra ID認証を使用してAzure SQL Databaseに接続する
    
    Returns:
        pyodbc.Connection: データベース接続オブジェクト
        
    Raises:
        Exception: 接続に失敗した場合
    """
    if not AZURE_AVAILABLE:
        raise Exception("Azure関連のモジュールが利用できません")
    
    try:
        credential = DefaultAzureCredential()
        token = credential.get_token("https://database.windows.net/.default")
        token_bytes = bytes(token.token, 'utf-8')
        exptoken = b''.join(bytes((b, 0)) for b in token_bytes)
        access_token = struct.pack('=i', len(exptoken)) + exptoken

        conn_str = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:w-paas-salesanalyzer-sqlserver.database.windows.net,1433;"
            f"Database=w-paas-salesanalyzer-sql;"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )

        return pyodbc.connect(conn_str, attrs_before={1256: access_token})
    except Exception as e:
        raise 