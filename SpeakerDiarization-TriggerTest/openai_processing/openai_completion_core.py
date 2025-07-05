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

# ロギング設定を追加
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# スクリプトの場所を基準としたベースディレクトリを設定
BASE_DIR = Path(__file__).resolve().parent
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

        settings_path = BASE_DIR / "local.settings.json"
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
    print(f"[DEBUG] save_step_output() が呼ばれました（step_num={step_num}）")
    print(f"[DEBUG] ステップ{step_num}のセグメント数: {len(segments)}")
    
    try:
        # セグメントをテキスト形式に変換
        text = ""
        for seg in segments:
            try:
                if isinstance(seg, dict):
                    text_val = seg["text"]
                    speaker_val = f"Speaker{seg.get('speaker', '?')}"
                elif isinstance(seg, ConversationSegment):
                    text_val = seg.text
                    speaker_val = f"Speaker{seg.speaker_id}"
                else:
                    continue

                if text_val.strip():
                    text += f"{speaker_val}: {text_val.strip()}\n"

            except Exception as e:
                print(f"[DEBUG] セグメント出力時エラー: {e}")
                continue

        # 出力ディレクトリの準備
        output_dir = BASE_DIR / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 出力ファイルパスの設定
        if isinstance(step_num, str):
            # 2段階処理の中間結果の場合
            output_path = output_dir / f"completion_result_step{step_num}.txt"
        else:
            # 通常のステップの場合
            output_path = output_dir / f"completion_result_step{step_num}.txt"
        
        # デバッグ用：出力先の確認
        print(f"[DEBUG] 出力先ディレクトリ: {output_dir}")
        print(f"[DEBUG] 出力ファイルパス: {output_path}")
        
        # ファイル出力前のデバッグログ
        logger.info(f"✅ completion_result_step{step_num}.txt を出力します: {output_path}")
            
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
            
        print(f"[DEBUG] save_step_output: ステップ{step_num}の結果を正常に出力しました")
        
        # ファイル作成の確認
        if output_path.exists():
            print(f"[DEBUG] ✅ ファイル作成成功: {output_path}")
        else:
            print(f"[ERROR] ❌ ファイル作成失敗: {output_path} が存在しません")
        
    except Exception as e:
        logger.error(f"[save_step_output] ステップ{step_num}の結果出力に失敗しました: {e}")
        traceback.print_exc()

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
        from pathlib import Path
        import logging
        logger = logging.getLogger(__name__)

        logger.info("ステップ8のみの実行を開始（ステップ1〜7は一時停止）")
        
        # ステップ8: ConversationSegmentテーブルへの挿入
        from .openai_completion_step8 import step8_insert_conversation_segments
        step8_success = step8_insert_conversation_segments(meeting_id)
        
        if step8_success:
            logger.info("✅ ステップ8処理が完了しました")
        else:
            logger.error("❌ ステップ8処理が失敗しました")
            return False
        
        logger.info("✅ ステップ8の処理が完了しました")
        return True
        
    except Exception as e:
        logger.error(f"会話データの処理中にエラーが発生: meeting_id={meeting_id}, error={e}")
        logger.error(traceback.format_exc())
        return False

def load_transcript_segments(meeting_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """DBからtranscript_textを読み込み、セグメントリストに変換する

    Args:
        meeting_id (Optional[int]): 会議ID

    Returns:
        List[Dict[str, Any]]: セグメントリスト
    """
    logger.info(f"[DEBUG] loading segments from DB for meeting_id={meeting_id}")
    logger.info(f"[DEBUG] meeting_id type: {type(meeting_id)}")

    if meeting_id is None:
        logger.error("[DEBUG] meeting_id is None")
        return []

    if not AZURE_AVAILABLE:
        logger.error("[DEBUG] Azure modules not available")
        return []

    try:
        logger.info("[DEBUG] Attempting to get DB connection")
        conn = get_db_connection()
        if not conn:
            logger.error("[DEBUG] Failed to get DB connection")
            return []

        cursor = conn.cursor()

        # SQL実行前のデバッグログ
        logger.info(f"[DEBUG] Executing SQL query for meeting_id={meeting_id}")
        query = "SELECT transcript_text FROM dbo.Meetings WHERE meeting_id = ?"
        logger.info(f"[DEBUG] SQL Query: {query}")
        
        cursor.execute(query, (meeting_id,))
        row = cursor.fetchone()
        
        if row:
            logger.info(f"[DEBUG] Found transcript_text for meeting_id={meeting_id}")
            transcript_text = row[0]
            if transcript_text:
                logger.info(f"[DEBUG] transcript_text content (first 100 chars): {transcript_text[:100]}...")
                logger.info(f"[DEBUG] transcript_text length: {len(transcript_text)}")
            else:
                logger.warning("[DEBUG] transcript_text is empty")
                return []
        else:
            logger.warning(f"[DEBUG] No row found for meeting_id={meeting_id}")
            return []

        # transcript_textをセグメント化
        segments = []
        
        # 複数の正規表現パターンを試行
        patterns = [
            # パターン1: (SpeakerX)[発言](offset)
            r'\(Speaker(\d+)\)\[(.*?)\]\(([\d.]+)\)',
            # パターン2: (SpeakerX)[発言]
            r'\(Speaker(\d+)\)\[(.*?)\]',
            # パターン3: SpeakerX:発言
            r'Speaker(\d+):(.+?)(?=Speaker\d+:|$)',
            # パターン4: [SpeakerX]発言
            r'\[Speaker(\d+)\](.+?)(?=\[Speaker\d+\]|$)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, transcript_text, flags=re.DOTALL)
            if matches:
                logger.info(f"✅ meeting_id={meeting_id}: パターンマッチ成功")
                
                for match in matches:
                    if len(match) >= 2:  # 最低でもspeaker_idとtextは必要
                        speaker_id = int(match[0])
                        text = match[1].strip()
                        # offsetは3番目の要素がある場合のみ使用
                        offset = float(match[2]) if len(match) > 2 else 0.0
                        
                        if text:  # 空のテキストはスキップ
                            segments.append({
                                "speaker": speaker_id,
                                "text": text,
                                "offset": offset
                            })
                
                # マッチが見つかったらループを抜ける
                if segments:
                    break
        
        if segments:
            # ✅ デバッグログ追加：return直前のsegments確認
            logger.info(f"[DEBUG] meeting_id={meeting_id}: セグメント抽出完了")
            logger.info(f"[DEBUG] 抽出されたセグメント数: {len(segments)}")
            return segments
        else:
            # 最後の手段：行単位での分割を試みる
            lines = transcript_text.splitlines()
            current_speaker = None
            current_text = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 新しい話者の検出
                speaker_match = re.match(r'(?:Speaker|＜話者)(\d+)(?:＞|:|）|\])', line)
                if speaker_match:
                    # 前の話者のテキストがあれば保存
                    if current_speaker is not None and current_text:
                        segments.append({
                            "speaker": current_speaker,
                            "text": " ".join(current_text).strip(),
                            "offset": 0.0
                        })
                        current_text = []
                    
                    current_speaker = int(speaker_match.group(1))
                    # 話者ID以降のテキストを取得
                    text_part = re.sub(r'^(?:Speaker|＜話者)(\d+)(?:＞|:|）|\])\s*', '', line).strip()
                    if text_part:
                        current_text.append(text_part)
                elif current_speaker is not None:
                    # 既存の話者の発言の続き
                    current_text.append(line)
            
            # 最後の話者のテキストを保存
            if current_speaker is not None and current_text:
                segments.append({
                    "speaker": current_speaker,
                    "text": " ".join(current_text).strip(),
                    "offset": 0.0
                })
            
            # ✅ デバッグログ追加：行単位処理後のsegments確認
            logger.info(f"[DEBUG] meeting_id={meeting_id}: 行単位処理でセグメント抽出完了")
            logger.info(f"[DEBUG] 抽出されたセグメント数: {len(segments)}")
            return segments
            
        return []
            
    except Exception as e:
        logger.error(f"❌ meeting_id={meeting_id} のセグメント抽出中にエラー: {str(e)}")
        return []
    finally:
        try:
            if 'conn' in locals():
                conn.close()
        except Exception:
            pass

def get_db_connection():
    """
    Entra ID認証を使用してAzure SQL Databaseに接続する
    
    Returns:
        pyodbc.Connection: データベース接続オブジェクト
        
    Raises:
        Exception: 接続に失敗した場合
    """
    if not AZURE_AVAILABLE:
        logger.error("❌ Azure関連のモジュールが利用できません")
        raise Exception("Azure関連のモジュールが利用できません")
    
    try:
        logger.info("🔑 DefaultAzureCredentialを取得中...")
        credential = DefaultAzureCredential()
        
        logger.info("🎟 データベースアクセストークンを取得中...")
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
        
        logger.info("🔌 データベースに接続中...")
        logger.debug(f"接続文字列: {conn_str}")
        
        conn = pyodbc.connect(conn_str, attrs_before={1256: access_token})
        logger.info("✅ データベース接続成功")
        return conn
        
    except Exception as e:
        logger.error(f"❌ データベース接続エラー: {str(e)}")
        logger.error(traceback.format_exc())
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
    # meeting_idの型と値を確認するデバッグログ
    logger.debug(f"[DEBUG] save_processed_segments - meeting_id type: {type(meeting_id)} value: {meeting_id}")
    
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