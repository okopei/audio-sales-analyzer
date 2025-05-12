[2025-05-12T08:58:31.639Z] Host lock lease acquired by instance ID '000000000000000000000000CBBBE2FF'.
[2025-05-12T08:58:36.569Z] Executing 'Functions.TranscriptionCallback' (Reason='This function was programmatically called via the host APIs.', Id=ce265f4f-6fd3-4fcb-9d08-d82a593673b9)
[2025-05-12T08:58:36.576Z] === Transcription Callback Start ===      
[2025-05-12T08:58:36.578Z] Received webhook data: {'self': 'https://japaneast.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions/b5fdea33-3ead-400e-b7b3-80073cbb182e', 'contentUrls': ['https://audiosalesanalyzeraudio.blob.core.windows.net/moc-audio/meeting_71_user_27_2025-04-30T02-11-30-801.wav'], 'resultsUrls': {'channel_0': 'https://spsvcprodjpe.blob.core.windows.net/bestor-948e9f4b-98f0-414a-b695-603be7bddabe/TranscriptionData/b5fdea33-3ead-400e-b7b3-80073cbb182e_0_0.json?skoid=c243ab90-da1a-4893-986b-063e4b26bd23&sktid=33e01921-4d64-4f8c-a055-5bdaffd5e33d&skt=2025-05-12T06%3A03%3A43Z&ske=2025-05-17T06%3A08%3A43Z&sks=b&skv=2021-08-06&sv=2025-01-05&st=2025-05-12T06%3A03%3A43Z&se=2025-05-12T18%3A08%3A43Z&sr=b&sp=rl&sig=vs4v0GN2f8oTAp2BvoSaKk05SX49QDN35Og8Y%2FUT2LA%3D'}, 'status': 'Succeeded'}
[2025-05-12T08:58:36.580Z] Webhook called. Transcription job URL: https://japaneast.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions/b5fdea33-3ead-400e-b7b3-80073cbb182e
[2025-05-12T08:58:36.582Z] Processing file: meeting_71_user_27_2025-04-30T02-11-30-801.wav
[2025-05-12T08:58:36.584Z] File path: moc-audio/meeting_71_user_27_2025-04-30T02-11-30-801.wav
[2025-05-12T08:58:36.586Z] Extracted meeting_id: 71, user_id: 27     
[2025-05-12T08:58:36.587Z] No environment configuration found.       
[2025-05-12T08:58:36.588Z] ManagedIdentityCredential will use IMDS   
[2025-05-12T08:58:36.590Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.21.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T08:58:39.768Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T08:58:40.958Z] Found client info - Company: okada-test5, Contact: okada-test2
[2025-05-12T08:58:40.961Z] Fetching transcription status from: https://japaneast.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions/b5fdea33-3ead-400e-b7b3-80073cbb182e
[2025-05-12T08:58:41.167Z] Transcription status: Succeeded
[2025-05-12T08:58:41.169Z] Fetching transcription results from: https://spsvcprodjpe.blob.core.windows.net/bestor-948e9f4b-98f0-414a-b695-603be7bddabe/TranscriptionData/b5fdea33-3ead-400e-b7b3-80073cbb182e_0_0.json?skoid=c243ab90-da1a-4893-986b-063e4b26bd23&sktid=33e01921-4d64-4f8c-a055-5bdaffd5e33d&skt=2025-05-12T06%3A03%3A43Z&ske=2025-05-17T06%3A08%3A43Z&sks=b&skv=2021-08-06&sv=2025-01-05&st=2025-05-12T06%3A03%3A43Z&se=2025-05-12T18%3A08%3A43Z&sr=b&sp=rl&sig=vs4v0GN2f8oTAp2BvoSaKk05SX49QDN35Og8Y%2FUT2LA%3D
[2025-05-12T08:58:41.362Z] Successfully retrieved and parsed transcription results
[2025-05-12T08:58:41.364Z] Generated transcript text: (Speaker1)[こんにちは。今日はいい天気ですね。] (Speaker2)[こんにちは。本当に気持ちいいですね。] (Speaker1)[週末は何をする予定ですか？] (Speaker2)[家族...
[2025-05-12T08:58:41.369Z] Request URL: 'https://audiosalesanalyzeraudio.blob.core.windows.net/moc-audio/meeting_71_user_27_2025-04-30T02-11-30-801.wav'
Request method: 'HEAD'
Request headers:
    'x-ms-version': 'REDACTED'
    'Accept': 'application/xml'
    'User-Agent': 'azsdk-python-storage-blob/12.25.1 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
    'x-ms-date': 'REDACTED'
    'x-ms-client-request-id': '4d239b24-2f0f-11f0-a269-b4b5b6f20152' 
    'Authorization': 'REDACTED'
No body was attached to the request
[2025-05-12T08:58:41.580Z] Response status: 200
Response headers:
    'Content-Length': '1071438'
    'Content-Type': 'application/octet-stream'
    'Content-MD5': 'REDACTED'
    'Last-Modified': 'Mon, 12 May 2025 05:38:37 GMT'
    'Accept-Ranges': 'REDACTED'
    'ETag': '"0x8DD91173E93C470"'
    'Vary': 'REDACTED'
    'Server': 'Windows-Azure-Blob/1.0 Microsoft-HTTPAPI/2.0'
    'x-ms-request-id': 'd6b5f8a1-c01e-000d-741c-c33684000000'        
    'x-ms-client-request-id': '4d239b24-2f0f-11f0-a269-b4b5b6f20152' 
    'x-ms-version': 'REDACTED'
    'x-ms-resource-type': 'REDACTED'
    'x-ms-creation-time': 'REDACTED'
    'x-ms-lease-status': 'REDACTED'
    'x-ms-lease-state': 'REDACTED'
    'x-ms-blob-type': 'REDACTED'
    'x-ms-server-encrypted': 'REDACTED'
    'x-ms-access-tier': 'REDACTED'
    'x-ms-access-tier-inferred': 'REDACTED'
    'x-ms-owner': 'REDACTED'
    'x-ms-group': 'REDACTED'
    'x-ms-permissions': 'REDACTED'
    'x-ms-acl': 'REDACTED'
    'Date': 'Mon, 12 May 2025 08:58:40 GMT'
[2025-05-12T08:58:41.582Z] Updating transcript_text for meeting_id: 71, user_id: 27
[2025-05-12T08:58:41.584Z] Request URL: 'https://audiosalesanalyzeraudio.blob.core.windows.net/moc-audio/meeting_71_user_27_2025-04-30T02-11-30-801.wav'
Request method: 'HEAD'
Request headers:
    'x-ms-version': 'REDACTED'
    'Accept': 'application/xml'
    'User-Agent': 'azsdk-python-storage-blob/12.25.1 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
    'x-ms-date': 'REDACTED'
    'x-ms-client-request-id': '4d43debf-2f0f-11f0-9cd0-b4b5b6f20152' 
    'Authorization': 'REDACTED'
No body was attached to the request
[2025-05-12T08:58:41.782Z] Response status: 200
Response headers:
    'Content-Length': '1071438'
    'Content-Type': 'application/octet-stream'
    'Content-MD5': 'REDACTED'
    'Last-Modified': 'Mon, 12 May 2025 05:38:37 GMT'
    'Accept-Ranges': 'REDACTED'
    'ETag': '"0x8DD91173E93C470"'
    'Vary': 'REDACTED'
    'Server': 'Windows-Azure-Blob/1.0 Microsoft-HTTPAPI/2.0'
    'x-ms-request-id': '0c98b8e0-b01e-0075-631c-c3957c000000'        
    'x-ms-client-request-id': '4d43debf-2f0f-11f0-9cd0-b4b5b6f20152' 
    'x-ms-version': 'REDACTED'
    'x-ms-resource-type': 'REDACTED'
    'x-ms-creation-time': 'REDACTED'
    'x-ms-lease-status': 'REDACTED'
    'x-ms-lease-state': 'REDACTED'
    'x-ms-blob-type': 'REDACTED'
    'x-ms-server-encrypted': 'REDACTED'
    'x-ms-access-tier': 'REDACTED'
    'x-ms-access-tier-inferred': 'REDACTED'
    'x-ms-owner': 'REDACTED'
    'x-ms-group': 'REDACTED'
    'x-ms-permissions': 'REDACTED'
    'x-ms-acl': 'REDACTED'
    'Date': 'Mon, 12 May 2025 08:58:40 GMT'
[2025-05-12T08:58:41.784Z] No environment configuration found.       
[2025-05-12T08:58:41.785Z] ManagedIdentityCredential will use IMDS   
[2025-05-12T08:58:41.786Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.21.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T08:58:44.774Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T08:58:44.775Z] Connecting to database with ODBC Driver 17 for SQL Server
[2025-05-12T08:58:45.384Z] クエリを実行: 
            MERGE INTO dbo.Meetings AS target
            USING (
                SELECT
                    ? AS meeting_id,
                    ? AS user_id,
                    ? AS transcript_text,
                    ? AS title,
                    ? AS file_name,
                    ? AS file_path,
                    ? AS file_size,
                    ? AS duration_seconds,
                    ? AS status,
                    ? AS client_company_name,
                    ? AS client_contact_name,
                    ? AS meeting_datetime,
                    ? AS start_datetime
                ) AS source
            ON (target.meeting_id = source.meeting_id AND target.user_id = source.user_id)
            WHEN MATCHED THEN
                UPDATE SET
                    transcript_text = source.transcript_text,        
                    updated_datetime = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (
                    meeting_id,
                    user_id,
                    transcript_text,
                    title,
                    file_name,
                    file_path,
                    file_size,
                    duration_seconds,
                    status,
                    client_company_name,
                    client_contact_name,
                    meeting_datetime,
                    start_datetime,
                    inserted_datetime
                ) VALUES (
                    source.meeting_id,
                    source.user_id,
                    source.transcript_text,
                    source.title,
                    source.file_name,
                    source.file_path,
                    source.file_size,
                    source.duration_seconds,
                    source.status,
                    source.client_company_name,
                    source.client_contact_name,
                    source.meeting_datetime,
                    source.start_datetime,
                    GETDATE()
                );

[2025-05-12T08:58:45.387Z] paramsの型: <class 'tuple'>
[2025-05-12T08:58:45.388Z] パラメータ: (71, 27, '(Speaker1)[こんにち は。今日はいい天気ですね。] (Speaker2)[こんにちは。本当に気持ちいいですね。] (Speaker1)[週末は何をする予定ですか？] (Speaker2)[家族と公園 に行くつもりです。あなた。] (Speaker1)[は？私は友達とカフェで勉強します。] (Speaker2)[いいですね。どんな勉強をするんですか？] (Speaker1)[ 英語のビジネスメールの書き方を練習します。] (Speaker2)[役に立ちそうですね。頑張ってください。] (Speaker1)[ありがとうございます。]', '会議 2025-04-30 02:11', 'meeting_71_user_27_2025-04-30T02-11-30-801.wav', 'moc-audio/meeting_71_user_27_2025-04-30T02-11-30-801.wav', 1071438, 0, 'completed', 'okada-test5', 'okada-test2', '2025-04-30 02:11:30', '2025-04-30 02:11:30')
[2025-05-12T08:58:45.467Z] ? コミット完了（execute_query）
[2025-05-12T08:58:45.469Z] ? Successfully updated transcript_text for meeting_id: 71, user_id: 27, title: 会議 2025-04-30 02:11, file: meeting_71_user_27_2025-04-30T02-11-30-801.wav
[2025-05-12T08:58:45.470Z] Executing sp_ExtractSpeakersAndSegmentsFromTranscript for meeting_id: 71
[2025-05-12T08:58:45.471Z] No environment configuration found.       
[2025-05-12T08:58:45.472Z] ManagedIdentityCredential will use IMDS   
[2025-05-12T08:58:45.474Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.21.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T08:58:48.492Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T08:58:48.493Z] Connecting to database with ODBC Driver 17 for SQL Server
[2025-05-12T08:58:48.966Z] クエリを実行: EXEC dbo.sp_ExtractSpeakersAndSegmentsFromTranscript ?
[2025-05-12T08:58:48.968Z] paramsの型: <class 'tuple'>
[2025-05-12T08:58:48.969Z] パラメータ: (71,)
[2025-05-12T08:58:49.152Z] ? コミット完了（execute_query）
[2025-05-12T08:58:49.154Z] ? Successfully executed sp_ExtractSpeakersAndSegmentsFromTranscript for meeting_id: 71
[2025-05-12T08:58:49.156Z] No environment configuration found.       
[2025-05-12T08:58:49.157Z] ManagedIdentityCredential will use IMDS   
[2025-05-12T08:58:49.458Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.21.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T08:58:52.508Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T08:58:52.509Z] Connecting to database with ODBC Driver 17 for SQL Server
[2025-05-12T08:58:53.043Z] クエリを実行: 
            INSERT INTO dbo.TriggerLog (
                event_type, table_name, record_id, event_time, additional_info
            ) VALUES (?, ?, ?, GETDATE(), ?)

[2025-05-12T08:58:53.045Z] paramsの型: <class 'tuple'>
[2025-05-12T08:58:53.045Z] パラメータ: ('INFO', 'Meetings', 71, '文字起こしテキストの更新と話者・セグメント抽出が完了しました。文字数: 269                event_type, table_name, record_id, event_time, additional_info
            ) VALUES (?, ?, ?, GETDATE(), ?)

[2025-05-12T08:58:53.045Z] paramsの型: <class 'tuple'>
[2025-05-12T08:58:53.045Z] パラメータ: ('INFO', 'Meetings', 71, '文字起こしテキストの更新と話者・セグメント抽出が完了しました。文字数: 269起こしテキストの更新と話者・セグメント抽出が完了しました。文字数: 269')
[2025-05-12T08:58:53.172Z] ? コミット完了（execute_query）
[2025-05-12T08:58:53.173Z] ? TriggerLog inserted successfully for meeting_id: 71
[2025-05-12T08:58:53.175Z] Executed 'Functions.TranscriptionCallback' (Succeeded, Id=ce265f4f-6fd3-4fcb-9d08-d82a593673b9, Duration=16608ms)