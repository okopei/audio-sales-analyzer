import sys
from openai_processing.openai_completion_core import clean_and_complete_conversation, load_transcript_segments

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_conversation_processing.py <meeting_id>")
        sys.exit(1)
    
    meeting_id = int(sys.argv[1])
    print(f"会議ID {meeting_id} の処理を開始します...")

    # transcript_textをDBから取得し、Step1用に整形
    segments = load_transcript_segments(meeting_id)
    if not segments:
        print("transcript_textが取得できませんでした")
        sys.exit(1)

    print(f"取得したセグメント数: {len(segments)}")

    # ステップ1〜8の全処理を実行
    success = clean_and_complete_conversation(meeting_id)
    
    if success:
        print(f"✅ 会議ID {meeting_id} の処理が完了しました")
        print("📊 処理内容:")
        print("  - ステップ8: ConversationSegmentsテーブルへの挿入（テスト実行）")
        print("  - インプット: completion_result_step7.txt")
        print("  - ステップ1〜7: 一時停止中")
    else:
        print(f"❌ 会議ID {meeting_id} の処理が失敗しました")
        sys.exit(1) 