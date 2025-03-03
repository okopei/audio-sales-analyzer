import os
import pyodbc
import logging
from datetime import datetime, UTC

def get_db_connection():
    """
    データベース接続文字列を環境変数から取得し、接続を返す
    """
    connection_string = os.environ.get('SqlConnectionString')
    if not connection_string:
        raise ValueError("SqlConnectionString environment variable is not set")
    return pyodbc.connect(connection_string)

def execute_query(query, params=None):
    """
    SQLクエリを実行し、結果を返す汎用関数
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # SELECT文の場合は結果を返す
        if query.strip().upper().startswith('SELECT'):
            columns = [column[0] for column in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        
        # INSERT/UPDATE/DELETEの場合はコミットして影響を受けた行数を返す
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        logging.error(f"Database error: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_current_time():
    """
    現在時刻をUTCで取得し、SQLサーバー互換の形式で返す
    """
    return datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S') 