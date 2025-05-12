CREATE OR ALTER PROCEDURE [dbo].[sp_ExtractSpeakersAndSegmentsFromTranscript]
    @meeting_id INT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @ErrorMessage NVARCHAR(4000);
    DECLARE @ErrorSeverity INT;
    DECLARE @ErrorState INT;
    
    -- トランザクション開始
    BEGIN TRANSACTION;
    
    BEGIN TRY
        -- 処理対象の会議データを取得
        DECLARE @transcript_text NVARCHAR(MAX);
        DECLARE @user_id INT;
        DECLARE @current_status NVARCHAR(50);
        DECLARE @file_name NVARCHAR(200);
        DECLARE @file_path NVARCHAR(1000);
        DECLARE @file_size BIGINT;
        DECLARE @duration_seconds INT;
        
        -- 会議データの存在確認と取得
        IF NOT EXISTS (SELECT 1 FROM dbo.Meetings WHERE meeting_id = @meeting_id)
        BEGIN
            RAISERROR('指定された会議IDが存在しません: %d', 16, 1, @meeting_id);
            RETURN;
        END;
        
        SELECT 
            @transcript_text = transcript_text,
            @user_id = user_id,
            @current_status = status,
            @file_name = file_name,
            @file_path = file_path,
            @file_size = file_size,
            @duration_seconds = duration_seconds
        FROM 
            dbo.Meetings
        WHERE 
            meeting_id = @meeting_id;
            
        -- STEP1: transcript_text 読み込み完了をログ
        INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
        VALUES ('INFO', 'Meetings', @meeting_id, GETDATE(), 'STEP1: transcript_text 読み込み完了');
            
        -- transcript_textが空の場合は処理をスキップ
        IF @transcript_text IS NULL OR LEN(@transcript_text) = 0
        BEGIN
            INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
            VALUES ('WARNING', 'Meetings', @meeting_id, GETDATE(), '文字起こしテキストが空のため、話者抽出をスキップします');
            COMMIT TRANSACTION;
            RETURN;
        END;
        
        -- 一時テーブルを作成して話者を格納
        CREATE TABLE #TempSpeakers (
            speaker_name NVARCHAR(50)
        );
        
        -- 一時テーブルを作成して話者IDを格納
        CREATE TABLE #TempSpeakersWithIds (
            speaker_id INT,
            speaker_name NVARCHAR(50)
        );
        
        -- 話者抽出処理
        DECLARE @pos INT = 1;
        DECLARE @match_start INT;
        DECLARE @match_end INT;
        DECLARE @speaker_name NVARCHAR(50);
        DECLARE @loop_count INT = 0;
        
        WHILE @pos <= LEN(@transcript_text) AND @loop_count < 10000
        BEGIN
            SET @loop_count += 1;
            
            SET @match_start = CHARINDEX('(', @transcript_text, @pos);
            IF @match_start = 0 BREAK;
            
            SET @match_end = CHARINDEX(')', @transcript_text, @match_start);
            IF @match_end = 0 BREAK;
            
            SET @speaker_name = SUBSTRING(@transcript_text, @match_start + 1, @match_end - @match_start - 1);
            
            IF NOT EXISTS (SELECT 1 FROM #TempSpeakers WHERE speaker_name = @speaker_name)
            BEGIN
                INSERT INTO #TempSpeakers (speaker_name)
                VALUES (@speaker_name);
            END;
            
            SET @pos = @match_end + 1;
        END;
        
        -- ループ上限チェック
        IF @loop_count >= 10000
        BEGIN
            RAISERROR('話者抽出のループ上限（10000）に達しました。文字起こしテキストの形式を確認してください。', 16, 1);
            RETURN;
        END;
        
        -- STEP2: 話者抽出完了をログ
        INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
        VALUES ('INFO', 'Speakers', @meeting_id, GETDATE(), 'STEP2: 話者抽出完了');
        
        -- 既存の話者を論理削除（ロック回避のためEXISTS句を追加）
        UPDATE dbo.Speakers 
        SET deleted_datetime = GETDATE()
        WHERE meeting_id = @meeting_id 
          AND deleted_datetime IS NULL
          AND EXISTS (SELECT 1 FROM dbo.Meetings WHERE meeting_id = @meeting_id);
        
        -- 話者情報をSpeakersテーブルに挿入
        INSERT INTO dbo.Speakers (
            speaker_name, 
            user_id, 
            meeting_id, 
            inserted_datetime, 
            updated_datetime
        )
        OUTPUT 
            inserted.speaker_id,
            inserted.speaker_name
        INTO #TempSpeakersWithIds (speaker_id, speaker_name)
        SELECT 
            speaker_name,
            @user_id,
            @meeting_id,
            GETDATE(),
            GETDATE()
        FROM
            #TempSpeakers;
            
        -- STEP3: Speakers テーブル登録完了をログ
        INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
        VALUES ('INFO', 'Speakers', @meeting_id, GETDATE(), 'STEP3: Speakers テーブル登録完了');
        
        -- 既存のConversationSegmentsを論理削除（ロック回避のためEXISTS句を追加）
        UPDATE dbo.ConversationSegments
        SET deleted_datetime = GETDATE()
        WHERE meeting_id = @meeting_id
          AND deleted_datetime IS NULL
          AND EXISTS (SELECT 1 FROM dbo.Meetings WHERE meeting_id = @meeting_id);
        
        -- セグメント抽出用の一時テーブル作成
        CREATE TABLE #TempSegments (
            speaker_name NVARCHAR(50),
            content NVARCHAR(MAX),
            segment_order INT IDENTITY(1,1),
            start_time FLOAT NULL,
            end_time FLOAT NULL
        );
        
        -- セグメント抽出処理
        SET @pos = 1;
        SET @loop_count = 0;
        DECLARE @text_start INT;
        DECLARE @text_end INT;
        DECLARE @segment_text NVARCHAR(MAX);
        
        WHILE @pos <= LEN(@transcript_text) AND @loop_count < 10000
        BEGIN
            SET @loop_count += 1;
            
            -- 括弧で囲まれた話者名を検索
            SET @match_start = CHARINDEX('(', @transcript_text, @pos);
            IF @match_start = 0 BREAK;
            
            SET @match_end = CHARINDEX(')', @transcript_text, @match_start);
            IF @match_end = 0 BREAK;
            
            SET @speaker_name = SUBSTRING(@transcript_text, @match_start + 1, @match_end - @match_start - 1);
            
            -- テキスト部分を検索（角括弧で囲まれた部分）
            SET @text_start = CHARINDEX('[', @transcript_text, @match_end);
            IF @text_start = 0 
            BEGIN
                SET @pos = @match_end + 1;
                CONTINUE;
            END;
            
            SET @text_end = CHARINDEX(']', @transcript_text, @text_start);
            IF @text_end = 0 
            BEGIN
                SET @pos = @text_start + 1;
                CONTINUE;
            END;
            
            SET @segment_text = SUBSTRING(@transcript_text, @text_start + 1, @text_end - @text_start - 1);
            
            -- 一時テーブルに挿入
            INSERT INTO #TempSegments (speaker_name, content)
            VALUES (@speaker_name, @segment_text);
            
            SET @pos = @text_end + 1;
        END;
        
        -- ループ上限チェック
        IF @loop_count >= 10000
        BEGIN
            RAISERROR('セグメント抽出のループ上限（10000）に達しました。文字起こしテキストの形式を確認してください。', 16, 1);
            RETURN;
        END;
        
        -- STEP4: セグメント抽出完了をログ
        INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
        VALUES ('INFO', 'ConversationSegments', @meeting_id, GETDATE(), 'STEP4: セグメント抽出完了');
        
        -- セグメントをConversationSegmentsテーブルに挿入
        INSERT INTO dbo.ConversationSegments (
            user_id,
            speaker_id,
            meeting_id,
            content,
            file_name,
            file_path,
            file_size,
            duration_seconds,
            status,
            start_time,
            end_time,
            inserted_datetime,
            updated_datetime
        )
        SELECT 
            @user_id,
            s.speaker_id,
            @meeting_id,
            ts.content,
            @file_name,
            @file_path,
            @file_size,
            @duration_seconds,
            'completed',
            ts.start_time,
            ts.end_time,
            GETDATE(),
            GETDATE()
        FROM
            #TempSegments ts
        INNER JOIN 
            #TempSpeakersWithIds s ON ts.speaker_name = s.speaker_name
        ORDER BY 
            ts.segment_order;
            
        -- STEP5: Segments テーブル登録完了をログ
        INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
        VALUES ('INFO', 'ConversationSegments', @meeting_id, GETDATE(), 'STEP5: Segments テーブル登録完了');
        
        -- Meetingsテーブルの状態を更新（ロック回避のためEXISTS句を追加）
        IF @current_status = 'completed'
        BEGIN
            UPDATE dbo.Meetings
            SET 
                status = 'completed_with_speakers_and_segments',
                updated_datetime = GETDATE()
            WHERE 
                meeting_id = @meeting_id
                AND EXISTS (SELECT 1 FROM dbo.Meetings WHERE meeting_id = @meeting_id);
                
            -- STEP6: Meetings ステータス更新完了をログ
            INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
            VALUES ('INFO', 'Meetings', @meeting_id, GETDATE(), 'STEP6: Meetings ステータス更新完了');
        END;
        
        -- 一時テーブルを削除
        DROP TABLE #TempSpeakers;
        DROP TABLE #TempSpeakersWithIds;
        DROP TABLE #TempSegments;
        
        -- トランザクションをコミット
        COMMIT TRANSACTION;
            
    END TRY
    BEGIN CATCH
        -- エラー情報を取得
        SET @ErrorMessage = ERROR_MESSAGE();
        SET @ErrorSeverity = ERROR_SEVERITY();
        SET @ErrorState = ERROR_STATE();
        
        -- トランザクションをロールバック
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
        
        -- エラー情報をログに記録
        INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
        VALUES ('ERROR', 'Speakers', @meeting_id, GETDATE(), @ErrorMessage);
        
        -- エラーステータスを更新（ロック回避のためEXISTS句を追加）
        UPDATE dbo.Meetings
        SET 
            status = 'error',
            error_message = CONCAT('話者・セグメント抽出エラー: ', @ErrorMessage),
            updated_datetime = GETDATE()
        WHERE 
            meeting_id = @meeting_id
            AND EXISTS (SELECT 1 FROM dbo.Meetings WHERE meeting_id = @meeting_id);
        
        -- エラーを再スロー
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH;
END;