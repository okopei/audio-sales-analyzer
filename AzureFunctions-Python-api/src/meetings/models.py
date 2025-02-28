from datetime import datetime

class Meeting:
    """会議データモデル"""
    def __init__(self, 
                 user_id, 
                 title, 
                 meeting_datetime, 
                 file_name="placeholder.mp3",
                 file_path="/placeholder/path",
                 file_size=0,
                 duration_seconds=3600,
                 status="pending"):
        self.user_id = user_id
        self.title = title
        self.file_name = file_name
        self.file_path = file_path
        self.file_size = file_size
        self.duration_seconds = duration_seconds
        self.status = status
        self.meeting_datetime = meeting_datetime
        self.start_datetime = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        self.end_datetime = None
        self.transcript_text = None
        self.error_message = None
        self.inserted_datetime = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        self.updated_datetime = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        self.deleted_datetime = None
    
    def to_dict(self):
        """辞書に変換"""
        return {
            "user_id": self.user_id,
            "title": self.title,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "meeting_datetime": self.meeting_datetime,
            "start_datetime": self.start_datetime,
            "end_datetime": self.end_datetime,
            "transcript_text": self.transcript_text,
            "error_message": self.error_message,
            "inserted_datetime": self.inserted_datetime,
            "updated_datetime": self.updated_datetime,
            "deleted_datetime": self.deleted_datetime
        }