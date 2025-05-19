import logging
import pyodbc
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC
from azure.identity import DefaultAzureCredential, ClientSecretCredential
import os
import struct

logger = logging.getLogger(__name__)

def get_db_connection():
    """データベース接続を確立する"""
    try:
        # 利用可能なODBCドライバ一覧をログ出力
        logger.info(f"利用可能なODBCドライバ: {pyodbc.drivers()}")
        
        # ローカル開発環境の場合
        if not os.environ.get('WEBSITE_SITE_NAME'):  # ローカル環境ではこの環境変数が存在しない
            # 環境変数から認証情報を取得
            tenant_id = os.environ.get('TENANT_ID')
            client_id = os.environ.get('CLIENT_ID')
            client_secret = os.environ.get('CLIENT_SECRET')
            
            if all([tenant_id, client_id, client_secret]):
                credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret
                )
            else:
                credential = DefaultAzureCredential()
        else:
            # 本番環境の場合
            credential = DefaultAzureCredential()

        token = credential.get_token("https://database.windows.net/.default")
        # アクセストークンの有効期限をログ出力
        logger.info(f"アクセストークンの有効期限 (UTC): {token.expires_on}")
        
        # トークンをバイト列に変換
        token_bytes = bytes(token.token, 'utf-8')
        exptoken = b''.join(bytes((b, 0)) for b in token_bytes)
        access_token = struct.pack('=i', len(exptoken)) + exptoken
        
        # 接続文字列をf-stringで明示的に構築
        conn_str = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:w-paas-salesanalyzer-sqlserver.database.windows.net,1433;"
            f"Database=w-paas-salesanalyzer-sql;"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
        
        logger.info("データベース接続を試行します...")
        logger.info(f"接続文字列: {conn_str}")  # デバッグ用に接続文字列を出力
        conn = pyodbc.connect(conn_str, attrs_before={1256: access_token})
        logger.info("データベース接続が確立されました")
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        logger.error(f"Connection string: {conn_str}")
        raise

def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """SQLクエリを実行し、結果を返す"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        if cursor.description:
            columns = [column[0] for column in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        else:
            conn.commit()
            return []
            
    except Exception as e:
        logger.error(f"Query execution error: {str(e)}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def get_current_time():
    """現在のUTC時刻を取得"""
    return datetime.now(UTC) 