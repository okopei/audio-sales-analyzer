from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Comment:
    """コメントデータモデル"""
    comment_id: Optional[int] = None
    segment_id: int = 0
    meeting_id: int = 0
    user_id: int = 0
    content: str = ""
    inserted_datetime: Optional[datetime] = None
    updated_datetime: Optional[datetime] = None
    deleted_datetime: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "comment_id": self.comment_id,
            "segment_id": self.segment_id,
            "meeting_id": self.meeting_id,
            "user_id": self.user_id,
            "content": self.content,
            "inserted_datetime": self.inserted_datetime.isoformat() if self.inserted_datetime else None,
            "updated_datetime": self.updated_datetime.isoformat() if self.updated_datetime else None
        }


@dataclass
class CommentRead:
    """コメント既読状態データモデル"""
    comment_id: int = 0
    reader_id: int = 0  # 既読したユーザーID
    read_datetime: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "comment_id": self.comment_id,
            "reader_id": self.reader_id,
            "read_datetime": self.read_datetime.isoformat() if self.read_datetime else None
        } 