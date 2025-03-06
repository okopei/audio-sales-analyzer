CREATE OR ALTER PROCEDURE [dbo].[sp_ExtractSpeakersFromTranscript]
    @meeting_id INT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- 処理対象の会議データを取得
        DECLARE @transcript_text NVARCHAR(MAX);
        DECLARE @user_id INT;
        DECLARE @current_status NVARCHAR(50);
        
        SELECT 
            @transcript_text = transcript_text,
            @user_id = user_id,
            @current_status = status
        FROM 
            dbo.Meetings
        WHERE 
            meeting_id = @meeting_id;
            
        -- transcript_textが空の場合は処理をスキップ
        IF @transcript_text IS NULL OR LEN(@transcript_text) = 0
        BEGIN
            INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
            VALUES ('WARNING', 'Meetings', @meeting_id, GETDATE(), '文字起こしテキストが空のため、話者抽出をスキップします');
            RETURN;
        END
        
        -- 一時テーブルを作成して話者を格納
        CREATE TABLE #TempSpeakers (
            speaker_name NVARCHAR(50)
        );
        
        -- 正規表現パターンを使用して話者を抽出
        -- パターン: (Speaker1), (Speaker2)などの形式
        DECLARE @pos INT = 1;
        DECLARE @match_start INT;
        DECLARE @match_end INT;
        DECLARE @speaker_name NVARCHAR(50);
        
        WHILE @pos <= LEN(@transcript_text)
        BEGIN
            -- 括弧で囲まれた話者名を検索
            SET @match_start = CHARINDEX('(', @transcript_text, @pos);
            
            -- 見つからなければループを終了
            IF @match_start = 0 BREAK;
            
            SET @match_end = CHARINDEX(')', @transcript_text, @match_start);
            
            -- 閉じ括弧が見つからなければループを終了
            IF @match_end = 0 BREAK;
            
            -- 話者名を抽出（括弧を除く）
            SET @speaker_name = SUBSTRING(@transcript_text, @match_start + 1, @match_end - @match_start - 1);
            
            -- 一時テーブルに挿入（重複を避けるためDISTINCTを使用）
            IF NOT EXISTS (SELECT 1 FROM #TempSpeakers WHERE speaker_name = @speaker_name)
            BEGIN
                INSERT INTO #TempSpeakers (speaker_name)
                VALUES (@speaker_name);
            END
            
            -- 次の検索位置を設定
            SET @pos = @match_end + 1;
        END
        
        -- 既存の話者を論理削除（同じmeeting_idに関連する話者を再作成するため）
        UPDATE dbo.Speakers 
        SET deleted_datetime = GETDATE()
        WHERE meeting_id = @meeting_id 
        AND deleted_datetime IS NULL;
        
        -- 一時テーブルから話者情報をSpeakersテーブルに挿入
        INSERT INTO dbo.Speakers (
            speaker_name, 
            user_id, 
            meeting_id, 
            inserted_datetime, 
            updated_datetime
        )
        SELECT 
            speaker_name,
            @user_id,
            @meeting_id,
            GETDATE(),
            GETDATE()
        FROM 
            #TempSpeakers;
            
        -- 一時テーブルを削除
        DROP TABLE #TempSpeakers;
        
        -- 処理完了ログ
        INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
        VALUES ('PROCESS', 'Speakers', @meeting_id, GETDATE(), '話者抽出が正常に完了しました');
        
        -- Meetingsテーブルの状態を更新（既存のstatusカラムを使用）
        -- 'completed'状態の場合のみ'completed_with_speakers'に更新
        IF @current_status = 'completed'
        BEGIN
            UPDATE dbo.Meetings
            SET 
                status = 'completed_with_speakers',
                updated_datetime = GETDATE()
            WHERE 
                meeting_id = @meeting_id;
        END
            
    END TRY
    BEGIN CATCH
        -- エラー情報を取得
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        
        -- エラー情報をログに記録
        INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
        VALUES ('ERROR', 'Speakers', @meeting_id, GETDATE(), @ErrorMessage);
        
        -- エラーステータスを更新（既存のstatusカラムとerror_messageカラムを使用）
        UPDATE dbo.Meetings
        SET 
            status = 'error',
            error_message = CONCAT('話者抽出エラー: ', @ErrorMessage),
            updated_datetime = GETDATE()
        WHERE 
            meeting_id = @meeting_id;
        
        -- エラーを再スロー
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END