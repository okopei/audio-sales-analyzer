"""
Audio Sales Analyzer API
Azure Functions アプリケーションのエントリーポイント
"""

import azure.functions as func
import logging
from azure.functions import AuthLevel, FunctionApp

# モジュール構造からのインポート
from src.auth import login, register, get_user_by_id
from src.meetings import get_meetings, get_members_meetings, save_basic_info, get_basic_info
# 削除する関数のインポートをコメントアウト: save_meeting, update_recording_from_blob

# Azure Functions アプリケーションの初期化
app = FunctionApp(http_auth_level=AuthLevel.ANONYMOUS)

# ヘルスチェックエンドポイント
@app.function_name(name="HealthCheck")
@app.route(route="health", methods=["GET", "OPTIONS"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """APIサーバーの稼働状態を確認するためのヘルスチェックエンドポイント"""
    logging.info("Health check endpoint called")
    
    if req.method == "OPTIONS":
        # CORS プリフライトリクエスト処理
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        return func.HttpResponse(status_code=204, headers=headers)
    
    # ヘルスチェックレスポンス
    headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
    return func.HttpResponse(
        body='{"status":"ok","message":"API server is running"}',
        status_code=200,
        headers=headers
    )

#
# 認証関連のエンドポイント
#

# テスト用ユーザー登録エンドポイント
@app.function_name(name="RegisterTest")
@app.route(route="register/test", methods=["GET", "POST", "OPTIONS"])
@app.generic_output_binding(
    arg_name="users",
    type="sql",
    CommandText="[dbo].[Users]",
    ConnectionStringSetting="SqlConnectionString"
)
def register_test(req: func.HttpRequest, users: func.Out[func.SqlRow]) -> func.HttpResponse:
    return register(req, users)

# ログインエンドポイント
@app.function_name(name="Login")
@app.route(route="users/login", methods=["POST", "OPTIONS"])
@app.generic_input_binding(
    arg_name="usersQuery", 
    type="sql",
    CommandText="SELECT * FROM dbo.Users",
    ConnectionStringSetting="SqlConnectionString"
)
def login_func(req: func.HttpRequest, usersQuery: func.SqlRowList) -> func.HttpResponse:
    return login(req, usersQuery)

# ユーザー情報取得エンドポイント
@app.function_name(name="GetUserById")
@app.route(route="users/{user_id}", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="usersQuery", 
    type="sql",
    CommandText="SELECT user_id, user_name, email, is_manager, manager_name, is_active, account_status FROM dbo.Users",
    ConnectionStringSetting="SqlConnectionString"
)
def get_user_by_id_func(req: func.HttpRequest, usersQuery: func.SqlRowList) -> func.HttpResponse:
    return get_user_by_id(req, usersQuery)

#
# 会議関連のエンドポイント
#

# save_meeting_funcエンドポイントを削除（Meetingsテーブルへの挿入機能）

# 基本情報保存エンドポイント
@app.function_name(name="SaveBasicInfo")
@app.route(route="basicinfo", methods=["POST", "OPTIONS"])
@app.generic_input_binding(
    arg_name="lastBasicInfo", 
    type="sql", 
    CommandText="SELECT TOP 1 meeting_id FROM dbo.BasicInfo ORDER BY meeting_id DESC", 
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_output_binding(
    arg_name="basicInfo", 
    type="sql", 
    CommandText="dbo.BasicInfo", 
    ConnectionStringSetting="SqlConnectionString"
)
def save_basic_info_func(req: func.HttpRequest, basicInfo: func.Out[func.SqlRow], lastBasicInfo: func.SqlRowList) -> func.HttpResponse:
    return save_basic_info(req, basicInfo, lastBasicInfo)

# 会議一覧取得エンドポイント
@app.function_name(name="GetMeetings")
@app.route(route="meetings", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="meetingsQuery", 
    type="sql", 
    CommandText="SELECT meeting_id, user_id, client_contact_name, client_company_name, meeting_datetime, duration_seconds, status, transcript_text, file_name, file_size, error_message FROM dbo.Meetings", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_meetings_func(req: func.HttpRequest, meetingsQuery: func.SqlRowList) -> func.HttpResponse:
    return get_meetings(req, meetingsQuery)

# メンバー会議一覧取得エンドポイント
@app.function_name(name="GetMembersMeetings")
@app.route(route="members-meetings", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="usersQuery", 
    type="sql", 
    CommandText="SELECT user_id, user_name, manager_name FROM dbo.Users", 
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_input_binding(
    arg_name="meetingsQuery", 
    type="sql", 
    CommandText="SELECT m.meeting_id, m.user_id, m.client_contact_name, m.client_company_name, m.meeting_datetime, m.duration_seconds, m.status, m.transcript_text, m.file_name, m.file_size, m.error_message, u.user_name FROM dbo.Meetings m JOIN dbo.Users u ON m.user_id = u.user_id", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_members_meetings_func(req: func.HttpRequest, usersQuery: func.SqlRowList, meetingsQuery: func.SqlRowList) -> func.HttpResponse:
    return get_members_meetings(req, usersQuery, meetingsQuery)

# update_meeting_with_recording_funcエンドポイントを削除（録音情報更新機能）

# 基本情報取得エンドポイント
@app.function_name(name="GetBasicInfo")
@app.route(route="basicinfo/{meeting_id}", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="basicInfoQuery", 
    type="sql", 
    CommandText="SELECT * FROM dbo.BasicInfo", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_basic_info_func(req: func.HttpRequest, basicInfoQuery: func.SqlRowList) -> func.HttpResponse:
    return get_basic_info(req, basicInfoQuery)

# 基本情報検索エンドポイント
@app.function_name(name="SearchBasicInfo")
@app.route(route="basicinfo/search", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="basicInfoQuery", 
    type="sql", 
    CommandText="SELECT * FROM dbo.BasicInfo", 
    ConnectionStringSetting="SqlConnectionString"
)
def search_basic_info_func(req: func.HttpRequest, basicInfoQuery: func.SqlRowList) -> func.HttpResponse:
    return get_basic_info(req, basicInfoQuery, search_mode=True)
