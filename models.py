"""
데이터베이스 ORM 모델 정의 모듈 (Database Models)
학생, 학업 성취도, 비교과 활동, 열정 프로젝트 및 상담 기록 테이블을 정의합니다.
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    """
    사용자 계정 모델 (Superuser / Teacher / Student)
    Google SSO 인증 기반 계정 정보와 역할을 관리합니다.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(50), default="student", nullable=False)  # 'superuser', 'teacher', 'student'
    student_id = Column(String(50), nullable=True)  # 학생 계정인 경우 매핑되는 학번
    picture_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def is_superuser(self) -> bool:
        """최고 관리자(나경식 카운슬러) 여부 확인"""
        return self.role == "superuser"

    @property
    def is_teacher(self) -> bool:
        """일반 교사 여부 확인"""
        return self.role == "teacher"

    @property
    def is_student(self) -> bool:
        """학생 본인 여부 확인"""
        return self.role == "student"


class Student(Base):
    """
    학생 기본 프로필 모델
    2026 Fall Semester LIS Roster 기반 학생 정보와 기본 메타데이터를 저장합니다.
    """
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), unique=True, index=True, nullable=False)  # 예: 2020S0101
    name_kr = Column(String(100), nullable=False)
    name_en = Column(String(100), nullable=True)
    nickname = Column(String(100), nullable=True)
    grade_code = Column(String(20), nullable=False)  # M8, H9, H10, H11, H12
    grade = Column(Integer, nullable=False)  # 8, 9, 10, 11, 12
    homeroom = Column(String(100), nullable=True)  # 담임 교사 이름
    gender = Column(String(10), nullable=True)  # M, F
    dob = Column(String(50), nullable=True)  # YYYY.MM.DD
    address = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(100), nullable=True)
    common_app_id = Column(String(50), nullable=True)
    counselor_name = Column(String(100), default="나경식 진학선생님")
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 1:N 관계 정의
    academic_records = relationship("AcademicRecord", back_populates="student", cascade="all, delete-orphan")
    extracurriculars = relationship("ExtracurricularActivity", back_populates="student", cascade="all, delete-orphan")
    passion_projects = relationship("PassionProject", back_populates="student", cascade="all, delete-orphan")
    counseling_logs = relationship("CounselingLog", back_populates="student", cascade="all, delete-orphan")


class AcademicRecord(Base):
    """
    누적 학업 및 성적 레코드 모델 (8~12학년 개별 관리)
    학년별 GPA, 지망 대학/전공, 공인시험 성적, 성적표 드라이브 링크를 보관합니다.
    """
    __tablename__ = "academic_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    grade = Column(Integer, nullable=False)  # 8, 9, 10, 11, 12
    semester = Column(String(50), nullable=True)  # e.g., '2025-2026 Academic Year'
    gpa_unweighted = Column(Float, default=4.0)
    gpa_weighted = Column(Float, default=4.0)
    class_rank = Column(String(50), nullable=True)  # e.g., 'Top 5%'
    target_uni_1 = Column(String(200), nullable=True)
    target_major_1 = Column(String(200), nullable=True)
    target_uni_2 = Column(String(200), nullable=True)
    target_major_2 = Column(String(200), nullable=True)
    target_uni_3 = Column(String(200), nullable=True)
    target_major_3 = Column(String(200), nullable=True)
    sat_rw = Column(Integer, nullable=True)
    sat_math = Column(Integer, nullable=True)
    sat_total = Column(Integer, nullable=True)
    act_composite = Column(Integer, nullable=True)
    toefl_total = Column(Integer, nullable=True)
    transcript_url = Column(String(500), nullable=True)  # Google Drive URL
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("Student", back_populates="academic_records")
    courses = relationship("CourseGrade", back_populates="academic_record", cascade="all, delete-orphan")


class CourseGrade(Base):
    """
    수강 과목 및 성적 세부 내역 모델
    각 학년별 세부 수강 과목명, 분류(AP, Honors, Regular), 학점 및 성적을 관리합니다.
    """
    __tablename__ = "course_grades"

    id = Column(Integer, primary_key=True, index=True)
    academic_record_id = Column(Integer, ForeignKey("academic_records.id"), nullable=False, index=True)
    course_name = Column(String(200), nullable=False)
    category = Column(String(50), default="Regular")  # AP, Honors, Regular, Dual Enrollment
    credits = Column(Float, default=1.0)
    grade_letter = Column(String(10), default="A")  # A+, A, A-, B+, etc.
    grade_point = Column(Float, default=4.0)

    academic_record = relationship("AcademicRecord", back_populates="courses")


class ExtracurricularActivity(Base):
    """
    비교과 활동 모델 (Extracurricular Activity)
    리더십, 클럽, 스포츠, 봉사, 학술 연구, 예술 등 6개 분류 활동과 Google Drive 증빙 링크를 저장합니다.
    """
    __tablename__ = "extracurricular_activities"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    category = Column(String(100), nullable=False)  # Leadership, Clubs, Sports, Volunteer, Academic, Arts
    title = Column(String(200), nullable=False)
    organization = Column(String(200), nullable=True)
    role = Column(String(100), nullable=True)
    grade_levels = Column(String(50), default="9, 10, 11")  # 참여 학년
    hours_per_week = Column(Float, default=3.0)
    weeks_per_year = Column(Float, default=30.0)
    description = Column(Text, nullable=True)
    evidence_url = Column(String(500), nullable=True)  # Google Drive 증빙 링크
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="extracurriculars")


class PassionProject(Base):
    """
    열정 프로젝트 모델 (Passion Project)
    장기 심층 프로젝트의 타임라인, 진행 단계, 연구 요약 및 산출물 드라이브 링크를 관리합니다.
    """
    __tablename__ = "passion_projects"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    field = Column(String(100), nullable=True)  # 생명공학, 인공지능, 공공정책 등
    summary = Column(Text, nullable=True)
    status = Column(String(50), default="In-Progress")  # In-Progress, Completed, Planning
    hours_total = Column(Integer, default=100)
    timeline_json = Column(Text, nullable=True)  # JSON 형태의 단계별 타임라인
    evidence_url = Column(String(500), nullable=True)  # Google Drive 연구 논문/포트폴리오 링크
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="passion_projects")


class CounselingLog(Base):
    """
    인터랙티브 상담 기록 모델 (Counseling Log)
    상단 학생 고민/상담 요청 메모와 하단 카운슬러 전략 피드백을 저장하며,
    is_private 플래그를 통한 RBAC 데이터 마스킹을 엄격히 지원합니다.
    """
    __tablename__ = "counseling_logs"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    counselor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    counselor_name = Column(String(100), default="나경식 진학선생님")
    session_date = Column(String(50), nullable=False)  # YYYY. MM. DD (요일) HH:MM
    attendees = Column(String(255), nullable=True)  # 김서윤(학생), 나경식(카운슬러), 모(학부모)
    student_notes = Column(Text, nullable=True)  # 학생 작성 영역 (고민 및 질문)
    counselor_feedback = Column(Text, nullable=True)  # 카운슬러 피드백 및 전략 제언
    is_private = Column(Boolean, default=False)  # 카운슬러 비공개 메모 토글 (RBAC 필터 대상)
    action_items_json = Column(Text, nullable=True)  # 차주 액션 아이템 리스트 (JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("Student", back_populates="counseling_logs")
    counselor = relationship("User")
