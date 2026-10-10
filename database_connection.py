import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        db_password = os.getenv("pass") or os.getenv("PASS") or os.getenv("DB_PASSWORD", "")
        _pool = pooling.MySQLConnectionPool(
            pool_name="aigym_tidb_pool",
            pool_size=5,
            pool_reset_session=True,
            host=os.getenv("DB_HOST", "gateway01.ap-northeast-1.prod.aws.tidbcloud.com"),
            port=int(os.getenv("DB_PORT", 4000)),
            user=os.getenv("DB_USER", "24hUSV88jwtA6TF.root"),
            password=db_password,
            database=os.getenv("DB_NAME", "aigym"),
            ssl_disabled=False
        )
    return _pool

def get_db_connection():
    """Retrieve an active connection from the pool, or fallback to fresh connection."""
    try:
        pool = _get_pool()
        conn = pool.get_connection()
        if conn.is_connected():
            return conn
    except Exception:
        pass

    # Fallback to direct connection if pool fails or is exhausted
    db_password = os.getenv("pass") or os.getenv("PASS") or os.getenv("DB_PASSWORD", "")
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "gateway01.ap-northeast-1.prod.aws.tidbcloud.com"),
        port=int(os.getenv("DB_PORT", 4000)),
        user=os.getenv("DB_USER", "24hUSV88jwtA6TF.root"),
        password=db_password,
        database=os.getenv("DB_NAME", "aigym"),
        ssl_disabled=False
    )