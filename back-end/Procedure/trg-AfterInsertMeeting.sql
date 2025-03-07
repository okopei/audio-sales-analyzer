CREATE OR ALTER TRIGGER [dbo].[trg_AfterInsertMeeting]
ON [dbo].[Meetings]
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    
    -- 挿入されたデータを取得
    DECLARE @meeting_id INT;
    SELECT @meeting_id = meeting_id FROM inserted;
    
    -- ログを残す
    INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
    VALUES ('INSERT', 'Meetings', @meeting_id, GETDATE(), '会議データが挿入されました');
    
    -- 文字起こしテキストが存在し、ステータスが'completed'の場合のみプロシージャを実行
    IF EXISTS (SELECT 1 FROM inserted WHERE transcript_text IS NOT NULL AND LEN(transcript_text) > 0 AND status = 'completed')
    BEGIN
        -- ストアドプロシージャを実行
        EXEC dbo.sp_ExtractSpeakersAndSegmentsFromTranscript @meeting_id;
    END
    ELSE
    BEGIN
        -- 文字起こしテキストがないか、ステータスが'completed'でない場合はログに記録
        INSERT INTO dbo.TriggerLog (event_type, table_name, record_id, event_time, additional_info)
        VALUES ('SKIP', 'Meetings', @meeting_id, GETDATE(), '文字起こしテキストがないか、ステータスが完了でないため、話者・セグメント抽出をスキップします');
    END
END 