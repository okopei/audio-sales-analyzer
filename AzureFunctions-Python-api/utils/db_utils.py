"""
データベース接続とクエリ実行の共通ユーティリティ
pypyodbc + MSI認証（Windows/Linux両対応）
"""

import logging
import os
import pypyodbc
import traceback
from typing import Optional, Dict, List, Any
from datetime import datetime, UTC

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # ログレベル強制設定

def get_db_connection():
    print("A: entering get_db_connection")

    server = os.getenv("SQL_SERVER")
    database = os.getenv("SQL_DATABASE")
    print(f"B: target = {server}/{database}")

    try:
        driver = '{ODBC Driver 18 for SQL Server}'
        auth = 'ActiveDirectoryMsi'
        
        connection_string = (
            'DRIVER=' + driver + ';'
            'Server=' + server + ';'
            'Database=' + database + ';'
            'Authentication=' + auth + ';'
        )
        print("C: created connection_string")

        conn = pypyodbc.connect(connection_string)
        print("D: connected")
        return conn

    except Exception as e:
        print("E: exception caught")
        print(f"Database connection error: {str(e)}")
        print(traceback.format_exc())

        logger.error(f"Database connection error: {str(e)}")
        logger.error(f"詳細トレース: {traceback.format_exc()}")
        raise

def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    SQLクエリを実行し、結果を返します。
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