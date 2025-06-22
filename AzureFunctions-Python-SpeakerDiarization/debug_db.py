#!/usr/bin/env python3
"""
DB接続とデータ確認用のデバッグスクリプト
"""

from openai_completion_core import get_db_connection, load_transcript_segments

def main():
    print("🔍 DB接続テスト開始...")
    
    try:
        # DB接続テスト
        conn = get_db_connection()
        print("✅ DB接続成功")
        
        cursor = conn.cursor()
        
        # meeting_id=88の存在確認
        cursor.execute("SELECT meeting_id, LEN(transcript_text) as text_length FROM dbo.Meetings WHERE meeting_id = 88")
        row = cursor.fetchone()
        
        if row:
            print(f"✅ meeting_id=88 が見つかりました: text_length={row[1]}")
            
            # transcript_textの内容確認
            cursor.execute("SELECT transcript_text FROM dbo.Meetings WHERE meeting_id = 88")
            text_row = cursor.fetchone()
            
            if text_row and text_row[0]:
                transcript_text = text_row[0]
                print(f"✅ transcript_textが存在します: {len(transcript_text)}文字")
                print(f"📝 先頭200文字: {transcript_text[:200]}...")
                
                # セグメント化テスト
                print("\n🔍 セグメント化テスト...")
                segments = load_transcript_segments(88)
                print(f"📊 セグメント数: {len(segments)}")
                
                if segments:
                    print("✅ セグメント化成功")
                    for i, seg in enumerate(segments[:3]):
                        print(f"  セグメント{i+1}: Speaker{seg['speaker']}: {seg['text'][:50]}...")
                else:
                    print("❌ セグメント化失敗")
            else:
                print("❌ transcript_textが空またはNULLです")
        else:
            print("❌ meeting_id=88 が見つかりません")
            
            # 利用可能なmeeting_idを確認
            cursor.execute("SELECT TOP 5 meeting_id, LEN(transcript_text) as text_length FROM dbo.Meetings WHERE transcript_text IS NOT NULL ORDER BY meeting_id")
            rows = cursor.fetchall()
            print(f"📋 利用可能なmeeting_id (上位5件): {[row[0] for row in rows]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 