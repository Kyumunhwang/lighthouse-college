"""
스킬 비즈니스 로직 모듈 (Skills & Business Logic Components)
skills.md 명세에 따른 AuthSkill, ProfileSkill, ECSkill, CounselingSkill을 구현합니다.
"""
from typing import List, Dict, Any, Optional
import json
import re
import openpyxl
from sqlalchemy.orm import Session
from models import (
    User,
    Student,
    AcademicRecord,
    CourseGrade,
    ExtracurricularActivity,
    PassionProject,
    CounselingLog,
)


class AuthSkill:
    """사용자 인증 및 권한 관리 스킬"""

    @staticmethod
    def login_with_google(email: str, name: str, db: Session, picture_url: Optional[str] = None) -> User:
        """
        Google SSO 로그인 처리 및 세션 유저 객체 획득.
        존재하지 않는 유저는 자동 등록합니다.
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            role = "superuser" if email == "nahkyungsik@gmail.com" else "teacher"
            user = User(email=email, name=name, role=role, picture_url=picture_url)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    @staticmethod
    def assign_role(user_id: int, new_role: str, db: Session, student_id: Optional[str] = None) -> User:
        """사용자에게 특정 권한(superuser/teacher/student) 및 학생 학번을 부여합니다."""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.role = new_role
            if student_id:
                user.student_id = student_id
            db.commit()
            db.refresh(user)
        return user

    @staticmethod
    def verify_permission(user_role: str, required_role: str) -> bool:
        """요청된 작업에 대해 현재 사용자 역할이 부합하는지 검증합니다."""
        role_hierarchy = {"student": 1, "teacher": 2, "superuser": 3}
        return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)


class ProfileSkill:
    """학생 기본 및 누적 학업 레코드 관리 스킬"""

    @staticmethod
    def load_student_roster(excel_file_path: str, db: Session) -> int:
        """
        2026 Fall Semester LIS Student Roster 엑셀 파일을 읽어
        8학년~12학년(M8, H9, H10, H11, H12) 학생 데이터를 DB에 적재합니다.
        """
        wb = openpyxl.load_workbook(excel_file_path, data_only=True)
        ws = wb.worksheets[0]

        target_grades = {"M8", "H9", "H10", "H11", "H12"}
        current_grade = None
        current_homeroom = None
        inserted_count = 0

        for r in range(5, 155):
            val_b = str(ws.cell(r, 2).value or "").strip()
            val_c = str(ws.cell(r, 3).value or "").strip()

            for tg in ["M8", "H9", "H10", "H11", "H12"]:
                if val_b.startswith(tg):
                    current_grade = tg
                    if val_c:
                        current_homeroom = val_c
                    break

            if current_grade in target_grades:
                name_kr = ws.cell(r, 5).value
                name_en = ws.cell(r, 6).value
                eng_nickname = ws.cell(r, 7).value
                student_id = ws.cell(r, 8).value
                address = ws.cell(r, 10).value
                gender = ws.cell(r, 11).value
                grade_num = ws.cell(r, 12).value
                dob = ws.cell(r, 13).value
                email = ws.cell(r, 16).value or ws.cell(r, 17).value
                cell_student = ws.cell(r, 20).value
                cell_mother = ws.cell(r, 19).value
                cell_father = ws.cell(r, 18).value

                if student_id and name_kr and not any(k in str(name_kr) for k in ["Name", "Grade", "TOTAL", "Total"]):
                    sid_clean = str(student_id).strip()
                    existing = db.query(Student).filter(Student.student_id == sid_clean).first()
                    g_int = 8 if current_grade == "M8" else int(current_grade[1:])

                    if not existing:
                        student = Student(
                            student_id=sid_clean,
                            name_kr=str(name_kr).strip(),
                            name_en=str(name_en or "").strip(),
                            nickname=str(eng_nickname or "").strip(),
                            grade_code=current_grade,
                            grade=g_int,
                            homeroom=current_homeroom or "나경식 카운슬러",
                            gender=str(gender or "").strip() if gender else "M",
                            dob=str(dob or "").strip(),
                            address=str(address or "").strip(),
                            email=str(email or "").strip(),
                            phone=str(cell_student or cell_mother or cell_father or "").strip(),
                            common_app_id=f"CA-{sid_clean[-6:]}",
                            counselor_name="나경식 진학담당교사",
                            avatar_url=f"https://api.dicebear.com/7.x/adventurer/svg?seed={sid_clean}"
                        )
                        db.add(student)
                        inserted_count += 1

        db.commit()
        return inserted_count

    @staticmethod
    def get_academic_record(student_id: int, grade: int, db: Session) -> Optional[AcademicRecord]:
        """특정 학생의 특정 학년 GPA 및 학업 기록 조회"""
        return db.query(AcademicRecord).filter(
            AcademicRecord.student_id == student_id,
            AcademicRecord.grade == grade
        ).first()

    @staticmethod
    def update_academic_record(record_id: int, update_data: Dict[str, Any], db: Session) -> AcademicRecord:
        """학업 성적 및 지망 대학 정보 업데이트"""
        record = db.query(AcademicRecord).filter(AcademicRecord.id == record_id).first()
        if record:
            for key, value in update_data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            db.commit()
            db.refresh(record)
        return record


class ECSkill:
    """비교과 및 열정 프로젝트 관리 스킬"""

    @staticmethod
    def add_passion_project(student_id: int, project_data: Dict[str, Any], db: Session) -> PassionProject:
        """새로운 열정 프로젝트 타임라인 노드 및 프로젝트 추가"""
        project = PassionProject(
            student_id=student_id,
            title=project_data.get("title", "새로운 열정 프로젝트"),
            field=project_data.get("field", "융합 학술 연구"),
            summary=project_data.get("summary", ""),
            status=project_data.get("status", "In-Progress"),
            hours_total=project_data.get("hours_total", 50),
            timeline_json=project_data.get("timeline_json", "[]"),
            evidence_url=project_data.get("evidence_url", "")
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def render_drive_link(url: Optional[str], label: str = "증빙 확인") -> str:
        """
        Google Drive URL 텍스트를 안전한 `<a>` 태그 클립(📎) UI로 파싱 변환.
        url이 비어있으면 빈 문자열 또는 미등록 배지를 반환합니다.
        """
        if not url or not str(url).strip():
            return '<span class="text-on-surface-variant text-caption italic">미등록</span>'
        clean_url = str(url).strip()
        return (
            f'<a href="{clean_url}" target="_blank" rel="noopener noreferrer" '
            f'class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-surface-container text-secondary '
            f'hover:bg-secondary hover:text-on-secondary transition text-xs font-medium">'
            f'<span class="material-symbols-outlined text-[14px]">link</span> {label}</a>'
        )


class CounselingSkill:
    """인터랙티브 협업 상담 및 코멘트 기능 스킬"""

    @staticmethod
    def save_student_memo(student_id: int, notes: str, session_date: str, db: Session) -> CounselingLog:
        """학생 본인의 고민 및 상담 요청 내용 저장"""
        log = CounselingLog(
            student_id=student_id,
            session_date=session_date,
            student_notes=notes,
            counselor_feedback="",
            is_private=False
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def save_counselor_feedback(
        log_id: int,
        feedback: str,
        is_private: bool,
        db: Session,
        counselor_name: str = "나경식 진학선생님",
        action_items_json: Optional[str] = None
    ) -> CounselingLog:
        """Superuser의 상담 피드백 저장 및 Private 공개범위 토글 설정"""
        log = db.query(CounselingLog).filter(CounselingLog.id == log_id).first()
        if log:
            log.counselor_feedback = feedback
            log.is_private = is_private
            log.counselor_name = counselor_name
            if action_items_json is not None:
                log.action_items_json = action_items_json
            db.commit()
            db.refresh(log)
        return log

    @staticmethod
    def get_counseling_thread(student_id: int, current_user_role: str, db: Session) -> List[Dict[str, Any]]:
        """
        타임라인 렌더링 시 Role에 따라 Private 코멘트를 엄격하게 필터링(Data Masking)하여 반환합니다.
        Superuser가 아닌 경우(Student, Teacher) is_private=True인 피드백은
        '🔒 [비공개 전략 메모] 최고 카운슬러 권한(Superuser)에서만 열람 가능합니다.' 로 마스킹 처리됩니다.
        """
        logs = db.query(CounselingLog).filter(
            CounselingLog.student_id == student_id
        ).order_by(CounselingLog.created_at.desc()).all()

        results = []
        is_admin = (current_user_role == "superuser")

        for l in logs:
            action_items = []
            if l.action_items_json:
                try:
                    action_items = json.loads(l.action_items_json)
                except Exception:
                    action_items = []

            # RBAC Data Masking 로직
            if l.is_private and not is_admin:
                feedback_display = "🔒 [비공개 전략 메모] 최고 카운슬러 권한(Superuser)에서만 열람 가능합니다."
                private_indicator = True
            else:
                feedback_display = l.counselor_feedback or ""
                private_indicator = l.is_private

            results.append({
                "id": l.id,
                "session_date": l.session_date,
                "attendees": l.attendees,
                "student_notes": l.student_notes,
                "counselor_feedback": feedback_display,
                "is_private": private_indicator,
                "counselor_name": l.counselor_name,
                "action_items": action_items,
                "can_view_private": is_admin,
                "created_at": l.created_at.strftime("%Y-%m-%d %H:%M") if l.created_at else ""
            })

        return results
