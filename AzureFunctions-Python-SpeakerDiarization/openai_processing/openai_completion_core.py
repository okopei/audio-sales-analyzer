import os
import json
import re
import logging
from openai import OpenAI
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import demjson3
import traceback

logger = logging.getLogger(__name__)

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

def clean_and_complete_conversation(meeting_id: int) -> bool:
    """
    会話データを段階的にクリーンアップ・補完する
    """
    try:
        # データベースから会話データを取得
        segments = load_transcript_segments(meeting_id)
        if not segments:
            logger.warning(f"会話データが見つかりません: meeting_id={meeting_id}")
            return False
        
        logger.info(f"会話データの処理を開始: {len(segments)}セグメント")
        
        # ステップ1: フォーマットとオフセット処理
        from .openai_completion_step1 import step1_format_with_offset
        segments = step1_format_with_offset(segments)
        
        # ステップ2: 不完全な文の補完
        from .openai_completion_step2 import step2_complete_incomplete_sentences
        segments = step2_complete_incomplete_sentences(segments)
        
        # ステップ3: 補完材料の削除
        from .openai_completion_step3 import step3_remove_completion_materials
        segments = step3_remove_completion_materials(segments)
        
        # ステップ4: 相槌と次の発話の統合
        from .openai_completion_step4 import step4_merge_backchannel_with_next
        segments = step4_merge_backchannel_with_next(segments)
        
        # ステップ5: 同一話者の連続セグメントの統合
        from .openai_completion_step5 import step5_merge_same_speaker_segments
        segments = step5_merge_same_speaker_segments(segments)
        
        # ステップ6: フィラー削除
        from .openai_completion_step6 import step6_remove_fillers
        segments = step6_remove_fillers(segments)
        
        # 処理結果をデータベースに保存
        save_processed_segments(meeting_id, segments)
        
        logger.info(f"会話データの処理が完了: meeting_id={meeting_id}")
        return True
        
    except Exception as e:
        logger.error(f"会話データの処理中にエラーが発生: meeting_id={meeting_id}, error={e}")
        logger.error(traceback.format_exc())
        return False

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

def save_processed_segments(meeting_id: int, segments: List[Dict[str, Any]]) -> bool:
    """
    処理済みセグメントをデータベースに保存する
    
    Args:
        meeting_id (int): 会議ID
        segments (List[Dict[str, Any]]): 処理済みセグメントリスト
        
    Returns:
        bool: 保存が成功したかどうか
    """
    if not AZURE_AVAILABLE:
        logger.warning("Azure関連のモジュールが利用できません")
        return False
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 既存のConversationSegmentを削除
        cursor.execute("DELETE FROM dbo.ConversationSegment WHERE meeting_id = ?", (meeting_id,))
        
        # 新しいセグメントを挿入
        for segment in segments:
            speaker_id = segment.get("speaker", 1)
            text = segment.get("text", "").strip()
            offset = segment.get("offset", 0.0)
            
            if text:  # 空のテキストはスキップ
                cursor.execute("""
                    INSERT INTO dbo.ConversationSegment 
                    (meeting_id, speaker_id, text, start_time, end_time, duration)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (meeting_id, speaker_id, text, offset, None, 0))
        
        conn.commit()
        logger.info(f"処理済みセグメントを保存しました: meeting_id={meeting_id}, segments={len(segments)}")
        return True
        
    except Exception as e:
        logger.error(f"セグメント保存中にエラーが発生: meeting_id={meeting_id}, error={e}")
        return False
    finally:
        try:
            if 'conn' in locals():
                conn.close()
        except Exception:
            pass 