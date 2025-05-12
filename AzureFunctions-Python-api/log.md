PS C:\Users\okoma\Desktop\audio-sales-analyzer\AzureFunctions-Python-api> func start
Found Python version 3.12.9 (py).

Azure Functions Core Tools
Core Tools Version:       4.0.7030 Commit hash: N/A +bb4c949899cd5659d6bfe8b92cc923453a2e8f88 (64-bit)
Function Runtime Version: 4.1037.0.23568

[2025-05-12T11:24:46.677Z] Worker process started and initialized.

Functions:

        AddComment: [POST,OPTIONS] http://localhost:7071/api/api/comments

        GetComments: [GET,OPTIONS] http://localhost:7071/api/api/comments/{segment_id}

        GetConversationSegments: [GET,OPTIONS] http://localhost:7071/api/api/conversation/segments/{meeting_id}

        GetFeedback: [GET,OPTIONS] http://localhost:7071/api/feedback

        GetFeedbackByMeetingId: [GET,OPTIONS] http://localhost:7071/api/feedback/{meeting_id}

        GetLatestComments: [GET,OPTIONS] http://localhost:7071/api/api/comments-latest

        GetMeetings: [GET,OPTIONS] http://localhost:7071/api/meetings

        GetMembersMeetings: [GET,OPTIONS] http://localhost:7071/api/members-meetings

        GetUserById: [GET,OPTIONS] http://localhost:7071/api/users/{user_id}

        HealthCheck: [GET,OPTIONS] http://localhost:7071/api/health  

        Login: [POST,OPTIONS] http://localhost:7071/api/users/login  

        MarkCommentAsRead: [POST,OPTIONS] http://localhost:7071/api/api/comments/read

        RegisterTest: [GET,POST,OPTIONS] http://localhost:7071/api/register/test

        SaveBasicInfo: [POST,OPTIONS] http://localhost:7071/api/basicinfo

        SearchBasicInfo: [GET,OPTIONS] http://localhost:7071/api/basicinfo/search

        TestDbConnection: [GET,OPTIONS] http://localhost:7071/api/test/db-connection

For detailed output, run func with --verbose flag.
[2025-05-12T11:24:51.627Z] Host lock lease acquired by instance ID '000000000000000000000000CBBBE2FF'.
[2025-05-12T11:25:01.498Z] Executing 'Functions.GetUserById' (Reason='This function was programmatically called via the host APIs.', Id=20106b79-02ee-43e0-8bc6-76d34d6cfc96)
[2025-05-12T11:25:01.498Z] Executing 'Functions.GetMembersMeetings' (Reason='This function was programmatically called via the host APIs.', Id=7fa8596e-001d-4243-bccf-639a20ca3678)
[2025-05-12T11:25:01.538Z] No environment configuration found.
[2025-05-12T11:25:01.538Z] No environment configuration found.       
[2025-05-12T11:25:01.540Z] ManagedIdentityCredential will use IMDS   
[2025-05-12T11:25:01.541Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.20.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T11:25:01.542Z] ManagedIdentityCredential will use IMDS   
[2025-05-12T11:25:01.544Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.20.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T11:25:03.903Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T11:25:03.904Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T11:25:03.905Z] Connecting to database with ODBC Driver 17 for SQL Server
[2025-05-12T11:25:03.906Z] Connecting to database with ODBC Driver 17 for SQL Server
[2025-05-12T11:25:04.276Z] クエリを実行: 
            SELECT user_id, user_name, email, is_manager, manager_name, is_active, account_status
            FROM dbo.Users
            WHERE user_id = ?

[2025-05-12T11:25:04.276Z] クエリを実行:
            SELECT m.meeting_id, m.user_id, m.client_contact_name, m.client_company_name,
                   m.meeting_datetime, m.duration_seconds, m.status, m.transcript_text,
                   m.file_name, m.file_size, m.error_message, u.user_name
            FROM dbo.Meetings m
            JOIN dbo.Users u ON m.user_id = u.user_id

[2025-05-12T11:25:04.278Z] パラメータ: ('27',)
[2025-05-12T11:25:04.365Z] Executed 'Functions.GetUserById' (Succeeded, Id=20106b79-02ee-43e0-8bc6-76d34d6cfc96, Duration=2888ms)
[2025-05-12T11:25:04.365Z] Executed 'Functions.GetMembersMeetings' (Succeeded, Id=7fa8596e-001d-4243-bccf-639a20ca3678, Duration=2888ms)  
[2025-05-12T11:25:04.384Z] Executing 'Functions.GetUserById' (Reason='This function was programmatically called via the host APIs.', Id=bacb02d8-8b39-430e-903f-3a6a57213938)
[2025-05-12T11:25:04.384Z] Executing 'Functions.GetMembersMeetings' (Reason='This function was programmatically called via the host APIs.', Id=7d57d444-8137-4f60-bd6b-1cf930afdd1d)
[2025-05-12T11:25:04.389Z] No environment configuration found.       
[2025-05-12T11:25:04.390Z] ManagedIdentityCredential will use IMDS
[2025-05-12T11:25:04.391Z] No environment configuration found.       
[2025-05-12T11:25:04.392Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.20.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T11:25:04.393Z] ManagedIdentityCredential will use IMDS   
[2025-05-12T11:25:04.394Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.20.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T11:25:05.480Z] Executing 'Functions.GetMeetings' (Reason='This function was programmatically called via the host APIs.', Id=77e69d9b-e357-4747-98bc-a5ee5f2d3632)
[2025-05-12T11:25:05.486Z] No environment configuration found.       
[2025-05-12T11:25:05.487Z] ManagedIdentityCredential will use IMDS   
[2025-05-12T11:25:05.488Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.20.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T11:25:06.738Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T11:25:06.739Z] Connecting to database with ODBC Driver 17 for SQL Server
[2025-05-12T11:25:06.747Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T11:25:06.748Z] Connecting to database with ODBC Driver 17 for SQL Server
[2025-05-12T11:25:06.911Z] クエリを実行: 
            SELECT user_id, user_name, email, is_manager, manager_name, is_active, account_status
            FROM dbo.Users
            WHERE user_id = ?

[2025-05-12T11:25:06.913Z] パラメータ: ('27',)
[2025-05-12T11:25:06.918Z] クエリを実行:
            SELECT m.meeting_id, m.user_id, m.client_contact_name, m.client_company_name,
                   m.meeting_datetime, m.duration_seconds, m.status, m.transcript_text,
                   m.file_name, m.file_size, m.error_message, u.user_name
            FROM dbo.Meetings m
            JOIN dbo.Users u ON m.user_id = u.user_id

[2025-05-12T11:25:06.962Z] Executed 'Functions.GetMembersMeetings' (Succeeded, Id=7d57d444-8137-4f60-bd6b-1cf930afdd1d, Duration=2577ms)  
[2025-05-12T11:25:06.993Z] Executed 'Functions.GetUserById' (Succeeded, Id=bacb02d8-8b39-430e-903f-3a6a57213938, Duration=2609ms)
[2025-05-12T11:25:06.997Z] Executing 'Functions.GetUserById' (Reason='This function was programmatically called via the host APIs.', Id=42b60b66-938d-426d-879b-04744d916296)
[2025-05-12T11:25:07.001Z] No environment configuration found.       
[2025-05-12T11:25:07.002Z] ManagedIdentityCredential will use IMDS   
[2025-05-12T11:25:07.003Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.20.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T11:25:07.778Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T11:25:07.779Z] Connecting to database with ODBC Driver 17 for SQL Server
[2025-05-12T11:25:07.962Z] クエリを実行: 
            SELECT meeting_id, user_id, client_contact_name, client_company_name,
                   meeting_datetime, duration_seconds, status, transcript_text,
                   file_name, file_size, error_message
            FROM dbo.Meetings

[2025-05-12T11:25:08.028Z] Executed 'Functions.GetMeetings' (Succeeded, Id=77e69d9b-e357-4747-98bc-a5ee5f2d3632, Duration=2548ms)
[2025-05-12T11:25:08.032Z] Executing 'Functions.GetMeetings' (Reason='This function was programmatically called via the host APIs.', Id=5b53c361-6056-4e63-a62a-9a583406a6f7)
[2025-05-12T11:25:08.036Z] No environment configuration found.       
[2025-05-12T11:25:08.037Z] ManagedIdentityCredential will use IMDS   
[2025-05-12T11:25:08.038Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.20.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T11:25:09.190Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T11:25:09.191Z] Connecting to database with ODBC Driver 17 for SQL Server
[2025-05-12T11:25:09.370Z] クエリを実行: 
            SELECT user_id, user_name, email, is_manager, manager_name, is_active, account_status
            FROM dbo.Users
            WHERE user_id = ?

[2025-05-12T11:25:09.371Z] パラメータ: ('27',)
[2025-05-12T11:25:09.461Z] Executed 'Functions.GetUserById' (Succeeded, Id=42b60b66-938d-426d-879b-04744d916296, Duration=2464ms)
[2025-05-12T11:25:09.465Z] Executing 'Functions.GetUserById' (Reason='This function was programmatically called via the host APIs.', Id=a24003a3-f4b5-4fa3-abf1-5ac44cb4fb7c)
[2025-05-12T11:25:09.469Z] No environment configuration found.       
[2025-05-12T11:25:09.470Z] ManagedIdentityCredential will use IMDS   
[2025-05-12T11:25:09.471Z] Request URL: 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=REDACTED&resource=REDACTED'    
Request method: 'GET'
Request headers:
    'User-Agent': 'azsdk-python-identity/1.20.0 Python/3.12.9 (Windows-11-10.0.26100-SP0)'
No body was attached to the request
[2025-05-12T11:25:10.272Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T11:25:10.273Z] Connecting to database with ODBC Driver 17 for SQL Server
[2025-05-12T11:25:10.294Z] クエリを実行: 
            SELECT meeting_id, user_id, client_contact_name, client_company_name,
                   meeting_datetime, duration_seconds, status, transcript_text,
                   file_name, file_size, error_message
            FROM dbo.Meetings

[2025-05-12T11:25:10.372Z] Executed 'Functions.GetMeetings' (Succeeded, Id=5b53c361-6056-4e63-a62a-9a583406a6f7, Duration=2340ms)
[2025-05-12T11:25:11.715Z] DefaultAzureCredential acquired a token from AzureCliCredential
[2025-05-12T11:25:11.716Z] Connecting to database with ODBC Driver 17 for SQL Server
[2025-05-12T11:25:11.898Z] クエリを実行: 
            SELECT user_id, user_name, email, is_manager, manager_name, is_active, account_status
            FROM dbo.Users
            WHERE user_id = ?

[2025-05-12T11:25:11.900Z] パラメータ: ('27',)
[2025-05-12T11:25:11.943Z] Executed 'Functions.GetUserById' (Succeeded, Id=a24003a3-f4b5-4fa3-abf1-5ac44cb4fb7c, Duration=2478ms)
