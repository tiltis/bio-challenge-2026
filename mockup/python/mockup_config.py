# -*- coding: utf-8 -*-
"""
LinkCure(링큐어) 앱 목업 : 편집 설정 파일
=========================================
이 파일의 값만 고치고 build_mockup.py 를 실행하면
수정 내용이 반영된 목업 HTML이 새로 만들어집니다.

실행 방법 (PyCharm: 초록 실행 버튼 / VS Code·터미널):
    python build_mockup.py
"""

# ── 전체 설정 ──────────────────────────────────────────────
TITLE = "LinkCure(링큐어) · 사회복지사용 사례관리 앱 목업"
WHITE_BACKGROUND = False   # True 로 바꾸면 인쇄용 흰 배경으로 생성
OUTPUT_FILE = "LinkCure_목업.html"   # 생성될 파일 이름

# ── 상단 리본(제목 배너) ───────────────────────────────────
RIBBON = "LinkCure"
RIBBON_SUB = "Linking Discharge to Continuous Care"
DECK = (
    "정신질환 퇴원환자의 <b>사후관리 취약도</b>를 퇴원요약지로 산출해, 의료사회복지사가<br>"
    "<b>우선 개입할 환자</b>를 확인하고 <b>복약·생활지도를 쉬운 말로</b> 전달하는 모바일 화면"
)

# ── 폰 ① 메인(홈) 화면 ────────────────────────────────────
HOSPITAL_KR = "경북대학교병원"
HOSPITAL_EN = "KYUNGPOOK NATIONAL UNIV. HOSPITAL"
ROLE_CHIP = "의료사회복지사<br>진성현"

# 컬러 타일 3개 : color 는 b(파랑)/r(빨강)/g(초록)
TILES = [
    {"label": "오늘 관리<br>대상",  "value": "8", "unit": "명", "color": "b"},
    {"label": "신규<br>관리취약",   "value": "3", "unit": "명", "color": "r"},
    {"label": "센터 연계<br>대기",  "value": "5", "unit": "명", "color": "g"},
]

HOME_TABS = ["홈", "담당 환자", "연계 현황", "통계"]   # 첫 번째가 선택 상태

# 아이콘 그리드 9칸 : icon 은 build_mockup.py 의 ICONS 목록 참고
# badge 에 숫자를 넣으면 빨간 알림 동그라미가 붙음 (없으면 None)
GRID = [
    {"label": "담당 환자<br>목록", "icon": "patients", "badge": "8"},
    {"label": "관리취약도<br>조회", "icon": "pulse",    "badge": None},
    {"label": "복약지도<br>해석",  "icon": "pill",     "badge": None},
    {"label": "생활지도<br>해석",  "icon": "home",     "badge": None},
    {"label": "센터<br>연계",      "icon": "share",    "badge": None},
    {"label": "상담<br>기록",      "icon": "chat",     "badge": None},
    {"label": "방문<br>일정",      "icon": "calendar", "badge": None},
    {"label": "알림",              "icon": "bell",     "badge": "2"},
    {"label": "설정",              "icon": "gear",     "badge": None},
]

# 개인정보 안내 카드
PRIVACY_TITLE = "개인정보 처리 · 사전 동의 안내"
PRIVACY_BADGE = "퇴원 시 사전 동의 완료"
PRIVACY_ITEMS = [
    ("사전 동의 기반", "퇴원 절차에서 환자(정보주체)의 사전 동의를 받은 뒤에만 관리취약도를 분석합니다."),
    ("병원 내부 처리", "진료기록(EMR) 원본은 병원 밖으로 나가지 않습니다."),
    ("산출 근거", "관리취약도는 퇴원요약지와 동의 시 추가 문진 항목으로만 산출합니다."),
    ("최소 전송", "관리취약도 결과와 사례관리 요약만 정신건강복지센터로 전달됩니다."),
    ("보관 후 파기", "사례관리 종료 후 보관기간이 지나면 안전하게 파기됩니다."),
]
PRIVACY_AGREE = "본인은 위 처리 방침에 동의합니다"

# ── 폰 ② 환자 관리 화면 ───────────────────────────────────
PHONE2_TITLE = "담당 환자 목록"

# 상단 요약 4칸 : tone 은 ""(검정)/"hi"(빨강)/"lo"(초록)
SUMMARY = [
    {"value": "32", "label": "담당 전체", "tone": ""},
    {"value": "8",  "label": "관리취약",  "tone": "hi"},
    {"value": "24", "label": "관리일반",  "tone": "lo"},
    {"value": "5",  "label": "연계 진행", "tone": ""},
]

CHIPS = ["관리취약", "전체", "관리일반", "신규", "의료급여"]   # 첫 번째가 선택 상태

# 환자 카드 목록
#   risk      : "hi"(관리취약·빨강) 또는 "lo"(관리일반·초록)
#   insurance : ("med", "의료급여 1종") 또는 ("hb", "건강보험")
#   tags      : 자유롭게 추가·삭제
PATIENTS = [
    {"name": "김○○", "meta": "54 · 남 · 조현병",   "risk": "hi",
     "insurance": ("med", "의료급여 1종"), "tags": ["독거", "복약 불규칙", "외래 미방문"], "dday": "퇴원 D+9"},
    {"name": "이○○", "meta": "41 · 여 · 양극성장애", "risk": "hi",
     "insurance": ("med", "의료급여 2종"), "tags": ["보호자 부재", "과거 치료중단"], "dday": "퇴원 D+3"},
    {"name": "박○○", "meta": "37 · 남 · 우울장애",  "risk": "lo",
     "insurance": ("hb", "건강보험"), "tags": ["보호자 동거", "복약 양호"], "dday": "퇴원 D+14"},
    {"name": "정○○", "meta": "29 · 여 · 불안장애",  "risk": "lo",
     "insurance": ("hb", "건강보험"), "tags": ["외래 규칙적"], "dday": "퇴원 D+22"},
]

# ── 폰 ③ 복약·생활지도 화면 ───────────────────────────────
PHONE3_TITLE = "복약·생활지도 해석"
PT_NAME = "김○○"
PT_AVATAR = "김"          # 동그라미 안 글자
PT_META = "54 · 조현병 · 의료급여 1종"
PT_RISK = "hi"            # "hi" 또는 "lo"

MED_SECTION_TITLE = "복약지도, 쉽게 풀어드려요"
MED_ORIGINAL = "Olanzapine 10mg 1T qd HS<br>Paliperidone LAI 100mg IM q4wk"
MED_PLAIN = (
    "<b>올란자핀</b>은 마음을 안정시키는 약이에요. <b>매일 잠자기 전 1알</b> 드세요. "
    "<b>팔리페리돈 주사</b>는 <b>4주에 한 번</b> 맞아 효과가 유지됩니다. 다음 예약일을 꼭 지켜 주세요."
)
MED_WARNING = "임의로 끊으면 증상이 재발할 수 있어요. 끊거나 줄일 땐 꼭 의료진과 상의하세요."

LIFE_SECTION_TITLE = "생활지도, 이렇게 챙겨요"
# icon 은 calendar_check / moon / bell / share 중 선택
LIFE_ITEMS = [
    {"icon": "calendar_check", "title": "외래 예약 지키기",
     "desc": "퇴원 2주 안에 정신건강의학과 외래를 꼭 방문하세요. 방문이 늦어지면 재발 위험이 커집니다."},
    {"icon": "moon", "title": "규칙적인 수면·생활",
     "desc": "매일 비슷한 시간에 자고 일어나세요. 밤낮이 바뀌면 증상이 나빠질 수 있어요."},
    {"icon": "bell", "title": "재발 신호 알아두기",
     "desc": "불면·불안·환청이 다시 생기면 다음 예약을 기다리지 말고 바로 연락하세요."},
    {"icon": "share", "title": "정신건강복지센터 연계",
     "desc": "독거·의료급여 대상이라 지역 센터의 사례관리 연결을 권합니다(동의 시 진행)."},
]

GUARD_TEXT = ("이 해석은 기존 퇴원 문서를 <b>쉽게 풀어 설명</b>한 것으로, "
              "<b>진단·처방을 바꾸지 않습니다</b>. 최종 판단은 전문가가 합니다.")
BUTTON_PRIMARY = "환자에게 전달하기"
BUTTON_GHOST = "인쇄"

# ── 폰 아래 캡션 3개 ──────────────────────────────────────
CAPTIONS = [
    {"n": "1", "title": "메인화면 · 오늘의 사례관리",
     "desc": "담당 현황(개입 대상·신규 관리취약·연계 대기)과<br>주요 기능을 한눈에"},
    {"n": "2", "title": "환자 관리 · 관리취약도 &amp; 의료보험",
     "desc": '<b style="color:#e24a4e">관리취약</b>/<b style="color:#0f9d8f">관리일반</b> 배지와 건강보험·의료급여를<br>한눈에: 관리 대상 우선 확인'},
    {"n": "3", "title": "복약·생활지도 · AI 쉬운 해석",
     "desc": "어려운 처방·생활수칙을 쉬운 말로 바꿔<br>환자에게 전달 (RAG 근거 기반·가드레일)"},
]

# ── 페이지 맨 아래 각주 ────────────────────────────────────
FOOT = ("LinkCure: 사회복지사용 사례관리 앱 개념 시안<br>"
        "화면·인물·수치는 <b>예시</b>이며 실제 환자 데이터가 아닙니다")
