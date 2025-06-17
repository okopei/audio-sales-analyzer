#!/usr/bin/env python3
"""
会話処理のメインスクリプト
"""

import logging
import os
import sys
from typing import Optional
from openai_completion_core import clean_and_complete_conversation, load_transcript_segments, get_db_connection

# ロギング設定
def setup_logging():
    """ロギング設定を初期化する"""
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

logger = setup_logging()

def process_conversation(meeting_id: int) -> Optional[str]:
    """会話処理のメイン関数
    
    Args:
        meeting_id (int): 処理対象のmeeting_id
        
    Returns:
        Optional[str]: 処理結果のテキスト。エラー時はNone
    """
    try:
        logger.info(f"🚀 meeting_id={meeting_id} の会話処理を開始します")
        
        # DBからtranscript_textを取得してセグメント化
        logger.info("📥 DBからtranscript_textを取得中...")
        segments = load_transcript_segments(meeting_id)
        
        if not segments:
            logger.error(f"❌ meeting_id={meeting_id} のtranscript_textが取得できませんでした")
            return None
        
        logger.info(f"✅ {len(segments)} セグメントを取得しました")
        
        # 会話の整形・補完処理を実行
        logger.info("🔄 会話の整形・補完処理を開始します")
        result_text = clean_and_complete_conversation(segments)
        
        if result_text:
            logger.info(f"✅ 処理完了: {len(result_text.splitlines())}行のテキストを生成しました")
            return result_text
        else:
            logger.error("❌ 会話処理に失敗しました")
            return None
            
    except Exception as e:
        logger.error(f"❌ 会話処理でエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def save_result_to_db(meeting_id: int, result_text: str) -> bool:
    """処理結果をDBのConversationSegmentテーブルに保存する
    
    Args:
        meeting_id (int): meeting_id
        result_text (str): 処理結果のテキスト
        
    Returns:
        bool: 保存が成功したかどうか
    """
    try:
        logger.info("💾 処理結果をDBに保存中...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 既存のConversationSegmentレコードを削除
        cursor.execute("DELETE FROM dbo.ConversationSegment WHERE meeting_id = ?", (meeting_id,))
        logger.info(f"🗑️ meeting_id={meeting_id} の既存ConversationSegmentレコードを削除しました")
        
        # 新しいレコードを挿入
        cursor.execute(
            "INSERT INTO dbo.ConversationSegment (meeting_id, segment_text, created_at) VALUES (?, ?, GETDATE())",
            (meeting_id, result_text)
        )
        
        conn.commit()
        logger.info(f"✅ meeting_id={meeting_id} の処理結果をDBに保存しました")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ DB保存に失敗しました: {str(e)}")
        return False
    finally:
        try:
            if 'conn' in locals():
                conn.close()
        except Exception:
            pass

def main():
    """メイン関数"""
    if len(sys.argv) != 2:
        logger.error("❌ 使用方法: python run_conversation_processing.py <meeting_id>")
        sys.exit(1)
    
    try:
        meeting_id = int(sys.argv[1])
    except ValueError:
        logger.error("❌ meeting_idは整数で指定してください")
        sys.exit(1)
    
    logger.info(f"🎯 meeting_id={meeting_id} の処理を開始します")
    
    # 会話処理を実行
    result_text = process_conversation(meeting_id)
    
    if result_text:
        # 結果をDBに保存
        if save_result_to_db(meeting_id, result_text):
            logger.info("🎉 処理が正常に完了しました")
            sys.exit(0)
        else:
            logger.error("❌ DB保存に失敗しました")
            sys.exit(1)
    else:
        logger.error("❌ 会話処理に失敗しました")
        sys.exit(1)

if __name__ == "__main__":
    main() 