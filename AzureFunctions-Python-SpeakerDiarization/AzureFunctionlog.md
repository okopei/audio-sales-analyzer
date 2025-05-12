[2025-05-12T06:10:44.259Z] Executing 'Functions.TranscriptionCallback' (Reason='This function was programmatically called via the host APIs.', Id=72313f2a-bf65-42a5-bb90-d93c133a7e53)
[2025-05-12T06:10:44.267Z] === Transcription Callback Start ===      
[2025-05-12T06:10:44.269Z] Received webhook data: {'self': 'https://japaneast.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions/b5fdea33-3ead-400e-b7b3-80073cbb182e', 'contentUrls': ['https://audiosalesanalyzeraudio.blob.core.windows.net/moc-audio/meeting_71_user_27_2025-04-30T02-11-30-801.wav'], 'resultsUrls': {'channel_0': 'https://spsvcprodjpe.blob.core.windows.net/bestor-948e9f4b-98f0-414a-b695-603be7bddabe/TranscriptionData/b5fdea33-3ead-400e-b7b3-80073cbb182e_0_0.json?skoid=c243ab90-da1a-4893-986b-063e4b26bd23&sktid=33e01921-4d64-4f8c-a055-5bdaffd5e33d&skt=2025-05-12T06%3A03%3A43Z&ske=2025-05-17T06%3A08%3A43Z&sks=b&skv=2021-08-06&sv=2025-01-05&st=2025-05-12T06%3A03%3A43Z&se=2025-05-12T18%3A08%3A43Z&sr=b&sp=rl&sig=vs4v0GN2f8oTAp2BvoSaKk05SX49QDN35Og8Y%2FUT2LA%3D'}, 'status': 'Succeeded'}
[2025-05-12T06:10:44.271Z] Webhook called. Transcription job URL: https://japaneast.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions/b5fdea33-3ead-400e-b7b3-80073cbb182e
[2025-05-12T06:10:44.273Z] Results URL expiration time: 2025-05-12T18:08:43+00:00
[2025-05-12T06:10:44.274Z] Current time: 2025-05-12T06:10:44.263925+00:00
[2025-05-12T06:10:44.276Z] ? Results URL is valid until: 2025-05-12T18:08:43+00:00
[2025-05-12T06:10:44.277Z] Processing file: meeting_71_user_27_2025-04-30T02-11-30-801.wav
[2025-05-12T06:10:44.279Z] File path: moc-audio/meeting_71_user_27_2025-04-30T02-11-30-801.wav
[2025-05-12T06:10:44.280Z] Extracted meeting_id: 71, user_id: 27     
[2025-05-12T06:10:44.281Z] No environment configuration found.       
[2025-05-12T06:10:44.282Z] ManagedIdentityCredential will use IMDS   
[2025-05-12T06:10:44.284Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.21.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T06:10:47.396Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T06:10:47.886Z] Found client info - Company: okada-test5, Contact: okada-test2
[2025-05-12T06:10:47.888Z] Fetching transcription status from: https://japaneast.api.cognitive.microsoft.com/speechtotext/v3.0/transcriptions/b5fdea33-3ead-400e-b7b3-80073cbb182e
[2025-05-12T06:10:48.008Z] Transcription status: Succeeded
[2025-05-12T06:10:48.010Z] Fetching transcription results from: https://spsvcprodjpe.blob.core.windows.net/bestor-948e9f4b-98f0-414a-b695-603be7bddabe/TranscriptionData/b5fdea33-3ead-400e-b7b3-80073cbb182e_0_0.json?skoid=c243ab90-da1a-4893-986b-063e4b26bd23&sktid=33e01921-4d64-4f8c-a055-5bdaffd5e33d&skt=2025-05-12T06%3A03%3A43Z&ske=2025-05-17T06%3A08%3A43Z&sks=b&skv=2021-08-06&sv=2025-01-05&st=2025-05-12T06%3A03%3A43Z&se=2025-05-12T18%3A08%3A43Z&sr=b&sp=rl&sig=vs4v0GN2f8oTAp2BvoSaKk05SX49QDN35Og8Y%2FUT2LA%3D
[2025-05-12T06:10:48.145Z] Successfully retrieved and parsed transcription results
[2025-05-12T06:10:48.148Z] Generated transcript text: (Speaker1)[こんにちは。今日はいい天気ですね。] (Speaker2)[こんにちは。本当に気持ちいいですね。] (Speaker1)[週末は何をする予定ですか？] (Speaker2)[家族...
[2025-05-12T06:10:48.149Z] Request URL: 'https://audiosalesanalyzeraudio.blob.core.windows.net/moc-audio/meeting_71_user_27_2025-04-30T02-11-30-801.wav'
Request method: 'HEAD'
Request headers:
    'x-ms-version': 'REDACTED'
    'Accept': 'application/xml'
    'User-Agent': 'azsdk-python-storage-blob/12.25.1 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
    'x-ms-date': 'REDACTED'
    'x-ms-client-request-id': 'd90784ee-2ef7-11f0-afc6-b4b5b6f20152' 
    'Authorization': 'REDACTED'
No body was attached to the request
[2025-05-12T06:10:48.303Z] Response status: 200
Response headers:
    'Content-Length': '1071438'
    'Content-Type': 'application/octet-stream'
    'Content-MD5': 'REDACTED'
    'Last-Modified': 'Mon, 12 May 2025 05:38:37 GMT'
    'Accept-Ranges': 'REDACTED'
    'ETag': '"0x8DD91173E93C470"'
    'Vary': 'REDACTED'
    'Server': 'Windows-Azure-Blob/1.0 Microsoft-HTTPAPI/2.0'
    'x-ms-request-id': '35feffbe-801e-0033-5c04-c3a1fb000000'        
    'x-ms-client-request-id': 'd90784ee-2ef7-11f0-afc6-b4b5b6f20152' 
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
    'Date': 'Mon, 12 May 2025 06:10:46 GMT'
[2025-05-12T06:10:48.306Z] No environment configuration found.       
[2025-05-12T06:10:48.307Z] ManagedIdentityCredential will use IMDS   
[2025-05-12T06:10:48.308Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.21.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T06:10:51.539Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T06:10:51.541Z] Connecting to database with ODBC Driver 17 for SQL Server
[2025-05-12T06:10:51.966Z] クエリを実行: 
        MERGE INTO dbo.Meetings AS target
        USING (SELECT ? AS meeting_id, ? AS user_id) AS source       
        ON (target.meeting_id = source.meeting_id AND target.user_id = source.user_id)
        WHEN MATCHED THEN UPDATE SET
            title = ?, file_name = ?, file_path = ?, file_size = ?, duration_seconds = ?,
            status = ?, transcript_text = ?, error_message = ?, client_company_name = ?,
            client_contact_name = ?, meeting_datetime = ?, start_datetime = ?, end_datetime = ?,
            inserted_datetime = ?, updated_datetime = ?
        WHEN NOT MATCHED THEN INSERT (
            meeting_id, user_id, title, file_name, file_path, file_size, duration_seconds,
            status, transcript_text, error_message, client_company_name, client_contact_name,
            meeting_datetime, start_datetime, end_datetime, inserted_datetime, updated_datetime
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

[2025-05-12T06:10:51.968Z] パラメータ: [71, 27, '会議 2025-04-30 02:11', 'meeting_71_user_27_2025-04-30T02-11-30-801.wav', 'moc-audio/meeting_71_user_27_2025-04-30T02-11-30-801.wav', 1071438, 0, 'completed', '(Speaker1)[こんにちは。今日はいい天気ですね。] (Speaker2)[こんにち は。本当に気持ちいいですね。] (Speaker1)[週末は何をする予定ですか？] (Speaker2)[家族と公園に行くつもりです。あなた。] (Speaker1)[は？私は 友達とカフェで勉強します。] (Speaker2)[いいですね。どんな勉強をするんですか？] (Speaker1)[英語のビジネスメールの書き方を練習します。] (Speaker2)[役に立ちそうですね。頑張ってください。] (Speaker1)[ありがとう ございます。]', None, 'okada-test5', 'okada-test2', '2025-04-30 02:11:30', '2025-04-30 02:11:30', '2025-04-30 02:11:30', '2025-05-12 06:10:48', '2025-05-12 06:10:48', 71, 27, '会議 2025-04-30 02:11', 'meeting_71_user_27_2025-04-30T02-11-30-801.wav', 'moc-audio/meeting_71_user_27_2025-04-30T02-11-30-801.wav', 1071438, 0, 'completed', '(Speaker1)[こんにちは。今日はいい天気ですね。] (Speaker2)[こんにちは。本当に気持ちいいですね。] (Speaker1)[週末は何をする予定ですか？] (Speaker2)[ 家族と公園に行くつもりです。あなた。] (Speaker1)[は？私は友達とカフェで勉強します。] (Speaker2)[いいですね。どんな勉強をするんですか？] (Speaker1)[英語のビジネスメールの書き方を練習します。] (Speaker2)[役に 立ちそうですね。頑張ってください。] (Speaker1)[ありがとうございます。]', None, 'okada-test5', 'okada-test2', '2025-04-30 02:11:30', '2025-04-30 02:11:30', '2025-04-30 02:11:30', '2025-05-12 06:10:48', '2025-05-12 06:10:48']


