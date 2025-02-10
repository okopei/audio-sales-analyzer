CREATE TABLE Meetings (
    meeting_id INT PRIMARY KEY IDENTITY(1,1),
    title NVARCHAR(200) NOT NULL,
    meeting_datetime DATETIME NOT NULL,
    user_id INT NOT NULL,
    audio_id INT NULL,          -- NULLを許可
    memo_id INT NULL,           -- NULLを許可
    rate DECIMAL(3,2),
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    
    -- 少なくともaudioかmemoのどちらかが必要という制約
    CONSTRAINT CHK_Meetings_RequiredFields 
        CHECK (audio_id IS NOT NULL OR memo_id IS NOT NULL),
    
    -- 外部キー制約
    CONSTRAINT FK_Meetings_Users 
        FOREIGN KEY (user_id) REFERENCES Users(user_id),
    CONSTRAINT FK_Meetings_Audio
        FOREIGN KEY (audio_id) REFERENCES Audio(audio_id),
    CONSTRAINT FK_Meetings_MeetingMemo 
        FOREIGN KEY (memo_id) REFERENCES MeetingMemo(memo_id)
);

-- インデックス
CREATE INDEX idx_meetings_audio ON Meetings(audio_id);
CREATE INDEX idx_meetings_memo ON Meetings(memo_id);
CREATE INDEX idx_meetings_user ON Meetings(user_id);