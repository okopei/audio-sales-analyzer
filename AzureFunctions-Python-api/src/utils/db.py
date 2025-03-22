import os
import pyodbc
import logging
from datetime import datetime, UTC

def get_db_connection():
    """
    データベース接続文字列を環境変数から取得し、接続を返す
    """
    try:
        connection_string = os.environ.get('SqlConnectionString')
        if not connection_string:
            raise ValueError("SqlConnectionString environment variable is not set")
        
        # 接続文字列からドライバー情報を確認
        if "Driver=" not in connection_string and "driver=" not in connection_string:
            # ドライバーが指定されていない場合、適切なドライバーを追加
            if "windows" in os.name.lower():
                # Windows環境用のドライバー
                connection_string += ";Driver={ODBC Driver 17 for SQL Server}"
            else:
                # Linux/Mac環境用のドライバー
                connection_string += ";Driver={ODBC Driver 18 for SQL Server}"
        
        # 接続前にログに出力（パスワードを除く）
        safe_conn_string = mask_password(connection_string)
        logging.info(f"Attempting to connect with: {safe_conn_string}")
        
        # 接続を試行
        conn = pyodbc.connect(connection_string)
        logging.info("Database connection established successfully")
        return conn
    except pyodbc.Error as e:
        # pyODBCエラーの詳細を記録
        error_details = str(e).split('\n')
        state = error_details[0] if len(error_details) > 0 else "Unknown state"
        message = error_details[1] if len(error_details) > 1 else str(e)
        
        logging.error(f"Database connection error: {state} - {message}")
        logging.error(f"Connection string (masked): {safe_conn_string}")
        
        # 利用可能なドライバーを表示
        try:
            available_drivers = pyodbc.drivers()
            logging.info(f"Available ODBC drivers: {available_drivers}")
        except:
            logging.error("Failed to retrieve available ODBC drivers")
        
        # エラーを再スロー
        raise
    except Exception as e:
        logging.error(f"Unexpected error establishing database connection: {str(e)}")
        raise

def mask_password(connection_string):
    """
    接続文字列内のパスワードをマスクする
    """
    import re
    # Password=xxx または pwd=xxx パターンをマスク
    masked = re.sub(r'(Password|pwd)=([^;]*)', r'\1=***', connection_string, flags=re.IGNORECASE)
    return masked

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
        logging.error(f"Database query error: {str(e)}")
        logging.error(f"Query: {query}")
        if params:
            logging.error(f"Parameters: {params}")
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