"""
Vercel Serverless Function Entry Point
Vercel 배포 시 모든 라우트를 처리하는 ASGI 앱 진입점입니다.
"""
import sys
import os

# 프로젝트 루트 디렉토리를 sys.path 최상단에 추가하여 모듈 임포트 보장
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import app
