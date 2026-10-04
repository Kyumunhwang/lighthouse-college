"""
인증 및 인가 모듈 (Authentication & RBAC Authorization)
Google SSO 로그인 시뮬레이션 및 역할 기반 접근 제어(RBAC) 데코레이터와 헬퍼 함수를 정의합니다.
"""
from typing import Optional
from fastapi import Request, HTTPException, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, Student

# 기본 최고 관리자 이메일 상수 (PRD 명시)
SUPERUSER_EMAIL = "nahkyungsik@gmail.com"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    HTTP 세션 또는 쿠키에서 현재 인증된 사용자를 조회합니다.
    세션에 사용자 정보가 없을 경우 기본 데모 최고관리자(나경식 선생님)를 반환하여
    개발 및 시연 시 원활한 흐름을 제공합니다.
    """
    user_email = request.session.get("user_email")
    if not user_email:
        # 기본 데모 유저는 최고관리자 계정으로 조회
        user_email = SUPERUSER_EMAIL

    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        # 사용자 레코드가 없는 경우 자동 생성 (Google SSO 첫 로그인 대응)
        role = "superuser" if user_email == SUPERUSER_EMAIL else "teacher"
        user = User(
            email=user_email,
            name="나경식 진학선생님" if role == "superuser" else "일반 교사",
            role=role,
            picture_url="https://lh3.googleusercontent.com/aida-public/AB6AXuAeq9vXS3xhSiBY940BMUu6lWeovw9qD_3D0dla70Fq7-We28dGLrwqxK8rL_nyBfp_tKWgKqwmu_MhvBKY37N_2t1Ay5I7lmI0h-suG-7pd_kHKjcOYeMFfgbxxzbVQCKzRo4H5HfuwR96od4bXk1jHrTghD3nJL3EnzkO12mp377OHUTd-pMi0vxp9kMi_s55MwIS-XOLhPqyiONAfqqbHaUzUg0FcSS-RZBSP-X3nv7_Vr9uNaoahg"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """
    최고 관리자(Superuser) 권한 요구 의존성
    권한이 없을 경우 HTTP 403 Forbidden 예외를 발생시킵니다.
    """
    if current_user.role != "superuser":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="최고 관리자(Superuser) 전용 작업입니다. 권한이 필요합니다."
        )
    return current_user


def require_teacher_or_above(current_user: User = Depends(get_current_user)) -> User:
    """
    교사 이상(Teacher or Superuser) 권한 요구 의존성
    """
    if current_user.role not in ["superuser", "teacher"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교사 이상 등급만 접근 가능한 작업입니다."
        )
    return current_user


def check_student_access(student_id: int, current_user: User, db: Session) -> bool:
    """
    학생 유저가 요청된 학생 정보에 접근 가능한지 검증합니다.
    - Superuser / Teacher: 모든 학생 접근 가능
    - Student: 본인 학번(student_id)만 접근 가능
    """
    if current_user.role in ["superuser", "teacher"]:
        return True
    if current_user.role == "student" and current_user.student_id:
        target_student = db.query(Student).filter(Student.id == student_id).first()
        return target_student is not None and target_student.student_id == current_user.student_id
    return False
