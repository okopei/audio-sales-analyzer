import azure.functions as func
import logging
import uuid
from datetime import datetime
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.function_name(name="HttpTrigger1")
@app.route(route="http_trigger")
@app.generic_output_binding(arg_name="toDoItems", type="sql", CommandText="dbo.ToDo", ConnectionStringSetting="SqlConnectionString")
def http_trigger(req: func.HttpRequest, toDoItems: func.Out[func.SqlRow]) -> func.HttpResponse:
    logging.info('HTTP trigger function processed a request.')

    try:
        # JSONデータを取得
        req_body = req.get_json()
        title = req_body.get('title')
        url = req_body.get('url')
    except ValueError:
        return func.HttpResponse(
            "Invalid JSON data",
            status_code=400
        )

    if title and url:
        # SQLバインディングを使用してデータを挿入
        toDoItems.set(func.SqlRow({
            "Id": str(uuid.uuid4()),
            "order": None,
            "title": title,
            "url": url,
            "completed": False
        }))
        return func.HttpResponse(
            f"ToDo item '{title}' created successfully.",
            status_code=201
        )
    else:
        return func.HttpResponse(
            "Please provide 'title' and 'url' in the JSON body",
            status_code=400
        )
# 会議ハンドラーをインポート
from src.meetings.handlers import save_meeting_handler

# 会議保存エンドポイント
@app.function_name(name="SaveMeeting")
@app.route(route="meetings", methods=["POST", "OPTIONS"])
@app.generic_output_binding(
    arg_name="meetings", 
    type="sql", 
    CommandText="dbo.Meetings", 
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_input_binding(
    arg_name="lastMeeting", 
    type="sql", 
    CommandText="SELECT TOP 1 meeting_id FROM dbo.Meetings ORDER BY meeting_id DESC", 
    ConnectionStringSetting="SqlConnectionString"
)
def save_meeting(req: func.HttpRequest, meetings: func.Out[func.SqlRow], lastMeeting: func.SqlRowList) -> func.HttpResponse:
    return save_meeting_handler(req, meetings, lastMeeting)