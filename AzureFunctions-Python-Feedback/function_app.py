import azure.functions as func
import logging
import json
from typing import Optional
from datetime import datetime
from azure.functions import AuthLevel, FunctionApp

# 独自のモジュールをインポート
# from src.comments import get_comments, add_comment, update_read_status
# from src.conversation import get_segments

app = func.FunctionApp(http_auth_level=AuthLevel.ANONYMOUS)

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

# 会話セグメント取得API
@app.function_name(name="GetConversationSegments")
@app.route(route="api/conversation/segments/{meeting_id}", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="segmentsQuery", 
    type="sql", 
    CommandText="SELECT s.segment_id, s.user_id, s.speaker_id, s.meeting_id, s.content, s.file_name, s.file_path, s.file_size, s.duration_seconds, s.status, s.inserted_datetime, s.updated_datetime, sp.speaker_name, sp.speaker_role FROM dbo.ConversationSegments s LEFT JOIN dbo.Speakers sp ON s.speaker_id = sp.speaker_id WHERE s.deleted_datetime IS NULL", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_conversation_segments(req: func.HttpRequest, segmentsQuery: func.SqlRowList) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            # CORS プリフライトリクエスト処理
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
            
        meeting_id = req.route_params.get('meeting_id')
        
        # データベースから会話セグメントを取得
        segments = []
        for row in segmentsQuery:
            if int(row['meeting_id']) == int(meeting_id):
                segments.append({
                    "segment_id": row['segment_id'],
                    "user_id": row['user_id'],
                    "speaker_id": row['speaker_id'],
                    "meeting_id": row['meeting_id'],
                    "content": row['content'],
                    "file_name": row['file_name'],
                    "file_path": row['file_path'],
                    "file_size": row['file_size'],
                    "duration_seconds": row['duration_seconds'],
                    "status": row['status'],
                    "inserted_datetime": row['inserted_datetime'].isoformat() if row['inserted_datetime'] else None,
                    "updated_datetime": row['updated_datetime'].isoformat() if row['updated_datetime'] else None,
                    "speaker_name": row['speaker_name'],
                    "speaker_role": row['speaker_role']
                })
        
        response = {
            "success": True,
            "message": f"会話セグメントを取得しました（meeting_id: {meeting_id}）",
            "segments": segments
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )
    except Exception as e:
        logging.error(f"セグメント取得中にエラーが発生しました: {str(e)}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"success": False, "message": f"エラー: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# コメント取得API
@app.function_name(name="GetComments")
@app.route(route="api/comments/{segment_id}", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="commentsQuery", 
    type="sql", 
    CommandText="SELECT c.comment_id, c.segment_id, c.meeting_id, c.user_id, c.content, c.inserted_datetime, c.updated_datetime, u.user_name FROM dbo.Comments c JOIN dbo.Users u ON c.user_id = u.user_id WHERE c.deleted_datetime IS NULL", 
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_input_binding(
    arg_name="commentReadsQuery", 
    type="sql", 
    CommandText="SELECT comment_id, reader_id, read_datetime FROM dbo.CommentReads", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_segment_comments(req: func.HttpRequest, commentsQuery: func.SqlRowList, commentReadsQuery: func.SqlRowList) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            # CORS プリフライトリクエスト処理
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
            
        segment_id = req.route_params.get('segment_id')
        
        # データベースからコメントを取得
        comments = []
        for row in commentsQuery:
            if int(row['segment_id']) == int(segment_id):
                # 既読情報を取得
                readers = []
                for read_row in commentReadsQuery:
                    if int(read_row['comment_id']) == int(row['comment_id']):
                        readers.append({
                            "reader_id": read_row['reader_id'],
                            "read_datetime": read_row['read_datetime'].isoformat() if read_row['read_datetime'] else None
                        })
                
                comments.append({
                    "comment_id": row['comment_id'],
                    "segment_id": row['segment_id'],
                    "meeting_id": row['meeting_id'],
                    "user_id": row['user_id'],
                    "user_name": row['user_name'],
                    "content": row['content'],
                    "inserted_datetime": row['inserted_datetime'].isoformat() if row['inserted_datetime'] else None,
                    "updated_datetime": row['updated_datetime'].isoformat() if row['updated_datetime'] else None,
                    "readers": readers
                })
        
        response = {
            "success": True,
            "message": f"コメントを取得しました（segment_id: {segment_id}）",
            "comments": comments
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False), 
            mimetype="application/json",
            status_code=200,
            headers=headers
        )
    except Exception as e:
        logging.error(f"コメント取得中にエラーが発生しました: {str(e)}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"success": False, "message": f"エラー: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# コメント追加API
@app.function_name(name="AddComment")
@app.route(route="api/comments", methods=["POST", "OPTIONS"])
@app.generic_input_binding(
    arg_name="lastCommentId", 
    type="sql", 
    CommandText="SELECT TOP 1 comment_id FROM dbo.Comments ORDER BY comment_id DESC", 
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_output_binding(
    arg_name="commentOut", 
    type="sql", 
    CommandText="dbo.Comments", 
    ConnectionStringSetting="SqlConnectionString"
)
def create_comment(req: func.HttpRequest, commentOut: func.Out[func.SqlRow], lastCommentId: func.SqlRowList) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            # CORS プリフライトリクエスト処理
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
            
        req_body = req.get_json()
        
        # リクエストのバリデーション
        segment_id = req_body.get('segment_id')
        meeting_id = req_body.get('meeting_id')
        user_id = req_body.get('user_id')
        content = req_body.get('content')
        
        if not all([segment_id, meeting_id, user_id, content]):
            headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
            return func.HttpResponse(
                json.dumps({"success": False, "message": "必須パラメータが不足しています"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400,
                headers=headers
            )
        
        # 新しいコメントIDを生成
        new_comment_id = 1
        for row in lastCommentId:
            new_comment_id = int(row['comment_id']) + 1
            break
        
        # 現在の日時
        now = datetime.now()
        
        # コメントをデータベースに挿入
        comment_row = func.SqlRow()
        comment_row["comment_id"] = new_comment_id
        comment_row["segment_id"] = segment_id
        comment_row["meeting_id"] = meeting_id
        comment_row["user_id"] = user_id
        comment_row["content"] = content
        comment_row["inserted_datetime"] = now
        comment_row["updated_datetime"] = now
        
        commentOut.set(comment_row)
        
        response = {
            "success": True,
            "message": "コメントが追加されました",
            "comment_id": new_comment_id
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=201,
            headers=headers
        )
    except Exception as e:
        logging.error(f"コメント追加中にエラーが発生しました: {str(e)}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"success": False, "message": f"エラー: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# コメント既読状態更新API
@app.function_name(name="MarkCommentAsRead")
@app.route(route="api/comments/read", methods=["POST", "OPTIONS"])
@app.generic_output_binding(
    arg_name="commentReadOut", 
    type="sql", 
    CommandText="dbo.CommentReads", 
    ConnectionStringSetting="SqlConnectionString"
)
def mark_comment_as_read(req: func.HttpRequest, commentReadOut: func.Out[func.SqlRow]) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            # CORS プリフライトリクエスト処理
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
            
        req_body = req.get_json()
        
        # リクエストのバリデーション
        comment_id = req_body.get('comment_id')
        user_id = req_body.get('user_id')
        
        if not all([comment_id, user_id]):
            headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
            return func.HttpResponse(
                json.dumps({"success": False, "message": "必須パラメータが不足しています"}, ensure_ascii=False),
                mimetype="application/json",
                status_code=400,
                headers=headers
            )
        
        # 現在の日時
        now = datetime.now()
        
        # 既読情報をデータベースに挿入
        comment_read_row = func.SqlRow()
        comment_read_row["comment_id"] = comment_id
        comment_read_row["reader_id"] = user_id
        comment_read_row["read_datetime"] = now
        
        commentReadOut.set(comment_read_row)
        
        response = {
            "success": True,
            "message": "コメントが既読としてマークされました"
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers=headers
        )
    except Exception as e:
        logging.error(f"コメント既読更新中にエラーが発生しました: {str(e)}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"success": False, "message": f"エラー: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        )

# 最新コメント取得API
@app.function_name(name="GetLatestComments")
@app.route(route="api/comments/latest", methods=["GET", "OPTIONS"])
@app.generic_input_binding(
    arg_name="commentsQuery", 
    type="sql", 
    CommandText="SELECT TOP 20 c.comment_id, c.segment_id, c.meeting_id, c.user_id, c.content, c.inserted_datetime, c.updated_datetime, u.user_name, m.client_company_name, m.client_contact_name FROM dbo.Comments c JOIN dbo.Users u ON c.user_id = u.user_id JOIN dbo.Meetings m ON c.meeting_id = m.meeting_id WHERE c.deleted_datetime IS NULL ORDER BY c.inserted_datetime DESC", 
    ConnectionStringSetting="SqlConnectionString"
)
@app.generic_input_binding(
    arg_name="commentReadsQuery", 
    type="sql", 
    CommandText="SELECT comment_id, reader_id, read_datetime FROM dbo.CommentReads", 
    ConnectionStringSetting="SqlConnectionString"
)
def get_latest_comments(req: func.HttpRequest, commentsQuery: func.SqlRowList, commentReadsQuery: func.SqlRowList) -> func.HttpResponse:
    try:
        if req.method == "OPTIONS":
            # CORS プリフライトリクエスト処理
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
            return func.HttpResponse(status_code=204, headers=headers)
            
        # クエリパラメータから値を取得
        user_id = req.params.get('userId', '1')  # デフォルト値1
        limit = int(req.params.get('limit', '5'))  # デフォルト値5
        
        # データベースから最新コメントを取得
        comments = []
        count = 0
        
        for row in commentsQuery:
            if count >= limit:
                break
                
            # 既読情報を取得
            is_read = False
            for read_row in commentReadsQuery:
                if int(read_row['comment_id']) == int(row['comment_id']) and int(read_row['reader_id']) == int(user_id):
                    is_read = True
                    break
            
            comments.append({
                "comment_id": row['comment_id'],
                "segment_id": row['segment_id'],
                "meeting_id": row['meeting_id'],
                "user_id": row['user_id'],
                "user_name": row['user_name'],
                "content": row['content'],
                "inserted_datetime": row['inserted_datetime'].isoformat() if row['inserted_datetime'] else None,
                "updated_datetime": row['updated_datetime'].isoformat() if row['updated_datetime'] else None,
                "client_company_name": row['client_company_name'],
                "client_contact_name": row['client_contact_name'],
                "isRead": is_read
            })
            count += 1
        
        response = {
            "success": True,
            "message": f"最新コメントを取得しました（limit: {limit}）",
            "comments": comments
        }
        
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps(response, ensure_ascii=False), 
            mimetype="application/json",
            status_code=200,
            headers=headers
        )
    except Exception as e:
        logging.error(f"最新コメント取得中にエラーが発生しました: {str(e)}")
        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        return func.HttpResponse(
            json.dumps({"success": False, "message": f"エラー: {str(e)}"}, ensure_ascii=False),
            mimetype="application/json",
            status_code=500,
            headers=headers
        ) 