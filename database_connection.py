import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    db_password = os.getenv("pass") or os.getenv("PASS") or os.getenv("DB_PASSWORD", "")

    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "gateway01.ap-northeast-1.prod.aws.tidbcloud.com"),
        port=int(os.getenv("DB_PORT", 4000)),
        user=os.getenv("DB_USER", "24hUSV88jwtA6TF.root"),
        password=db_password,
        database=os.getenv("DB_NAME", "aigym"),
        ssl_disabled=False
    )