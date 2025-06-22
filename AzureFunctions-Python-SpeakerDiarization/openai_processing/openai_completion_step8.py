import re
import logging
import traceback
from typing import List, Dict, Any
from pathlib import Path
import os

logger = logging.getLogger(__name__)

# スクリプトの場所を基準としたベースディレクトリを設定
BASE_DIR = Path(__file__).resolve().parent

def get_db_connection():
    """
    Entra ID認証を使用してAzure SQL Databaseに接続する
    
    Returns:
        pyodbc.Connection: データベース接続オブジェクト
        
    Raises:
        Exception: 接続に失敗した場合
    """
    try:
        import pyodbc
        import struct
        from azure.identity import DefaultAzureCredential
        
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

        logger.info("Connecting to database with ODBC Driver 17 for SQL Server")
        return pyodbc.connect(conn_str, attrs_before={1256: access_token})
    except Exception as e:
        logger.error(f"❌ DB接続失敗: {str(e)}")
        raise

def execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    """
    SQLクエリを実行し、結果を返します
    
    Args:
        query (str): 実行するSQLクエリ
        params (tuple): クエリパラメータ
        
    Returns:
        List[Dict[str, Any]]: クエリ結果のリスト
    """
    conn = None
    try:
        conn = get_db_connection()
        logger.info(f"クエリを実行: {query[:100]}...")
        
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # 結果セットの取得（SELECTまたはOUTPUT句を含むクエリの場合）
        if cursor.description:
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]

            # datetime → 文字列化
            for row in results:
                for key, value in row.items():
                    if hasattr(value, 'isoformat'):
                        row[key] = value.isoformat()

            conn.commit()
            return results
        else:
            conn.commit()
            logger.info("コミット完了")
            return []
            
    except Exception as e:
        if conn:
            try:
                conn.rollback()
                logger.warning("ロールバックを実行しました")
            except Exception as rollback_error:
                logger.warning(f"ロールバックに失敗: {str(rollback_error)}")
        
        logger.error(f"クエリ実行エラー: {str(e)}")
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"データベース接続のクローズに失敗: {str(e)}")

def insert_conversation_segment(meeting_id: int, speaker_id: int, text: str, 
                               start_time: float = None, duration: int = 0, 
                               end_time: float = None, user_id: int = None) -> None:
    """
    ConversationSegmentテーブルに1件のセグメントを挿入する
    
    Args:
        meeting_id (int): 会議ID
        speaker_id (int): 話者ID（0はシステム話者）
        text (str): 発話内容
        start_time (float): 開始時間
        duration (int): 継続時間
        end_time (float): 終了時間
        user_id (int): ユーザーID
    """
    try:
        # user_idが指定されていない場合は、meeting_idから取得
        if user_id is None:
            result = execute_query(
                "SELECT user_id FROM dbo.Meetings WHERE meeting_id = ?",
                (meeting_id,)
            )
            if result:
                user_id = result[0]["user_id"]
            else:
                logger.error(f"meeting_id {meeting_id} に対応するuser_idが見つかりません")
                return
        
        # ファイル情報を取得
        result = execute_query(
            "SELECT file_name, file_path, file_size FROM dbo.Meetings WHERE meeting_id = ?",
            (meeting_id,)
        )
        file_name = result[0]["file_name"] if result else ""
        file_path = result[0]["file_path"] if result else ""
        file_size = result[0]["file_size"] if result else 0
        
        # ConversationSegmentに挿入
        insert_sql = """
            INSERT INTO dbo.ConversationSegments (
                user_id, speaker_id, meeting_id, content,
                file_name, file_path, file_size, duration_seconds,
                status, inserted_datetime, updated_datetime,
                start_time, end_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), ?, ?)
        """
        
        execute_query(insert_sql, (
            user_id,
            speaker_id,
            meeting_id,
            text,
            file_name,
            file_path,
            file_size,
            duration,
            "completed",
            start_time,
            end_time
        ))
        
        logger.debug(f"✅ ConversationSegment挿入完了: speaker_id={speaker_id}, text='{text[:50]}...'")
        
    except Exception as e:
        logger.error(f"ConversationSegment挿入エラー: {str(e)}")
        raise

def ensure_system_speaker_exists(meeting_id: int, user_id: int) -> int:
    """
    システム話者（speaker_id=0）が存在することを確認し、存在しない場合は作成する
    
    Args:
        meeting_id (int): 会議ID
        user_id (int): ユーザーID
        
    Returns:
        int: システム話者のspeaker_id
    """
    try:
        # 既存のシステム話者を確認
        result = execute_query(
            "SELECT speaker_id FROM dbo.Speakers WHERE meeting_id = ? AND speaker_name = ? AND deleted_datetime IS NULL",
            (meeting_id, "System")
        )
        
        if result:
            # 既存のシステム話者のspeaker_idを使用
            speaker_id = result[0]["speaker_id"]
            logger.info(f"既存のシステム話者を使用: speaker_id={speaker_id}")
            return speaker_id
        else:
            # システム話者を新規登録
            insert_query = """
                INSERT INTO dbo.Speakers (
                    speaker_name, user_id, meeting_id, 
                    inserted_datetime, updated_datetime
                )
                OUTPUT INSERTED.speaker_id
                VALUES (?, ?, ?, GETDATE(), GETDATE())
            """
            
            insert_result = execute_query(insert_query, ("System", user_id, meeting_id))
            
            if not insert_result:
                raise Exception("System Speaker INSERT failed: No OUTPUT returned")
                
            speaker_id = insert_result[0]["speaker_id"]
            logger.info(f"システム話者を新規登録: speaker_id={speaker_id}")
            return speaker_id
            
    except Exception as e:
        logger.error(f"システム話者の確認・作成に失敗: {str(e)}")
        raise

def ensure_speaker_exists(meeting_id: int, user_id: int, speaker_number: int) -> int:
    """
    指定された話者が存在することを確認し、存在しない場合は作成する
    
    Args:
        meeting_id (int): 会議ID
        user_id (int): ユーザーID
        speaker_number (int): 話者番号
        
    Returns:
        int: 話者のspeaker_id
    """
    try:
        speaker_name = f"Speaker{speaker_number}"
        
        # 既存の話者を確認
        result = execute_query(
            "SELECT speaker_id FROM dbo.Speakers WHERE meeting_id = ? AND speaker_name = ? AND deleted_datetime IS NULL",
            (meeting_id, speaker_name)
        )
        
        if result:
            # 既存の話者のspeaker_idを使用
            speaker_id = result[0]["speaker_id"]
            logger.debug(f"既存の話者を使用: {speaker_name} (speaker_id={speaker_id})")
            return speaker_id
        else:
            # 新規話者として登録
            insert_query = """
                INSERT INTO dbo.Speakers (
                    speaker_name, user_id, meeting_id, 
                    inserted_datetime, updated_datetime
                )
                OUTPUT INSERTED.speaker_id
                VALUES (?, ?, ?, GETDATE(), GETDATE())
            """
            
            insert_result = execute_query(insert_query, (speaker_name, user_id, meeting_id))
            
            if not insert_result:
                raise Exception(f"Speaker INSERT failed: No OUTPUT returned for {speaker_name}")
                
            speaker_id = insert_result[0]["speaker_id"]
            logger.info(f"新規話者を登録: {speaker_name} (speaker_id={speaker_id})")
            return speaker_id
            
    except Exception as e:
        logger.error(f"話者の確認・作成に失敗: {str(e)}")
        raise

def insert_conversation_segments_from_file(meeting_id: int, file_path: str = None) -> None:
    """
    completion_result_step7.txt を読み込み、ConversationSegment テーブルに発話と要約を挿入する

    Args:
        meeting_id (int): 対象の会議ID
        file_path (str): 整形済み会話の保存ファイル（デフォルトはステップ7出力）
    """
    try:
        logger.info(f"ステップ8: ConversationSegment挿入を開始 (meeting_id: {meeting_id})")
        
        # ファイルパスの設定
        if file_path is None:
            file_path = BASE_DIR / "outputs" / "completion_result_step7.txt"
        
        logger.info(f"読み込みファイル: {file_path}")
        
        # ファイルの存在確認
        if not Path(file_path).exists():
            logger.error(f"ファイルが見つかりません: {file_path}")
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
        
        # user_idを取得
        result = execute_query(
            "SELECT user_id FROM dbo.Meetings WHERE meeting_id = ?",
            (meeting_id,)
        )
        if not result:
            logger.error(f"meeting_id {meeting_id} が見つかりません")
            raise ValueError(f"meeting_id {meeting_id} が見つかりません")
        
        user_id = result[0]["user_id"]
        logger.info(f"user_id: {user_id}")
        
        # 既存のConversationSegmentを削除
        logger.info(f"既存のConversationSegmentを削除: meeting_id={meeting_id}")
        execute_query(
            "DELETE FROM dbo.ConversationSegments WHERE meeting_id = ?",
            (meeting_id,)
        )
        
        # ファイルを1回だけ読み込み
        logger.info("ファイルを読み込み中...")
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        logger.info(f"ファイル読み込み完了: {len(lines)}行")
        
        # 処理対象の行をフィルタリング
        valid_lines = []
        for i, line in enumerate(lines):
            line = line.strip()
            if line:  # 空行でない場合のみ追加
                valid_lines.append((i, line))
        
        logger.info(f"処理対象行数: {len(valid_lines)}行")
        
        inserted_count = 0
        
        # 1回のループですべての行を処理
        for line_index, line in valid_lines:
            try:
                if line.startswith("Summary:"):
                    # 要約行（speaker_id = 0, user_id = 0）
                    text = line.replace("Summary:", "").strip()
                    
                    insert_conversation_segment(
                        meeting_id=meeting_id,
                        speaker_id=0,  # 明示的に0に固定
                        text=text,
                        start_time=line_index,  # 順序を保持するため行番号を使用
                        duration=0,
                        end_time=None,
                        user_id=0  # 明示的に0に固定
                    )
                    inserted_count += 1
                    logger.debug(f"✅ Summary行 {line_index+1} を挿入: '{text}' (speaker_id=0, user_id=0)")
                    
                elif line.startswith("Speaker"):
                    # Speaker行の解析
                    match = re.match(r"Speaker(\d+):\s*(.*)\(([\d.]+)\)", line)
                    if match:
                        speaker_number = int(match.group(1))
                        text = match.group(2).strip()
                        start_time = float(match.group(3))
                        
                        # 話者の存在確認・作成
                        speaker_id = ensure_speaker_exists(meeting_id, user_id, speaker_number)
                        
                        insert_conversation_segment(
                            meeting_id=meeting_id,
                            speaker_id=speaker_id,
                            text=text,
                            start_time=start_time,
                            duration=0,
                            end_time=None,
                            user_id=user_id
                        )
                        inserted_count += 1
                        logger.debug(f"✅ Speaker行 {line_index+1} を挿入: Speaker{speaker_number}, text='{text[:50]}...'")
                    else:
                        logger.warning(f"⚠️ 行 {line_index+1} が解析不可能な形式です: {line}")
                else:
                    logger.warning(f"⚠️ 行 {line_index+1} が想定外の形式です: {line}")
                    
            except Exception as e:
                logger.error(f"行 {line_index+1} の処理中にエラーが発生: {str(e)}")
                continue
        
        # 処理完了ログ
        logger.info(f"✅ ステップ8完了: {inserted_count}件のConversationSegmentを挿入しました")
        logger.info("ステップ8の処理が正常に終了しました")
        
    except Exception as e:
        logger.error(f"ステップ8でエラーが発生: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def step8_insert_conversation_segments(meeting_id: int) -> bool:
    """
    ステップ8: ConversationSegmentテーブルへの挿入
    
    Args:
        meeting_id (int): 対象の会議ID
        
    Returns:
        bool: 処理が成功したかどうか
    """
    try:
        insert_conversation_segments_from_file(meeting_id)
        return True
    except Exception as e:
        logger.error(f"ステップ8でエラーが発生: {str(e)}")
        return False 