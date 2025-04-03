from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class ConversationSegment:
    """会話セグメントデータモデル"""
    segment_id: Optional[int] = None
    user_id: int = 0
    speaker_id: int = 0
    meeting_id: int = 0
    content: str = ""
    file_name: str = ""
    file_path: str = ""
    file_size: int = 0
    duration_seconds: int = 0
    status: str = "processing"  # waiting, processing, completed, error
    inserted_datetime: Optional[datetime] = None
    updated_datetime: Optional[datetime] = None
    deleted_datetime: Optional[datetime] = None
    
    # 表示用の拡張データ
    speaker_name: Optional[str] = None
    speaker_role: Optional[str] = None
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "segment_id": self.segment_id,
            "user_id": self.user_id,
            "speaker_id": self.speaker_id,
            "meeting_id": self.meeting_id,
            "content": self.content,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "inserted_datetime": self.inserted_datetime.isoformat() if self.inserted_datetime else None,
            "updated_datetime": self.updated_datetime.isoformat() if self.updated_datetime else None,
            "speaker_name": self.speaker_name,
            "speaker_role": self.speaker_role
        } 