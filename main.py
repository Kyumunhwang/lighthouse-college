"""
등대글로벌스쿨 진학 지도 카운슬러 포털 시스템 (LCS - Lighthouse College System)
메인 애플리케이션 진입점 및 라우트 핸들러 모듈
"""
import os
import json
from typing import Optional, List
from fastapi import FastAPI, Request, Depends, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import engine, get_db, Base
from models import (
    User,
    Student,
    AcademicRecord,
    CourseGrade,
    ExtracurricularActivity,
    PassionProject,
    CounselingLog,
)
from auth import (
    get_current_user,
    require_superuser,
    require_teacher_or_above,
    SUPERUSER_EMAIL,
)
from skills import ProfileSkill, ECSkill, CounselingSkill

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 데이터베이스 테이블 안전 초기화
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database schema init notice: {e}")

app = FastAPI(
    title="Lighthouse College System (LCS)",
    description="등대글로벌스쿨 진학 지도 및 누적 포트폴리오 관리 포털",
    version="1.0.0"
)

# 세션 미들웨어 등록 (세션 기반 Google SSO 상태 및 RBAC 역할 유지)
app.add_middleware(SessionMiddleware, secret_key="lighthouse-college-secret-key-2026")

# 템플릿 엔진 설정 (다중 경로 탐색 보장)
possible_template_dirs = [
    os.path.join(BASE_DIR, "templates"),
    os.path.abspath("templates"),
    os.path.join(os.getcwd(), "templates"),
]
templates_dir = next((d for d in possible_template_dirs if os.path.isdir(d)), os.path.join(BASE_DIR, "templates"))
templates = Jinja2Templates(directory=templates_dir)

# 디자인 정적 에셋 마운트 (있는 경우)
design_dir = os.path.join(BASE_DIR, "design")
if os.path.exists(design_dir):
    app.mount("/design", StaticFiles(directory=design_dir), name="design")


def get_global_stats(db: Session) -> dict:
    """대시보드 및 통계 공통 지표 산출 함수"""
    total_students = db.query(Student).count()
    count_m8 = db.query(Student).filter(Student.grade_code == "M8").count()
    count_h9 = db.query(Student).filter(Student.grade_code == "H9").count()
    count_h10 = db.query(Student).filter(Student.grade_code == "H10").count()
    count_h11 = db.query(Student).filter(Student.grade_code == "H11").count()
    count_h12 = db.query(Student).filter(Student.grade_code == "H12").count()
    total_counselings = db.query(CounselingLog).count()
    total_passion_projects = db.query(PassionProject).count()
    total_ecs = db.query(ExtracurricularActivity).count()

    return {
        "total_students": total_students,
        "count_m8": count_m8,
        "count_h9": count_h9,
        "count_h10": count_h10,
        "count_h11": count_h11,
        "count_h12": count_h12,
        "total_counselings": total_counselings,
        "total_passion_projects": total_passion_projects,
        "total_ecs": total_ecs,
    }


# ==========================================================
# 1. 대시보드 뷰 (Dashboard View)
# ==========================================================
@app.get("/", response_class=HTMLResponse)
async def dashboard_view(
    request: Request,
    grade: str = "ALL",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    진학포털 메인 대시보드 뷰
    학년별 통계 지표, 재학생 목록, 최근 상담 기록을 렌더링합니다.
    """
    stats = get_global_stats(db)

    # 학년별 필터링
    query = db.query(Student)
    if grade != "ALL":
        query = query.filter(Student.grade_code == grade)
    students = query.order_by(Student.grade.desc(), Student.name_kr.asc()).all()

    # 최근 상담 기록 조회 (최대 5건)
    recent_logs = db.query(CounselingLog).order_by(CounselingLog.created_at.desc()).limit(6).all()
    
    # RBAC Data Masking 적용
    masked_recent = []
    is_admin = (current_user.role == "superuser")
    for log in recent_logs:
        feedback = log.counselor_feedback
        if log.is_private and not is_admin:
            feedback = "🔒 [비공개 전략 메모] 카운슬러 전용 메모입니다."
        masked_recent.append({
            "student": log.student,
            "session_date": log.session_date,
            "counselor_name": log.counselor_name,
            "is_private": log.is_private,
            "counselor_feedback": feedback,
            "student_notes": log.student_notes
        })

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "current_user": current_user,
            "stats": stats,
            "students": students,
            "current_grade": grade,
            "recent_counselings": masked_recent,
            "active_nav": "dashboard",
            "selected_student_id": "LGS-220814"
        }
    )


# ==========================================================
# 2. 학생 관리 디렉토리 뷰 (Students Directory)
# ==========================================================
@app.get("/students", response_class=HTMLResponse)
async def students_directory_view(
    request: Request,
    grade: str = "ALL",
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    학생 관리 디렉토리 뷰
    학년별 필터링 및 이름/학번 검색 기능을 제공합니다.
    """
    query = db.query(Student)

    if grade != "ALL":
        query = query.filter(Student.grade_code == grade)

    if q and q.strip():
        search_term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Student.name_kr.ilike(search_term),
                Student.name_en.ilike(search_term),
                Student.nickname.ilike(search_term),
                Student.student_id.ilike(search_term)
            )
        )

    students = query.order_by(Student.grade.desc(), Student.name_kr.asc()).all()
    all_count = db.query(Student).count()

    return templates.TemplateResponse(
        request=request,
        name="students_directory.html",
        context={
            "current_user": current_user,
            "students": students,
            "all_count": all_count,
            "current_grade": grade,
            "search_query": q or "",
            "active_nav": "students",
            "selected_student_id": "LGS-220814"
        }
    )


# ==========================================================
# 3. 학업 및 성적 상세 뷰 (Academic & GPA)
# ==========================================================
@app.get("/students/{student_id}/academic", response_class=HTMLResponse)
async def student_academic_view(
    request: Request,
    student_id: str,
    grade: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    학생 개별 학업 및 GPA 성적 상세 뷰
    8~12학년 탭별 누적 성적, 이수 과목 및 공인 시험 점수를 렌더링합니다.
    """
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")

    # 탭으로 선택된 학년 (기본값: 학생 현재 학년)
    target_grade = grade if grade is not None else student.grade

    # 해당 학년 AcademicRecord 조회
    active_record = db.query(AcademicRecord).filter(
        AcademicRecord.student_id == student.id,
        AcademicRecord.grade == target_grade
    ).first()

    courses = []
    if active_record:
        courses = db.query(CourseGrade).filter(
            CourseGrade.academic_record_id == active_record.id
        ).all()

    return templates.TemplateResponse(
        request=request,
        name="student_detail.html",
        context={
            "current_user": current_user,
            "student": student,
            "selected_grade": target_grade,
            "active_record": active_record,
            "courses": courses,
            "active_nav": "academic",
            "selected_student_id": student.student_id
        }
    )


@app.post("/api/students/{student_id_num}/academic")
async def update_student_academic(
    student_id_num: int,
    grade: int = Query(...),
    gpa_unweighted: float = Form(4.0),
    gpa_weighted: float = Form(4.0),
    sat_total: Optional[int] = Form(None),
    sat_rw: Optional[int] = Form(None),
    sat_math: Optional[int] = Form(None),
    target_uni_1: Optional[str] = Form(None),
    transcript_url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser)
):
    """
    학업 레코드 수정 API (Superuser 전용)
    """
    student = db.query(Student).filter(Student.id == student_id_num).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")

    record = db.query(AcademicRecord).filter(
        AcademicRecord.student_id == student.id,
        AcademicRecord.grade == grade
    ).first()

    if not record:
        record = AcademicRecord(
            student_id=student.id,
            grade=grade,
            semester=f"Grade {grade}"
        )
        db.add(record)

    record.gpa_unweighted = gpa_unweighted
    record.gpa_weighted = gpa_weighted
    record.sat_total = sat_total
    record.sat_rw = sat_rw
    record.sat_math = sat_math
    record.target_uni_1 = target_uni_1
    record.transcript_url = transcript_url

    db.commit()
    return RedirectResponse(
        url=f"/students/{student.student_id}/academic?grade={grade}",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ==========================================================
# 4. 비교과 & 열정프로젝트 뷰 (ECs & Passion Projects)
# ==========================================================
@app.get("/students/{student_id}/ecs", response_class=HTMLResponse)
async def student_ecs_view(
    request: Request,
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    비교과 활동 및 열정 프로젝트 상세 뷰
    타임라인형 연구 프로젝트 및 6개 카테고리 비교과 활동을 렌더링합니다.
    """
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")

    passion_projects = db.query(PassionProject).filter(
        PassionProject.student_id == student.id
    ).all()

    # 타임라인 JSON 파싱
    for pp in passion_projects:
        try:
            pp.parsed_timeline = json.loads(pp.timeline_json or "[]")
        except Exception:
            pp.parsed_timeline = []

    extracurriculars = db.query(ExtracurricularActivity).filter(
        ExtracurricularActivity.student_id == student.id
    ).all()

    verified_proofs_count = sum(1 for ec in extracurriculars if ec.evidence_url)
    total_hours = sum(int(ec.hours_per_week * ec.weeks_per_year) for ec in extracurriculars)

    return templates.TemplateResponse(
        request=request,
        name="passion_projects.html",
        context={
            "current_user": current_user,
            "student": student,
            "passion_projects": passion_projects,
            "extracurriculars": extracurriculars,
            "verified_proofs_count": verified_proofs_count,
            "total_hours": total_hours,
            "active_nav": "ecs",
            "selected_student_id": student.student_id
        }
    )


@app.post("/api/students/{student_id_num}/ecs")
async def add_student_ec(
    student_id_num: int,
    category: str = Form(...),
    grade_levels: str = Form("11"),
    title: str = Form(...),
    organization: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    hours_per_week: float = Form(3.0),
    weeks_per_year: float = Form(30.0),
    description: Optional[str] = Form(None),
    evidence_url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser)
):
    """
    신규 비교과 활동 추가 API (Superuser 전용)
    """
    student = db.query(Student).filter(Student.id == student_id_num).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")

    ec = ExtracurricularActivity(
        student_id=student.id,
        category=category,
        grade_levels=grade_levels,
        title=title,
        organization=organization,
        role=role,
        hours_per_week=hours_per_week,
        weeks_per_year=weeks_per_year,
        description=description,
        evidence_url=evidence_url
    )
    db.add(ec)
    db.commit()

    return RedirectResponse(
        url=f"/students/{student.student_id}/ecs",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ==========================================================
# 5. 인터랙티브 상담 뷰 (Interactive Counseling & RBAC)
# ==========================================================
@app.get("/students/{student_id}/counseling", response_class=HTMLResponse)
async def student_counseling_view(
    request: Request,
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    인터랙티브 상담 뷰
    상단 [학생 영역] / 하단 [카운슬러 영역] 분할 및 RBAC 비공개 메모 마스킹을 적용합니다.
    """
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")

    # CounselingSkill을 통한 권한별 Data Masking 적용 조회
    threads = CounselingSkill.get_counseling_thread(
        student_id=student.id,
        current_user_role=current_user.role,
        db=db
    )

    return templates.TemplateResponse(
        request=request,
        name="counseling.html",
        context={
            "current_user": current_user,
            "student": student,
            "counseling_threads": threads,
            "active_nav": "counseling",
            "selected_student_id": student.student_id
        }
    )


@app.post("/api/students/{student_id_num}/counseling")
async def create_counseling_log(
    student_id_num: int,
    session_date: str = Form(...),
    attendees: Optional[str] = Form(None),
    student_notes: Optional[str] = Form(None),
    counselor_feedback: Optional[str] = Form(None),
    is_private: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    상담 기록 작성 및 수정 처리 API
    - 학생: 본인 학생 고민 작성 가능
    - Superuser: 카운슬러 피드백 및 Private 메모 토글 가능
    """
    student = db.query(Student).filter(Student.id == student_id_num).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")

    is_private_bool = (is_private == "true") if current_user.is_superuser else False
    feedback_text = counselor_feedback if current_user.is_superuser else ""

    log = CounselingLog(
        student_id=student.id,
        counselor_name=current_user.name if current_user.is_superuser else "나경식 진학담당교사",
        session_date=session_date,
        attendees=attendees,
        student_notes=student_notes or "",
        counselor_feedback=feedback_text,
        is_private=is_private_bool,
        action_items_json=json.dumps(["목표 대학 입시 요강 분석", "에세이 1차 아웃라인 준비"], ensure_ascii=False)
    )
    db.add(log)
    db.commit()

    return RedirectResponse(
        url=f"/students/{student.student_id}/counseling",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ==========================================================
# 6. 통계 및 원서 현황 (College Board)
# ==========================================================
@app.get("/statistics", response_class=HTMLResponse)
async def statistics_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    통계 및 원서 현황 집계 뷰
    """
    stats = get_global_stats(db)
    return templates.TemplateResponse(
        request=request,
        name="statistics.html",
        context={
            "current_user": current_user,
            "stats": stats,
            "active_nav": "statistics",
            "selected_student_id": "LGS-220814"
        }
    )


# ==========================================================
# 7. 신규 학생 등록 API (Superuser 전용)
# ==========================================================
@app.post("/api/students")
async def create_student(
    name_kr: str = Form(...),
    name_en: Optional[str] = Form(None),
    student_id: str = Form(...),
    grade_code: str = Form(...),
    email: Optional[str] = Form(None),
    target_uni: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser)
):
    """
    신규 진학 대상 학생 등록 API (Superuser 전용)
    """
    existing = db.query(Student).filter(Student.student_id == student_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 등록된 학번입니다.")

    g_num = 8 if grade_code == "M8" else int(grade_code[1:])
    student = Student(
        student_id=student_id,
        name_kr=name_kr,
        name_en=name_en or "",
        nickname=name_en or "",
        grade_code=grade_code,
        grade=g_num,
        homeroom="나경식 진학담당교사",
        email=email or f"{student_id.lower()}@lighthouse.edu",
        common_app_id=f"CA-{student_id[-6:]}",
        avatar_url=f"https://api.dicebear.com/7.x/adventurer/svg?seed={student_id}"
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    # 기본 1지망 학업 레코드 생성
    if target_uni:
        rec = AcademicRecord(
            student_id=student.id,
            grade=g_num,
            semester=f"Grade {g_num}",
            target_uni_1=target_uni,
            target_major_1="General Studies"
        )
        db.add(rec)
        db.commit()

    return RedirectResponse(url=f"/students/{student.student_id}/academic", status_code=status.HTTP_303_SEE_OTHER)


# ==========================================================
# 8. 역할 전환 시뮬레이터 API (RBAC Live Testing)
# ==========================================================
@app.get("/api/switch-role")
async def switch_role(
    role: str = Query(..., pattern="^(superuser|teacher|student)$"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    개발 및 시연 목적 원클릭 역할 전환 API (Google SSO 계정 스위칭 시뮬레이션)
    - superuser: nahkyungsik@gmail.com
    - teacher: teacher@lighthouse.edu
    - student: chloe.kim@lgs.ac.kr (김서윤 학생)
    """
    role_email_map = {
        "superuser": SUPERUSER_EMAIL,
        "teacher": "teacher@lighthouse.edu",
        "student": "chloe.kim@lgs.ac.kr"
    }

    target_email = role_email_map.get(role, SUPERUSER_EMAIL)
    request.session["user_email"] = target_email

    # 직전 페이지(Referer)로 리다이렉트
    referer = request.headers.get("referer") or "/"
    return RedirectResponse(url=referer, status_code=status.HTTP_303_SEE_OTHER)


if __name__ == "__main__":
    import uvicorn
    # 고유 포트 3008번으로 실행
    uvicorn.run("main:app", host="0.0.0.0", port=3008, reload=True)
