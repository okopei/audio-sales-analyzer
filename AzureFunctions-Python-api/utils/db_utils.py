"""
データベース接続とクエリ実行の共通ユーティリティ
"""

import logging
import pyodbc
import struct
from typing import Optional, Dict, List, Any
from datetime import datetime, UTC
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

def get_db_connection():
    """
    Entra ID認証を使用してAzure SQL Databaseに接続する
    ODBC Driver 17 for SQL Serverを使用
    """
    try:
        # Microsoft Entra ID認証のトークンを取得
        credential = DefaultAzureCredential()
        token = credential.get_token("https://database.windows.net/.default")
        
        # トークンをバイナリ形式に変換
        token_bytes = bytes(token.token, 'utf-8')
        exptoken = b''.join(bytes((b, 0)) for b in token_bytes)
        access_token = struct.pack('=i', len(exptoken)) + exptoken
        
        # 接続文字列の構築
        conn_str = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:w-paas-salesanalyzer-sqlserver.database.windows.net,1433;"
            f"Database=w-paas-salesanalyzer-sql;"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
        
        logger.info("Connecting to database with ODBC Driver 17 for SQL Server")
        conn = pyodbc.connect(conn_str, attrs_before={1256: access_token})
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        logger.error(f"Connection string (masked): {conn_str.replace('w-paas-salesanalyzer-sqlserver.database.windows.net', '***').replace('w-paas-salesanalyzer-sql', '***')}")
        raise

def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    SQLクエリを実行し、結果を返します。
    
    Args:
        query (str): 実行するSQLクエリ
        params (Optional[Dict[str, Any]]): クエリパラメータ
        
    Returns:
        List[Dict[str, Any]]: クエリ結果のリスト
    """
    try:
        with get_db_connection() as conn:
            logger.info(f"クエリを実行: {query}")
            if params:
                logger.info(f"パラメータ: {params}")
            
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith("SELECT"):
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                results = [dict(zip(columns, row)) for row in rows]

                # datetime → 文字列化
                for row in results:
                    for key, value in row.items():
                        if hasattr(value, 'isoformat'):
                            row[key] = value.isoformat()

                return results
            else:
                conn.commit()
                return []
                
    except Exception as e:
        logger.error(f"クエリ実行エラー: {str(e)}")
        raise

def test_db_connection() -> bool:
    """
    データベース接続をテストします。
    
    Returns:
        bool: 接続テストの結果
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            logger.info(f"SQL Server バージョン: {version}")
            return True
    except Exception as e:
        logger.error(f"接続テストエラー: {str(e)}")
        return False

def get_current_time():
    """
    現在時刻をUTCで取得し、SQLサーバー互換の形式で返す
    """
    return datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S') 