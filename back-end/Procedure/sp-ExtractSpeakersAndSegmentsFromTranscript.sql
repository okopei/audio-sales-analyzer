-- 修正版: 会話の順番でConversationSegmentsに挿入するプロシージャ
CREATE OR ALTER PROCEDURE [dbo].[sp_ExtractSpeakersAndSegmentsFromTranscript]
    @meeting_id INT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- 処理対象の会議データを取得
        DECLARE @transcript_text NVARCHAR(MAX);
        DECLARE @user_id INT;
        DECLARE @current_status NVARCHAR(50);
        DECLARE @file_name NVARCHAR(200);
        DECLARE @file_path NVARCHAR(1000);
        DECLARE @file_size BIGINT;
        DECLARE @duration_seconds INT;
        
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
        
        -- 一時テーブルを作成して話者IDを格納
        CREATE TABLE #TempSpeakersWithIds (
            speaker_id INT,
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
        
        -- 一時テーブルから話者情報をSpeakersテーブルに挿入し、IDを取得
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
            
        -- 処理完了ログ
        INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
        VALUES ('PROCESS', 'Speakers', @meeting_id, GETDATE(), '話者抽出が正常に完了しました');
        
        -- 既存のConversationSegmentsを論理削除
        UPDATE dbo.ConversationSegments
        SET deleted_datetime = GETDATE()
        WHERE meeting_id = @meeting_id
        AND deleted_datetime IS NULL;
        
        -- 一時テーブルを作成してセグメントを格納（会話の順序を保存）
        CREATE TABLE #TempSegments (
            speaker_name NVARCHAR(50),
            content NVARCHAR(MAX),
            segment_order INT IDENTITY(1,1)
        );
        
        -- 文字起こしテキストからセグメントを抽出
        -- パターン: (Speaker1)[テキスト] (Speaker2)[テキスト]などの形式
        SET @pos = 1;
        DECLARE @text_start INT;
        DECLARE @text_end INT;
        DECLARE @segment_text NVARCHAR(MAX);
        
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
            
            -- テキスト部分を検索（角括弧で囲まれた部分）
            SET @text_start = CHARINDEX('[', @transcript_text, @match_end);
            
            -- 角括弧が見つからなければ次の話者へ
            IF @text_start = 0 
            BEGIN
                SET @pos = @match_end + 1;
                CONTINUE;
            END
            
            SET @text_end = CHARINDEX(']', @transcript_text, @text_start);
            
            -- 閉じ角括弧が見つからなければ次の話者へ
            IF @text_end = 0 
            BEGIN
                SET @pos = @text_start + 1;
                CONTINUE;
            END
            
            -- テキストを抽出（角括弧を除く）
            SET @segment_text = SUBSTRING(@transcript_text, @text_start + 1, @text_end - @text_start - 1);
            
            -- 一時テーブルに挿入（会話の順序が自動的に記録される）
            INSERT INTO #TempSegments (speaker_name, content)
            VALUES (@speaker_name, @segment_text);
            
            -- 次の検索位置を設定
            SET @pos = @text_end + 1;
        END
        
        -- セグメントをConversationSegmentsテーブルに挿入（会話の順序でソート）
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
            GETDATE(),
            GETDATE()
        FROM 
            #TempSegments ts
        INNER JOIN 
            #TempSpeakersWithIds s ON ts.speaker_name = s.speaker_name
        ORDER BY 
            ts.segment_order;
            
        -- 一時テーブルを削除
        DROP TABLE #TempSpeakers;
        DROP TABLE #TempSpeakersWithIds;
        DROP TABLE #TempSegments;
        
        -- 処理完了ログ
        INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
        VALUES ('PROCESS', 'ConversationSegments', @meeting_id, GETDATE(), 'セグメント抽出が正常に完了しました');
        
        -- Meetingsテーブルの状態を更新（既存のstatusカラムを使用）
        -- 'completed'状態の場合のみ'completed_with_speakers_and_segments'に更新
        IF @current_status = 'completed'
        BEGIN
            UPDATE dbo.Meetings
            SET 
                status = 'completed_with_speakers_and_segments',
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
            error_message = CONCAT('話者・セグメント抽出エラー: ', @ErrorMessage),
            updated_datetime = GETDATE()
        WHERE 
            meeting_id = @meeting_id;
        
        -- エラーを再スロー
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END 