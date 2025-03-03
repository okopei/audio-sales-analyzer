from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class User:
    """
    ユーザーモデル - データベースのUsersテーブルに対応
    """
    user_id: Optional[str] = None
    user_name: str = ""
    email: str = ""
    password_hash: str = ""
    salt: str = ""
    role: str = "member"  # 'member' または 'manager'
    manager_name: Optional[str] = None
    is_active: bool = True
    account_status: str = "active"  # 'active', 'locked', 'inactive'
    inserted_datetime: Optional[datetime] = None
    updated_datetime: Optional[datetime] = None
    login_attempt_count: int = 0
    last_login_datetime: Optional[datetime] = None

    def to_dict(self):
        """
        ユーザーオブジェクトを辞書に変換
        """
        result = {
            "user_name": self.user_name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "account_status": self.account_status,
            "login_attempt_count": self.login_attempt_count
        }
        
        # オプションフィールドを追加
        if self.user_id:
            result["user_id"] = self.user_id
        
        if self.manager_name:
            result["manager_name"] = self.manager_name
            
        if self.inserted_datetime:
            result["inserted_datetime"] = self.inserted_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
        if self.updated_datetime:
            result["updated_datetime"] = self.updated_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
        if self.last_login_datetime:
            result["last_login_datetime"] = self.last_login_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
        return result
    
    def to_sql_row(self):
        """
        SQLバインディング用の辞書を返す
        """
        result = self.to_dict()
        
        # パスワード関連の情報を追加
        result["password_hash"] = self.password_hash
        result["salt"] = self.salt
        
        return result
    
    @classmethod
    def from_dict(cls, data):
        """
        辞書からユーザーオブジェクトを作成
        """
        user = cls()
        
        for key, value in data.items():
            if hasattr(user, key):
                # 日付文字列をdatetimeオブジェクトに変換
                if key.endswith('_datetime') and value and isinstance(value, str):
                    try:
                        setattr(user, key, datetime.strptime(value, '%Y-%m-%d %H:%M:%S'))
                    except ValueError:
                        # 日付形式が異なる場合はそのまま設定
                        setattr(user, key, value)
                else:
                    setattr(user, key, value)
                    
        return user 