"""
데이터베이스 초기화 및 Seed 적재 스크립트 (Database Seeder)
LIS 학생 Roster 엑셀 파일(8~12학년)을 파싱하여 기본 사용자, 학생 프로필,
누적 성적, 비교과 활동, 열정 프로젝트 및 상담 기록을 생성합니다.
"""
import os
import json
from database import engine, SessionLocal, Base
from models import (
    User,
    Student,
    AcademicRecord,
    CourseGrade,
    ExtracurricularActivity,
    PassionProject,
    CounselingLog,
)
from skills import ProfileSkill

ROSTER_FILE = "2026 Fall Semester LIS Student Roster.xlsx"


def init_database():
    """테이블 스키마 생성 및 초기 Seed 데이터 적재"""
    print(">>> Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. 초기 사용자(User) 셋업
        print(">>> Setting up default user accounts...")
        # 1) 최고 관리자 (나경식 진학선생님)
        admin = db.query(User).filter(User.email == "nahkyungsik@gmail.com").first()
        if not admin:
            admin = User(
                email="nahkyungsik@gmail.com",
                name="나경식 진학담당교사",
                role="superuser",
                picture_url="https://lh3.googleusercontent.com/aida-public/AB6AXuAeq9vXS3xhSiBY940BMUu6lWeovw9qD_3D0dla70Fq7-We28dGLrwqxK8rL_nyBfp_tKWgKqwmu_MhvBKY37N_2t1Ay5I7lmI0h-suG-7pd_kHKjcOYeMFfgbxxzbVQCKzRo4H5HfuwR96od4bXk1jHrTghD3nJL3EnzkO12mp377OHUTd-pMi0vxp9kMi_s55MwIS-XOLhPqyiONAfqqbHaUzUg0FcSS-RZBSP-X3nv7_Vr9uNaoahg"
            )
            db.add(admin)

        # 2) 일반 교사
        teacher = db.query(User).filter(User.email == "teacher@lighthouse.edu").first()
        if not teacher:
            teacher = User(
                email="teacher@lighthouse.edu",
                name="박지혜 교과교사",
                role="teacher",
                picture_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=256&q=80"
            )
            db.add(teacher)

        db.commit()

        # 2. 엑셀 학생 Roster 적재 (M8, H9, H10, H11, H12)
        if os.path.exists(ROSTER_FILE):
            print(f">>> Parsing Excel Roster: {ROSTER_FILE}...")
            count = ProfileSkill.load_student_roster(ROSTER_FILE, db)
            print(f">>> Successfully loaded {count} target students into DB.")
        else:
            print(f"!!! Warning: Roster file {ROSTER_FILE} not found.")

        # 3. 디자인 템플릿의 대표 학생(김서윤 Chloe Kim) 생성/확인
        # 만약 Roster에 없거나 디자인 뷰와 100% 매칭을 위해 김서윤을 11학년 대표 학생으로 지정
        chloe = db.query(Student).filter(Student.student_id == "LGS-220814").first()
        if not chloe:
            chloe = Student(
                student_id="LGS-220814",
                name_kr="김서윤",
                name_en="Chloe Kim",
                nickname="Chloe",
                grade_code="H11",
                grade=11,
                homeroom="박지혜 수석교사",
                gender="F",
                dob="2008.04.19",
                address="대한민국 서울특별시 강남구 대치동",
                email="chloe.kim@lgs.ac.kr",
                phone="010-8921-4320",
                common_app_id="CA-984210",
                counselor_name="나경식 진학담당교사",
                avatar_url="https://lh3.googleusercontent.com/aida-public/AB6AXuCuw2Wz8lURzpiJD2JSRnau1Q8ZJvtpxBnRk7mQoozouMqu4Z5rAdllvy8g68Q08n1qtbChS5z8_RQAzyzla-_ssXuOCJC4941XQvlZrcHuMK0RFBCYaIKtzvSSzNCIGpWvrAk6cqpzko6HbTxCI1Yrza8X4GX1dcg-3A2InD3GEoKk7bB4MSc3udPkX7tbwrYEmjSO2YT4TM249vordNzW49h-vxtcFH2qVTrgMfERk3awKLY5rrO08Q"
            )
            db.add(chloe)
            db.commit()
            db.refresh(chloe)

        # 학생 계정(김서윤) User 추가
        student_user = db.query(User).filter(User.email == "chloe.kim@lgs.ac.kr").first()
        if not student_user:
            student_user = User(
                email="chloe.kim@lgs.ac.kr",
                name="김서윤 (Chloe Kim)",
                role="student",
                student_id=chloe.student_id,
                picture_url=chloe.avatar_url
            )
            db.add(student_user)
            db.commit()

        # 4. 김서윤 학생 및 주요 학생들에게 학업 레코드 및 더미 데이터 보강
        target_students = [chloe]
        # Roster에서 첫 5명 학생도 기본 레코드 생성
        other_students = db.query(Student).filter(Student.id != chloe.id).limit(6).all()
        target_students.extend(other_students)

        for s in target_students:
            # 8~11(또는 12)학년 누적 학업 레코드 확인 및 추가
            for g in range(8, s.grade + 1):
                existing_rec = db.query(AcademicRecord).filter(
                    AcademicRecord.student_id == s.id,
                    AcademicRecord.grade == g
                ).first()
                if not existing_rec:
                    rec = AcademicRecord(
                        student_id=s.id,
                        grade=g,
                        semester=f"Grade {g} (202{g-5}-202{g-4})",
                        gpa_unweighted=3.92 if g < 11 else 3.96,
                        gpa_weighted=4.15 if g < 10 else 4.42,
                        class_rank="Top 3%",
                        target_uni_1="Johns Hopkins University",
                        target_major_1="Biomedical Engineering (BME)",
                        target_uni_2="Cornell University",
                        target_major_2="Biological Sciences",
                        target_uni_3="Northwestern University",
                        target_major_3="Pre-Med / Biology",
                        sat_rw=750,
                        sat_math=790,
                        sat_total=1540,
                        act_composite=35,
                        toefl_total=116,
                        transcript_url="https://drive.google.com/file/d/1official_transcript_chloekim_pdf/view"
                    )
                    db.add(rec)
                    db.commit()
                    db.refresh(rec)

                    # 과목 성적 추가
                    courses = [
                        ("AP Biology", "AP", 1.0, "A+", 4.3),
                        ("AP Chemistry", "AP", 1.0, "A", 4.0),
                        ("AP Calculus BC", "AP", 1.0, "A+", 4.3),
                        ("AP English Language", "AP", 1.0, "A", 4.0),
                        ("World History", "Regular", 1.0, "A", 4.0),
                        ("Academic Research Seminars", "Honors", 1.0, "A+", 4.3),
                    ]
                    for c_name, c_cat, c_cr, c_let, c_gp in courses:
                        c_grade = CourseGrade(
                            academic_record_id=rec.id,
                            course_name=c_name,
                            category=c_cat,
                            credits=c_cr,
                            grade_letter=c_let,
                            grade_point=c_gp
                        )
                        db.add(c_grade)
                    db.commit()

            # 비교과 활동 추가 (6개 카테고리)
            if not db.query(ExtracurricularActivity).filter(ExtracurricularActivity.student_id == s.id).first():
                ecs = [
                    (
                        "Leadership",
                        "바이오메디컬 융합 동아리 (BioTech Horizons)",
                        "LGS 고등부 학술연합",
                        "설립자 & 대표 (President)",
                        "10, 11",
                        4.0,
                        32.0,
                        "생명공학 최신 저널 리뷰 및 고등학생 대상 유전자 가위 세미나 주최 (회원 35명)",
                        "https://drive.google.com/drive/folders/1biotech_club_leadership_portfolio"
                    ),
                    (
                        "Clubs",
                        "등대 모의유엔 (LGS Model UN Secretariat)",
                        "MUN Society",
                        "의장단 (Head Delegate)",
                        "9, 10, 11",
                        3.5,
                        28.0,
                        "WHO 위원회 수석의장 역임, 글로벌 팬데믹 방역 조약 결의안 공동 발의",
                        "https://drive.google.com/file/d/1mun_who_resolution_awards/view"
                    ),
                    (
                        "Academic",
                        "서울대 의대 의과학 연구실 인턴십",
                        "SNU College of Medicine Lab",
                        "학생 연구 보조 (Student Intern)",
                        "10, 11",
                        6.0,
                        8.0,
                        "CRISPR-Cas9 표적 이탈 변이 분석 알고리즘 파이프라인 데이터 검증 참여",
                        "https://drive.google.com/file/d/1snu_lab_internship_certificate/view"
                    ),
                    (
                        "Volunteer",
                        "소아암 환우 학습 멘토링 봉사단 (Light & Hope)",
                        "한국백혈병어린이재단",
                        "팀장 (Team Lead)",
                        "9, 10, 11",
                        3.0,
                        40.0,
                        "병원학교 온라인 과학 실험 키트 기획 및 누적 120시간 일대일 멘토링 지도",
                        "https://drive.google.com/drive/folders/1volunteer_light_hope_hours"
                    ),
                    (
                        "Sports",
                        "LGS 대표 배구부 (Varsity Volleyball)",
                        "KAIAC Conference",
                        "주전 세터 (Starting Setter)",
                        "9, 10",
                        5.0,
                        16.0,
                        "춘계 외국인학교 토너먼트 준우승 견인, 스포츠맨십 상 수상",
                        "https://drive.google.com/file/d/1kaiac_volleyball_roster_award/view"
                    ),
                    (
                        "Arts",
                        "과학 일러스트 및 메디컬 인포그래픽 프로젝트",
                        "Science Visual Media Lab",
                        "크리에이티브 디렉터",
                        "10, 11",
                        2.5,
                        20.0,
                        "희귀 유전 질환 인식 개선 카드뉴스 및 웹 인포그래픽 15편 제작 배포",
                        "https://drive.google.com/drive/folders/1medical_infographics_art"
                    )
                ]
                for cat, title, org, role, grs, hpw, wpy, desc, url in ecs:
                    act = ExtracurricularActivity(
                        student_id=s.id,
                        category=cat,
                        title=title,
                        organization=org,
                        role=role,
                        grade_levels=grs,
                        hours_per_week=hpw,
                        weeks_per_year=wpy,
                        description=desc,
                        evidence_url=url
                    )
                    db.add(act)
                db.commit()

            # 열정 프로젝트 (Passion Project) 추가
            if not db.query(PassionProject).filter(PassionProject.student_id == s.id).first():
                timeline_data = [
                    {
                        "step": "1단계: 선행 문헌 고찰 및 연구 가설 수립",
                        "period": "2024.03 ~ 2024.05",
                        "detail": "PubMed 및 bioRxiv 기반 45편의 메디컬 논문 분석, 비침습적 바이오센서 효용성 검토 완료",
                        "doc_url": "https://drive.google.com/file/d/1passion_lit_review_pdf/view"
                    },
                    {
                        "step": "2단계: 아두이노 기반 프로토타입 회로 설계 및 센서 테스팅",
                        "period": "2024.06 ~ 2024.09",
                        "detail": "광학 심박 및 산소포화도 센서 캘리브레이션, 3D 프린팅 하우징 제작",
                        "doc_url": "https://drive.google.com/file/d/1prototype_schematic_drive/view"
                    },
                    {
                        "step": "3단계: 데이터 수집 및 머신러닝 이상 징후 감지 모델",
                        "period": "2024.10 ~ 2025.01",
                        "detail": "정상군/비정상 파형 분류 Random Forest 알고리즘 정확도 94.2% 달성",
                        "doc_url": "https://drive.google.com/file/d/1ml_model_benchmark_data/view"
                    },
                    {
                        "step": "4단계: 고등학생 청소년 학술대회(ISEF Regional) 논문 제출",
                        "period": "2025.02 ~ 진행 중",
                        "detail": "Final Draft 영문 에세이 최종 감수 및 포스터 세션 발표 준비 중",
                        "doc_url": "https://drive.google.com/file/d/1final_manuscript_draft_pdf/view"
                    }
                ]
                pp = PassionProject(
                    student_id=s.id,
                    title="저비용 웨어러블 바이오센서를 활용한 청소년 부정맥 조기 스크리닝 시스템 연구",
                    field="바이오메디컬 엔지니어링 & 헬스케어 AI",
                    summary="의료 취약계층 청소년을 위한 휴대용 부정맥 모니터링 디바이스 프로토타입 제작 및 생체 신호 분석 연구",
                    status="In-Progress",
                    hours_total=240,
                    timeline_json=json.dumps(timeline_data, ensure_ascii=False),
                    evidence_url="https://drive.google.com/drive/folders/1chloe_passion_project_master"
                )
                db.add(pp)
                db.commit()

            # 상담 기록 (Counseling Logs) 추가 (Public 1건, Private 1건 - RBAC 검증용)
            if not db.query(CounselingLog).filter(CounselingLog.student_id == s.id).first():
                # 1) 일반 공개 상담 기록
                c1 = CounselingLog(
                    student_id=s.id,
                    counselor_name="나경식 진학담당교사",
                    session_date="2025. 02. 20 (목) 15:30",
                    attendees=f"{s.name_kr}(학생), 나경식(카운슬러), 모(학부모)",
                    student_notes="존스홉킨스 BME 1지망(ED) 지원 전략과 3월 SAT 점수 목표(1560+) 달성을 위한 학습 플랜에 대해 자문을 구하고 싶습니다. AP Chem 점수 유지에 약간의 부담감이 있습니다.",
                    counselor_feedback="현재 Unweighted GPA 3.96과 SAT 1540은 매우 경쟁력 있는 구간입니다. BME 지원 시 연구 실적(열정 프로젝트 논문)을 주무기로 삼아 커먼앱 메인 에세이와 Supplement 소재를 일치시키는 Holistic 어필이 유효합니다.",
                    is_private=False,
                    action_items_json=json.dumps([
                        "3월 Digital SAT 모의고사 1560점대 안정화",
                        "열정 프로젝트 4단계 최종 논문 영문 교정 완료",
                        "존스홉킨스 BME 교수진 최근 연구 논문 2편 요약 작성"
                    ], ensure_ascii=False)
                )
                db.add(c1)

                # 2) 카운슬러 전용 비공개(Private) 전략 메모
                c2 = CounselingLog(
                    student_id=s.id,
                    counselor_name="나경식 진학담당교사",
                    session_date="2025. 02. 22 (토) 10:00 (전략 회의)",
                    attendees="나경식(카운슬러 내부 메모)",
                    student_notes="",
                    counselor_feedback="[내부 비공개 입시 전략] 존스홉킨스 ED 지원이 유력하나, 코넬 RD 합격 가능성이 더 높음. 여름방학 중 코넬 의대 연계 서머스쿨 추천서(교장선생님 친필) 작성 필요. 가정환경 및 재정보조(CSS Profile) 신청 여부는 부모님과 별도 비공개 면담 요망.",
                    is_private=True,
                    action_items_json=json.dumps([
                        "코넬대 입학사정관 네트워크 사전 컨택 확인",
                        "재정 보조 지원 가이드라인 검토"
                    ], ensure_ascii=False)
                )
                db.add(c2)
                db.commit()

        print(">>> Database seeding completed successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
