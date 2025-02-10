CREATE TABLE Users (
    -- 基本情報
    user_id INT PRIMARY KEY IDENTITY(1,1),
    user_name VARCHAR(50) NOT NULL,
    email VARCHAR(256) NOT NULL UNIQUE,
    password_hash NVARCHAR(128) NOT NULL,  -- ハッシュ化されたパスワード
    salt NVARCHAR(36) NOT NULL,            -- パスワードソルト
    
    -- アカウント状態
    is_active BIT DEFAULT 1,
    account_status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE, LOCKED, SUSPENDED など
    last_login_datetime DATETIME,
    
    -- 監査情報
    inserted_datetime DATETIME DEFAULT GETDATE(),
    updated_datetime DATETIME DEFAULT GETDATE(),
    deleted_datetime DATETIME NULL,        -- 論理削除用
    
    -- アカウント管理
    password_reset_token VARCHAR(100) NULL,
    password_reset_expires DATETIME NULL,
    login_attempt_count INT DEFAULT 0
)
