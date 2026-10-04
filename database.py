"""
데이터베이스 설정 모듈 (Database Configuration)
SQLite 데이터베이스 연결 및 ORM 세션 팩토리를 구성합니다.
Vercel 서버리스 배포 환경(/tmp 파일시스템 및 외부 DATABASE_URL)을 자동 지원합니다.
"""
import os
import shutil
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Vercel 서버리스 환경 대응: 읽기 전용 파일시스템 우회
if os.environ.get("DATABASE_URL"):
    # 외부 Postgres 등 연결 (e.g. Neon, Supabase)
    db_url = os.environ.get("DATABASE_URL")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URL = db_url
    connect_args = {}
elif os.environ.get("VERCEL"):
    # Vercel 환경에서는 쓰기 가능한 /tmp 디렉토리로 SQLite 복사
    tmp_db = "/tmp/lccs.db"
    if not os.path.exists(tmp_db) and os.path.exists("./lccs.db"):
        shutil.copyfile("./lccs.db", tmp_db)
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{tmp_db}"
    connect_args = {"check_same_thread": False}
else:
    # 로컬 개발 환경
    SQLALCHEMY_DATABASE_URL = "sqlite:///./lccs.db"
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
