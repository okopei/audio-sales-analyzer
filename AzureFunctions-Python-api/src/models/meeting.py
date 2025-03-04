from dataclasses import dataclass
from typing import Optional, Union
from datetime import datetime

@dataclass
class Meeting:
    """
    会議モデル - データベースのMeetingsテーブルに対応
    """
    meeting_id: Optional[str] = None
    user_id: str = ""
    user_name: Optional[str] = None  # 結合クエリ用
    title: str = ""
    client_contact_name: Optional[str] = None  # 顧客名フィールドを追加
    client_company_name: Optional[str] = None  # 企業名フィールドを追加
    meeting_datetime: Union[datetime, str, None] = None
    duration_seconds: int = 0
    status: str = "pending"  # 'pending', 'processing', 'completed', 'error'
    transcript_text: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    error_message: Optional[str] = None
    inserted_datetime: Optional[datetime] = None
    updated_datetime: Optional[datetime] = None

    def to_dict(self):
        """
        会議オブジェクトを辞書に変換
        """
        result = {
            "user_id": self.user_id,
            "title": self.title,
            "status": self.status,
            "duration_seconds": self.duration_seconds
        }
        
        # オプションフィールドを追加
        if self.meeting_id:
            result["meeting_id"] = self.meeting_id
            
        if self.user_name:
            result["user_name"] = self.user_name
            
        # 顧客名フィールドを追加
        if self.client_contact_name:
            result["client_contact_name"] = self.client_contact_name
            
        # 企業名フィールドを追加
        if self.client_company_name:
            result["client_company_name"] = self.client_company_name
            
        if self.meeting_datetime:
            if isinstance(self.meeting_datetime, datetime):
                result["meeting_datetime"] = self.meeting_datetime.isoformat()
            else:
                result["meeting_datetime"] = self.meeting_datetime
                
        if self.transcript_text:
            result["transcript_text"] = self.transcript_text
            
        if self.file_name:
            result["file_name"] = self.file_name
            
        if self.file_size is not None:
            result["file_size"] = self.file_size
            
        if self.error_message:
            result["error_message"] = self.error_message
            
        if self.inserted_datetime:
            if isinstance(self.inserted_datetime, datetime):
                result["inserted_datetime"] = self.inserted_datetime.strftime('%Y-%m-%d %H:%M:%S')
            else:
                result["inserted_datetime"] = self.inserted_datetime
            
        if self.updated_datetime:
            if isinstance(self.updated_datetime, datetime):
                result["updated_datetime"] = self.updated_datetime.strftime('%Y-%m-%d %H:%M:%S')
            else:
                result["updated_datetime"] = self.updated_datetime
            
        return result
    
    def to_sql_row(self):
        """
        SQLバインディング用の辞書を返す
        """
        return self.to_dict()
    
    @classmethod
    def from_dict(cls, data):
        """
        辞書から会議オブジェクトを作成
        """
        meeting = cls()
        
        for key, value in data.items():
            if hasattr(meeting, key):
                # 日付文字列をdatetimeオブジェクトに変換
                if key == 'meeting_datetime' and value and isinstance(value, str):
                    try:
                        # ISO形式の場合
                        setattr(meeting, key, datetime.fromisoformat(value.replace('Z', '+00:00')))
                    except ValueError:
                        try:
                            # SQL Server形式の場合
                            setattr(meeting, key, datetime.strptime(value, '%Y-%m-%d %H:%M:%S'))
                        except ValueError:
                            # 日付形式が異なる場合はそのまま設定
                            setattr(meeting, key, value)
                elif key.endswith('_datetime') and value and isinstance(value, str):
                    try:
                        setattr(meeting, key, datetime.strptime(value, '%Y-%m-%d %H:%M:%S'))
                    except ValueError:
                        # 日付形式が異なる場合はそのまま設定
                        setattr(meeting, key, value)
                else:
                    setattr(meeting, key, value)
                    
        return meeting 