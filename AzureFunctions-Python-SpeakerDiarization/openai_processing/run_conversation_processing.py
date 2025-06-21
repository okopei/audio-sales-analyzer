import sys
from openai_processing.openai_completion_core import clean_and_complete_conversation, load_transcript_segments

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_conversation_processing.py <meeting_id>")
        sys.exit(1)
    
    meeting_id = int(sys.argv[1])

    # transcript_textをDBから取得し、Step1用に整形
    segments = load_transcript_segments(meeting_id)
    if not segments:
        print("transcript_textが取得できませんでした")
        sys.exit(1)

    transcript_text = "\n".join(
        f"Speaker{seg['speaker']}: {seg['text']}({seg.get('offset', 0.0)})"
        for seg in segments if seg.get('text', '').strip()
    )

    clean_and_complete_conversation(meeting_id, transcript_text) 