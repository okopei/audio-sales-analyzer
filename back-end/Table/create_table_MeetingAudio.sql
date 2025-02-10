CREATE TABLE MeetingAudio (
    audio_id INT PRIMARY KEY IDENTITY(1,1),
    blob_url NVARCHAR(500) NOT NULL,        -- Azure Blob StorageのURL
    blob_container NVARCHAR(100) NOT NULL,   -- コンテナ名
    blob_path NVARCHAR(500) NOT NULL,        -- Blob内のパス
    original_file_name NVARCHAR(200) NOT NULL,
    content_type NVARCHAR(100) NOT NULL,     -- audio/mp3
    file_size BIGINT NOT NULL,              -- ファイルサイズ（バイト）
    duration INT,                           -- 音声の長さ（秒）
    llm_summary NVARCHAR(MAX),              -- LLMによる音声の要約内容
    user_id INT NOT NULL,
    inserted_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    updated_datetime DATETIME NOT NULL DEFAULT GETDATE(),
    
    -- 外部キー制約
    CONSTRAINT FK_MeetingAudio_Users 
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- インデックス
CREATE INDEX idx_meeting_audio_user ON MeetingAudio(user_id);