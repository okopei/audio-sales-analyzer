#!/usr/bin/env python3
"""
OpenAI処理パイプラインのテストスクリプト
FunctionAppを通さずに直接OpenAI処理をテストできます
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import openai_completion_core
from openai_completion_core import get_db_connection

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print('AZURE_AVAILABLE:', openai_completion_core.AZURE_AVAILABLE)

def main():
    parser = argparse.ArgumentParser(description='OpenAI処理パイプラインのテスト')
    parser.add_argument('--meeting-id', type=int, help='テスト対象のmeeting_id')
    parser.add_argument('--text', type=str, help='直接テストするテキスト（meeting_idと併用不可）')
    parser.add_argument('--output', type=str, default='test_output.txt', help='出力ファイル名')
    
    args = parser.parse_args()
    
    if not args.meeting_id and not args.text:
        logger.error("❌ --meeting-id または --text のいずれかを指定してください")
        return 1
    
    if args.meeting_id and args.text:
        logger.error("❌ --meeting-id と --text は同時に指定できません")
        return 1
    
    try:
        # openai_completion_coreをインポート
        # sys.path.append(str(Path(__file__).parent))
        from openai_completion_core import clean_and_complete_conversation, load_transcript_segments
        
        if args.meeting_id:
            logger.info(f"🔍 meeting_id: {args.meeting_id} のtranscript_textを取得してOpenAI処理を実行します")
            
            # DBからtranscript_textを取得
            segments = load_transcript_segments(args.meeting_id)
            
            if not segments:
                logger.error("❌ transcript_textの取得に失敗しました")
                logger.error("💡 確認事項:")
                logger.error("   - meeting_idが正しいか")
                logger.error("   - DBにtranscript_textが保存されているか")
                logger.error("   - Azure関連のモジュールが利用できるか")
                return 1
            
            logger.info(f"✅ {len(segments)} セグメントを取得しました")
            print('segments:', segments)
        
        else:
            logger.info("🔍 指定されたテキストでOpenAI処理を実行します")
            
            # テキストをセグメント形式に変換
            segments = []
            for line in args.text.splitlines():
                if line.strip():
                    import re
                    m = re.match(r"Speaker(\d+):(.+)", line)
                    if m:
                        segments.append({
                            "speaker": int(m.group(1)),
                            "text": m.group(2).strip(),
                            "duration": 0,
                            "offset": 0
                        })
            
            if not segments:
                logger.error("❌ テキストのセグメント化に失敗しました")
                return 1
            
            logger.info(f"✅ {len(segments)} セグメントに変換しました")
        
        # OpenAI処理を実行
        logger.info("🚀 OpenAI処理を開始します")
        processed_text = clean_and_complete_conversation(segments)
        
        if processed_text:
            logger.info(f"✅ OpenAI処理が完了しました。文字数: {len(processed_text)}")
            
            # 結果をファイルに保存
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(processed_text)
            
            logger.info(f"✅ 結果を {args.output} に保存しました")
            
            # DBに保存する処理（ConversationSegment）
            if args.meeting_id:
                conn = get_db_connection()
                cursor = conn.cursor()

                inserted = 0
                for line in processed_text.splitlines():
                    import re
                    match = re.match(r"Speaker(\d+):(.+)", line)
                    if match:
                        speaker_id = int(match.group(1))
                        text = match.group(2).strip()
                        cursor.execute(
                            "INSERT INTO dbo.ConversationSegment (meeting_id, speaker_id, text) VALUES (?, ?, ?)",
                            (args.meeting_id, speaker_id, text)
                        )
                        inserted += 1

                conn.commit()
                conn.close()
                logger.info(f"✅ ConversationSegment に {inserted} 件のレコードを挿入しました")
            else:
                logger.warning("⚠️ meeting_id が指定されていないため、ConversationSegment への挿入はスキップされました")
            
            # 結果の一部を表示
            print("\n" + "="*50)
            print("OpenAI処理結果（最初の10行）:")
            print("="*50)
            lines = processed_text.splitlines()
            for i, line in enumerate(lines[:10]):
                print(f"{i+1:2d}: {line}")
            if len(lines) > 10:
                print(f"... 他 {len(lines)-10} 行")
            print("="*50)
            
        else:
            logger.error("❌ OpenAI処理が失敗しました")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main()) 