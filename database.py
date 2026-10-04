"""
데이터베이스 설정 모듈 (Database Configuration)
SQLite 데이터베이스 연결 및 ORM 세션 팩토리를 구성합니다.
Vercel/AWS Lambda 서버리스 환경(/tmp)과 로컬 환경을 모두 완벽 지원합니다.
"""
import os
import shutil
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Vercel, AWS Lambda, 또는 읽기 전용 샌드박스 환경 감지
is_serverless = (
    any(os.environ.get(k) for k in [
        "VERCEL", "VERCEL_ENV", "NOW_REGION",
        "AWS_LAMBDA_FUNCTION_NAME", "LAMBDA_TASK_ROOT"
    ])
    or not os.access(BASE_DIR, os.W_OK)
)

if os.environ.get("DATABASE_URL"):
    # 외부 Postgres 등 연결 (e.g. Neon, Supabase)
    db_url = os.environ.get("DATABASE_URL")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URL = db_url
    connect_args = {}
elif is_serverless:
    # Vercel 환경에서는 쓰기 가능한 임시 디렉토리(/tmp)로 SQLite DB 복사
    tmp_dir = tempfile.gettempdir()
    tmp_db = os.path.join(tmp_dir, "lccs.db")
    possible_local_dbs = [
        os.path.join(BASE_DIR, "lccs.db"),
        os.path.abspath("lccs.db"),
        os.path.join(os.getcwd(), "lccs.db"),
    ]
    local_db = next((p for p in possible_local_dbs if os.path.exists(p)), None)
    try:
        if not os.path.exists(tmp_db) and local_db:
            shutil.copyfile(local_db, tmp_db)
    except Exception as e:
        print(f"Warning copying SQLite to temp: {e}")
    
    norm_path = tmp_db.replace("\\", "/")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{norm_path}"
    connect_args = {"check_same_thread": False}
else:
    # 로컬 개발 환경
    local_path = os.path.join(BASE_DIR, "lccs.db").replace("\\", "/")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{local_path}"
    connect_args = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    요청 단위 데이터베이스 세션을 생성하고 종료하는 제너레이터 함수.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
