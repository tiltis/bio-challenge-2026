"""
app.py : AI 기반 Two-Track Care Coordination Platform (데모 대시보드)
정신질환 퇴원환자의 치료중단·재입원 위험을 예측하고, Two-Track으로 개입을 연계한다.
2026 연구 아이디어 기술사업화 챌린지 · 경북대학교병원 팀

설계 철학(신청서 일치):
- 진단하지 않는다. EMR 기반 '치료중단/재입원 위험 신호'와 Track 배정만 제공(규제 안전).
- 핵심기술 ① XGBoost+SHAP 위험예측 엔진(설명가능 AI)
- 핵심기술 ② RAG 기반 LLM 건강 문해력 지원(Track 1)
- 예측에서 끝내지 않고 Track 2 → 의료사회복지사 컨설트 → 정신건강복지센터 연계로 '개입의 고리'를 닫는다.

문헌 근거(피처 설계·모델 선택·성능 기준):
- Donisi et al., BMC Psychiatry 2016 (정신과 재입원 예측인자 체계적 문헌고찰
  : '과거 입원력'이 가장 일관된 예측인자)
- Morel et al., Int J Med Inform 2020 (정신·물질사용장애 30일 재입원 XGBoost,
  AUROC 0.738 : 과거입원·의료이용·퇴원형태·진단·동반질환이 상위 피처)
- McCoy & Perlis 그룹, Transl Psychiatry 2021 (정신과 재입원 예측 난이도,
  인구학 기반 AUC ~0.68)
- Ren et al., JMIR Ment Health 2025 (기관 간 모델 이식성 한계
  : 병원별 site-specific 학습 필요 → 본 설계의 온프레미스 재학습 근거)

실행: streamlit run app.py
요구사항: streamlit >= 1.37 (use_container_width API : 설치본 1.37.1 호환),
          .streamlit/config.toml 에 [server] enableStaticServing = true
          (아리따 부리 폰트 static/fonts 정적 서빙용 : 없으면 시스템 serif 폴백)
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio

# ---------------------------------------------------------------- 색 팔레트
# 화이트/블랙/그레이 + 포인트=하늘(클린 블루) + 강조=클린 레드. 채도·대비를 정돈.
INK      = "#101828"   # 제목·강한 텍스트 (거의 검정)
BODY     = "#344054"   # 본문 텍스트 (진회색)
MUTED    = "#667085"   # 캡션·보조 (회색)
BORDER   = "#e4e7ec"   # 경계선 (연회색)
SURFACE  = "#f9fafb"   # 카드/보조 배경 (아주 연한 회색)
APP_BG   = "#f5f7fa"   # 페이지 배경 (쿨 라이트 그레이)
SKY      = "#2e90fa"   # 포인트(클린 블루)
SKY_DK   = "#1570ef"   # 진한 블루
SKY_LT   = "#84caff"   # 연블루
SKY_BG   = "#eff8ff"   # 블루 틴트 배경
SKY_BD   = "#b2ddff"   # 블루 경계
CYAN     = "#53b1fd"   # 보조 블루
VERM     = "#f04438"   # 강조(클린 레드)
ORANGE   = "#f79009"   # 경고(앰버)
DANGER   = "#f04438"   # 위험(레드)
RED_DK   = "#d92d20"   # 최고 위험(진레드)
PINK     = "#f6a6c6"   # 연핑크(배지 테두리)
PINK_BG  = "#fff5f9"   # 연핑크 틴트 배경

# Plotly 차트 전역 기본 폰트 = 아리따 부리 + 라이트 톤 (브라우저 @font-face로 렌더).
_ARITA = "AritaBuri, serif"
for _t in ("plotly", "plotly_white", "plotly_dark"):
    _tl = pio.templates[_t].layout
    _tl.font.family = _ARITA
    _tl.font.color = BODY

from data_generator import (generate, FEATURE_LABELS, FEATURE_GROUPS,
                            FEATURE_COLS, NUMERIC_COLS, BINARY_COLS, DIAGNOSES)
from pipeline import (train_and_score, compute_shap, global_importance,
                      patient_shap, compare_models, assign_band,
                      band_description, RISK_BANDS, BAND_COLORS,
                      TRACK2_THRESHOLD, TRACK_COLORS)
from rag_literacy import build_document, plain_rewrite
import drug_api
from real_data import (load_uci, train_and_score_uci, uci_global_importance,
                       FEATURE_MAPPING)

# 라이트 테마용 색 오버라이드 (Track 1=하늘, Track 2=주홍)
TRACK_COLORS = {"Track 1": SKY, "Track 2": DANGER}
# 밴드 배지(흰 글자 채움) : WCAG 대비 확보를 위해 어두운 톤으로 에스컬레이션.
# (기존 #f79009·#f2762e 는 흰 글자와 대비 2.2~2.6:1로 가독성 미달 → 교체)
BAND_COLORS = {"낮음": SKY_DK, "중간": "#b54708",
               "높음": "#c4320a", "매우높음": "#912018"}

st.set_page_config(page_title="Two-Track Care Coordination",
                   page_icon="🏥", layout="wide")

# ---------------------------------------------------------------- 스타일
st.markdown(f"""
<style>
  /* ---- 아리따 부리 (아모레퍼시픽 나눔글꼴, 세리프) : 정적 서빙 static/fonts ---- */
  @font-face {{ font-family:'AritaBuri'; font-weight:500; font-style:normal;
    src:url('app/static/fonts/AritaBuriKR-Medium.ttf') format('truetype'); font-display:swap; }}
  @font-face {{ font-family:'AritaBuri'; font-weight:600; font-style:normal;
    src:url('app/static/fonts/AritaBuriKR-SemiBold.ttf') format('truetype'); font-display:swap; }}
  @font-face {{ font-family:'AritaBuri'; font-weight:700; font-style:normal;
    src:url('app/static/fonts/AritaBuriKR-Bold.ttf') format('truetype'); font-display:swap; }}

  /* 전체를 아리따 부리로 통일 */
  html, body, .stApp, [class*="css"],
  p, span, label, div, li, td, th, input, textarea, select, button, code {{
    font-family:'AritaBuri',serif; }}
  h1,h2,h3,h4,h5,h6 {{
    font-family:'AritaBuri',serif; font-weight:700; letter-spacing:-0.01em; color:{INK}; }}

  /* 가독성 : 본문 줄간격·크기 확보 (세리프 한글 대비) */
  .stApp {{ background:{APP_BG}; font-size:16px; }}
  p, li {{ line-height:1.72; }}
  .stMarkdown li {{ margin-bottom:2px; }}
  h1 {{ font-size:1.85rem; }}  h2 {{ font-size:1.4rem; }}
  h3 {{ font-size:1.22rem; }}  h4 {{ font-size:1.05rem; }}

  /* ---- 라이트 클린 테마 (플랫·정돈) ---- */
  .block-container {{ padding-top:2.4rem; }}
  section[data-testid="stSidebar"] {{ background:#ffffff; border-right:1px solid {BORDER}; }}
  p, span, label, li {{ color:{BODY}; }}
  [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{ color:{MUTED}; }}
  a {{ color:{SKY_DK}; }}
  hr {{ border-color:{BORDER}; margin:1.1rem 0; }}

  /* 배지(pill) : 밴드용 플랫 태그(채움) */
  .pill {{ display:inline-block; padding:3px 12px; border-radius:7px;
    color:#fff; font-weight:700; font-size:0.8rem; letter-spacing:.01em; }}
  /* Track 배지 : 채움 없이 연핑크 테두리 + 진한 글자(가독) */
  .pill-track {{ display:inline-block; padding:3px 13px; border-radius:7px;
    background:{PINK_BG}; color:{INK}; border:1.5px solid {PINK};
    font-weight:700; font-size:0.82rem; letter-spacing:.01em; }}

  /* KPI 카드 : 4칸 동일 높이 */
  .kpi {{ min-height:122px; display:flex; flex-direction:column; justify-content:center; }}
  .kpi h2 {{ margin:4px 0 2px; }}

  /* 카드 : 클릭/호버 인터랙션 (절제된 그림자) */
  .card {{ background:#ffffff; border:1px solid {BORDER}; border-radius:14px;
    padding:16px 18px; box-shadow:0 1px 3px rgba(16,24,40,.05);
    transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease; }}
  .card:hover {{ transform:translateY(-2px);
    box-shadow:0 8px 20px rgba(16,24,40,.08); border-color:{SKY_BD}; }}
  .card:active {{ transform:translateY(0) scale(.997); }}
  .card h2 {{ color:{INK}; }}

  /* 안내/경고 노트 */
  .safe-note {{ background:{SKY_BG}; border-left:3px solid {SKY}; padding:11px 15px;
    border-radius:10px; font-size:0.88rem; color:#175cd3; }}
  .safe-note b {{ color:{SKY_DK}; }}
  .warn-note {{ background:#fffaeb; border-left:3px solid {ORANGE}; padding:11px 15px;
    border-radius:10px; font-size:0.88rem; color:#b54708; }}
  .warn-note b {{ color:{RED_DK}; }}

  /* 초보자 안내 스트립 : 저채도 정돈 */
  .intro {{ background:{SURFACE}; border:1px solid {BORDER}; border-left:3px solid {SKY};
    border-radius:9px; padding:9px 14px; font-size:0.88rem; color:{BODY}; margin-bottom:8px; }}
  .intro b {{ color:{SKY_DK}; }}

  /* 참고문헌 목록 */
  .refs {{ font-size:0.82rem; color:{MUTED}; line-height:1.8; }}
  .refs b {{ color:{BODY}; }}

  /* 시작 가이드 카드 */
  .guide {{ background:{SURFACE};
    border:1px solid {BORDER}; border-radius:14px; padding:4px 4px; }}
  .gstep {{ display:inline-block; min-width:24px; height:24px; line-height:24px; text-align:center;
    border-radius:7px; background:{SKY}; color:#fff; font-weight:700; font-size:0.8rem;
    margin-right:8px; }}

  div[data-testid="stMetricValue"] {{ color:{INK}; }}
  div[data-testid="stMetricLabel"] {{ color:{MUTED}; }}

  /* 탭 : 호버/선택 인터랙션 (하늘 포인트) */
  button[data-baseweb="tab"] {{ transition:background .15s ease, color .15s ease;
    border-radius:10px 10px 0 0; padding:6px 10px; }}
  button[data-baseweb="tab"]:hover {{ background:{SKY_BG}; color:{SKY_DK}; }}
  button[data-baseweb="tab"][aria-selected="true"] {{ color:{SKY_DK}; }}
  [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{ background-color:{SKY} !important; }}

  /* 버튼 : 눌리는 느낌 */
  .stButton>button, .stDownloadButton>button, .stFormSubmitButton>button {{
    transition:transform .12s ease, box-shadow .15s ease, filter .15s ease;
    border-radius:10px; }}
  .stButton>button:hover, .stDownloadButton>button:hover, .stFormSubmitButton>button:hover {{
    transform:translateY(-1px); box-shadow:0 6px 16px rgba(2,132,199,.22); filter:saturate(1.05); }}
  .stButton>button:active, .stDownloadButton>button:active, .stFormSubmitButton>button:active {{
    transform:translateY(0) scale(.97); }}

  /* 데이터프레임/표 헤더 */
  [data-testid="stDataFrame"] {{ border-radius:12px; }}

  /* 셀렉트·입력 포커스 하늘 하이라이트 */
  [data-baseweb="select"] > div:focus-within,
  .stNumberInput input:focus, .stTextInput input:focus {{
    border-color:{SKY} !important; box-shadow:0 0 0 2px {SKY_BD} !important; }}
</style>
""", unsafe_allow_html=True)


def tab_intro(text):
    """각 탭 상단 초보자용 한 줄 안내."""
    st.markdown(f"<div class='intro'>🔰 <b>쉽게 말하면</b> : {text}</div>",
                unsafe_allow_html=True)


# ---------------------------------------------------------------- 데이터·모델 캐시
@st.cache_resource
def load_all():
    df = generate()
    res = train_and_score(df)
    shp = compute_shap(res["model"], res["X"])
    return res, shp

@st.cache_data
def get_compare():
    return compare_models(generate())

res, SHP = load_all()
DF = res["df"]
X = res["X"]
METRICS = res["metrics"]
patients = list(DF["patient_id"])


# ---------------------------------------------------------------- 사이드바
st.sidebar.markdown("## 🏥 Two-Track Care")
st.sidebar.caption("정신질환 퇴원환자 AI Care Coordination Platform")
st.sidebar.markdown("---")

st.sidebar.markdown(
    f"<div style='font-size:0.82rem;color:{MUTED};margin-bottom:6px'>"
    f"👇 환자를 바꾸면 <b style='color:{SKY_DK}'>③·④·탭</b> 내용이 "
    f"그 환자 기준으로 바뀝니다.</div>", unsafe_allow_html=True)
# 위험순 정렬 옵션
order = st.sidebar.radio("환자 목록 정렬", ["위험 높은 순", "환자 ID 순"], index=0)
plist = (DF.sort_values("risk_prob", ascending=False)["patient_id"].tolist()
         if order == "위험 높은 순" else sorted(patients))
sel = st.sidebar.selectbox("환자 선택", plist, index=0,
    format_func=lambda p: f"{p} · {DF.set_index('patient_id').loc[p,'diagnosis']}"
                          f" · 위험 {DF.set_index('patient_id').loc[p,'risk_prob']*100:.0f}%")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "<div class='safe-note'>본 시스템은 <b>진단 도구가 아닙니다</b>. EMR 기반 "
    "치료중단·재입원 <b>위험 신호</b>와 Track 배정만 제공하며, 모든 임상·연계 결정은 "
    "의료진과 의료사회복지사가 수행합니다.</div>", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.caption(f"코호트: 정신과 퇴원 {len(DF)}건 (합성 EMR)")
st.sidebar.caption("FHIR(Patient·Encounter·Condition·MedicationRequest) 표준 매핑 설계 → 실 EMR 즉시 호환")


# ---------------------------------------------------------------- 헤더
st.markdown("# AI 기반 Two-Track Care Coordination Platform")
st.markdown("##### 병원 EMR로 퇴원 시점의 치료중단·재입원 위험을 예측해, 의료사회복지사에게 "
            "‘우선 개입할 고위험 환자’를 제시하고 병원–의료사회복지사–정신건강복지센터를 하나의 "
            "업무 흐름으로 잇는 **의사결정 지원 시스템**")
st.markdown(
    f"<div class='intro' style='margin-top:2px'>🎯 <b>이 플랫폼의 목적</b> : 퇴원 후 "
    f"외래·복약이 끊긴 환자를 <b>조기에 포착해 공공 관리체계 안으로 다시 연결</b>합니다. "
    f"<b>환자용 앱이 아니라</b>, 병원·의료사회복지사·정신건강복지센터가 데이터를 근거로 "
    f"<b>먼저 개입</b>하도록 돕는 실무자용 도구입니다.</div>", unsafe_allow_html=True)

dft = DF
n_t1 = int((dft["track"] == "Track 1").sum())
n_t2 = int((dft["track"] == "Track 2").sum())
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f"<div class='card kpi'><span style='color:{MUTED}'>퇴원 코호트</span>"
            f"<h2>{len(dft)}<span style='font-size:0.5em'>건</span></h2>"
            f"<span style='font-size:0.78rem;color:{MUTED}'>합성 EMR · 퇴원 1건/행</span></div>",
            unsafe_allow_html=True)
c2.markdown(f"<div class='card kpi'><span class='pill-track'>Track 1</span>"
            f"<h2>{n_t1}<span style='font-size:0.5em'>명</span></h2>"
            f"<span style='font-size:0.78rem;color:{MUTED}'>일반 관리군 · 건강문해력 지원</span></div>",
            unsafe_allow_html=True)
c3.markdown(f"<div class='card kpi'><span class='pill-track'>Track 2</span>"
            f"<h2>{n_t2}<span style='font-size:0.5em'>명</span></h2>"
            f"<span style='font-size:0.78rem;color:{MUTED}'>고위험군 · 사회복지사 연계</span></div>",
            unsafe_allow_html=True)
c4.markdown(f"<div class='card kpi'><span style='color:{MUTED}'>예측 성능(AUROC) "
            f"<span style='font-size:0.82em'>(합성 기준)</span></span>"
            f"<h2>{METRICS['auroc']:.3f}</h2>"
            f"<span style='font-size:0.78rem;color:{MUTED}'>홀드아웃 {METRICS['n_test']}건 · "
            f"AUPRC {METRICS['auprc']:.3f} · 실전 목표 0.68~0.75</span></div>",
            unsafe_allow_html=True)

st.markdown("")

# ---------------------------------------------------------------- 시작 가이드(초보자)
with st.expander("🔰 처음 오셨나요? : 30초 사용 설명 (클릭해서 펼치기/접기)", expanded=True):
    st.markdown(
        f"<div class='guide'>"
        f"<p style='margin:4px 2px 10px;font-size:0.96rem;color:{INK}'>"
        f"<b>이 데모가 하는 일 (한 문장):</b> 정신질환으로 입원했다가 퇴원하는 환자가 "
        f"퇴원 후 <b style='color:{VERM}'>치료를 중단하거나 다시 입원할 위험</b>을 "
        f"<b>병원에 이미 있는 진료기록(EMR)</b>으로 미리 계산하고, 위험이 낮으면 "
        f"<b style='color:{SKY_DK}'>쉬운 건강 설명</b>을, 높으면 "
        f"<b style='color:{VERM}'>사회복지사·정신건강복지센터 연계</b>를 자동으로 이어줍니다."
        f"</p></div>", unsafe_allow_html=True)
    gc1, gc2 = st.columns([1, 1])
    with gc1:
        st.markdown("**꼭 알아야 할 용어 3개**")
        st.markdown(
            f"- <b style='color:{SKY_DK}'>위험예측</b> : 병원 기록을 넣으면 재입원 가능성을 "
            f"0~100%로 계산 (AI 모델 = XGBoost)\n"
            f"- <b style='color:{SKY_DK}'>Two-Track</b> : 그 결과를 낮은 위험(Track 1)/"
            f"높은 위험(Track 2) 두 갈래로 자동 분류\n"
            f"- <b style='color:{SKY_DK}'>SHAP</b> : AI가 <b>왜</b> 그렇게 판단했는지 이유를 "
            f"항상 함께 보여줌 (블랙박스 아님)", unsafe_allow_html=True)
    with gc2:
        st.markdown("**이 순서로 보세요**")
        st.markdown(
            "<span class='gstep'>1</span> ① 어떤 데이터를 쓰나 · "
            "필요 데이터 확인<br>"
            "<span class='gstep'>2</span> ② AI가 위험을 어떻게 계산·설명하나<br>"
            "<span class='gstep'>3</span> ③ <b>우선개입 대기열</b> (고위험 환자 순위) + 환자 상세<br>"
            "<span class='gstep'>4</span> ④ 위험군별로 무엇을 해주나<br>"
            "<span class='gstep'>5</span> ⑤⑥⑦ 차별점 · 실데이터 증명 · 직접 입력",
            unsafe_allow_html=True)

st.markdown("")
tabs = st.tabs(["① EMR 데이터", "② AI 위험예측 엔진 (XGBoost·SHAP)",
                "③ 우선개입 대기열 · 환자 상세",
                "④ 대응 · 개입 연계", "⑤ 차별점 · 성능",
                "⑥ 실데이터 검증", "⑦ 신규 환자 입력·예측"])


# ================================================================ ① EMR 데이터
with tabs[0]:
    tab_intro("병원에 이미 있는 진료기록(EMR)에서 <b>어떤 값들을 쓰는지</b> 보여줍니다. "
              "웨어러블·설문 같은 새 장비 없이 <b>기존 기록만</b>으로 동작합니다.")
    st.markdown("### 병원 EMR 기반 입력 데이터")
    st.caption("퇴원 시점에 EMR에서 추출되는 피처만 사용합니다. 웨어러블·별도 센서 없이 기존 의무기록만으로 동작합니다. "
               "피처 선정은 정신과 재입원 예측인자 체계적 문헌고찰(Donisi et al., BMC Psychiatry 2016)과 "
               "정신·물질사용장애 재입원 ML 연구(Morel et al., 2020)의 상위 위험요인을 반영했습니다.")

    cols = st.columns(len(FEATURE_GROUPS))
    for col, (gname, gcols) in zip(cols, FEATURE_GROUPS.items()):
        with col:
            st.markdown(
                f"<h4 style='color:{INK};font-size:1.0rem;border-bottom:2px solid {SKY_BD};"
                f"padding-bottom:6px;margin-bottom:8px'>{gname}</h4>",
                unsafe_allow_html=True)
            for c in gcols:
                st.markdown(f"- {FEATURE_LABELS.get(c, c)}")

    st.markdown("---")
    st.markdown("#### 퇴원 환자 코호트 미리보기")
    st.markdown(
        "<div class='warn-note'>⚠️ <b>이 코호트는 실제 환자 데이터가 아닙니다.</b> "
        "한국 정신과 실 EMR은 민감정보·IRB 승인 대상이라 아이디어 검증 단계에서 쓸 수 없어, "
        "임상적으로 알려진 위험요인 구조를 반영해 <b>프로그램으로 생성한 합성 데이터(1,500건)</b>"
        "입니다(<code>data_generator.py</code>). 파이프라인이 <b>실데이터</b>에서 작동하는지는 "
        "⑥ 실데이터 검증 탭(UCI 실환자 약 7만 명)에서 별도로 증명합니다.</div>",
        unsafe_allow_html=True)
    st.markdown("")
    show_cols = (["patient_id", "diagnosis", "age", "prior_admissions",
                  "prior_noshow_rate", "med_pdc", "lives_alone", "medicaid",
                  "risk_prob", "track"])
    pretty = DF[show_cols].copy()
    pretty["risk_prob"] = (pretty["risk_prob"] * 100).round(0)
    pretty["prior_noshow_rate"] = (pretty["prior_noshow_rate"] * 100).round(0)
    pretty["med_pdc"] = (pretty["med_pdc"] * 100).round(0)
    pretty["lives_alone"] = np.where(pretty["lives_alone"] == 1, "예", "-")
    pretty["medicaid"] = np.where(pretty["medicaid"] == 1, "예", "-")
    pretty = pretty.rename(columns={
        "patient_id": "환자", "diagnosis": "진단", "age": "연령",
        "prior_admissions": "과거입원", "prior_noshow_rate": "외래미방문율",
        "med_pdc": "복약보유율", "lives_alone": "독거", "medicaid": "의료급여",
        "risk_prob": "위험%", "track": "Track"})
    st.dataframe(
        pretty.head(25), use_container_width=True, height=380, hide_index=True,
        column_config={
            "환자": st.column_config.TextColumn(width="small"),
            "진단": st.column_config.TextColumn(width="small"),
            "연령": st.column_config.NumberColumn(width="small", format="%d"),
            "과거입원": st.column_config.NumberColumn(width="small", format="%d회"),
            "외래미방문율": st.column_config.NumberColumn(width="small", format="%d%%"),
            "복약보유율": st.column_config.NumberColumn(width="small", format="%d%%"),
            "독거": st.column_config.TextColumn(width="small"),
            "의료급여": st.column_config.TextColumn(width="small"),
            "위험%": st.column_config.NumberColumn(width="small", format="%d%%"),
            "Track": st.column_config.TextColumn(width="small"),
        })
    st.caption("라벨(90일 내 치료중단/재입원)은 학습·평가에만 사용하고 화면에는 위험확률·Track만 노출합니다.")

    # ---------------- 실제 도입에 필요한 데이터 (기술 강화) ----------------
    st.markdown("---")
    st.markdown("#### 🔧 실제 병원 도입 시 필요한 데이터 : 무엇을, 어디서, 어떤 형식으로")
    st.markdown(
        f"<div class='intro'>아래 표의 값들은 <b>대부분 병원 EMR·처방시스템에 이미 존재</b>합니다. "
        f"새로 수집할 것은 사회경제 항목(초기 사회사업 평가) 정도이며, 표준코드(ICD-10·ATC·FHIR)로 "
        f"사상되어 있어 <b>연동 시 추가 개발이 적습니다.</b></div>", unsafe_allow_html=True)

    req = pd.DataFrame([
        ["인구학", "연령, 성별", "환자기본정보", "FHIR Patient (birthDate·gender)", "입원 시 1회"],
        ["진단", "주·부상병 (조현병/양극성/우울/불안)", "진단 기록", "ICD-10 (F20·F31·F32·F41) → FHIR Condition", "입·퇴원 시"],
        ["입원·응급 이력", "과거 입원횟수, 재원일수, 응급실 방문, 비자발 입원", "입퇴원·응급 기록", "FHIR Encounter (class·period)", "실시간 누적"],
        ["외래·예약", "외래 방문수, 예약부도율(no-show)", "예약·수납 시스템", "예약일 vs 실제 내원일 차이로 산출", "일 단위"],
        ["복약", "약물 수, 복약보유율(PDC), 과거 치료중단", "처방·조제 이력", "ATC 코드 → FHIR MedicationRequest/Dispense", "처방 시마다"],
        ["사회경제·접근성", "독거, 보호자, 의료급여, 거주거리, 물질사용", "사회사업 초기평가·자격 DB", "사회복지 초기평가지 · 자격 행정연계", "입원 초기 1회"],
        ["동반질환", "Charlson 동반질환 지수", "진단 이력 집계", "ICD-10 매핑 후 가중합 계산", "퇴원 시"],
        ["라벨(정답)", "퇴원 후 90일 내 재입원·치료중단 여부", "입원·처방 공백 추적", "재입원 Encounter + 처방 gap(≥허용일)", "학습용(후향 추적)"],
    ], columns=["데이터 개념", "구체 항목(예)", "어디서 오나 (원천)", "표준코드 / 형식", "갱신 주기"])
    st.dataframe(req, use_container_width=True, height=330)

    r1, r2, r3 = st.columns(3)
    r1.markdown(
        f"<div class='card'><b style='color:{SKY_DK}'>📦 최소 요건</b>"
        f"<p style='font-size:0.85rem'>퇴원 사례 <b>수백~수천 건</b>(사건 수 기준). "
        f"라벨 관측을 위해 <b>퇴원 후 90일 추적</b> 기간이 필요합니다.</p></div>",
        unsafe_allow_html=True)
    r2.markdown(
        f"<div class='card'><b style='color:{SKY_DK}'>🔐 개인정보</b>"
        f"<p style='font-size:0.85rem'>가명·비식별 처리 후 반입, 병원 내(온프레미스) 학습 권장. "
        f"인종 등 <b>민감·차별 소지 속성은 제외</b>합니다.</p></div>",
        unsafe_allow_html=True)
    r3.markdown(
        f"<div class='card'><b style='color:{SKY_DK}'>🔁 운영</b>"
        f"<p style='font-size:0.85rem'>월 단위 재학습으로 성능 유지 : 기관 간 모델 이식성이 "
        f"낮아 <b>병원별(site-specific) 학습</b>이 필요하다는 최신 근거(Ren et al., "
        f"JMIR Ment Health 2025)와 부합. FHIR Bundle 수신 시 "
        f"<b>퇴원 순간 자동 예측</b> (환자 앱 입력에 의존하지 않음).</p></div>",
        unsafe_allow_html=True)
    st.caption("※ 이 데모는 위 스키마와 동일한 구조의 합성 EMR로 동작하며, 실데이터에서의 작동은 "
               "⑥ 실데이터 검증 탭에서 공개 실환자 데이터로 증명합니다.")


# ================================================================ ② 위험예측 엔진
with tabs[1]:
    tab_intro("①의 값들을 넣으면 AI가 <b>‘퇴원 후 90일 안에 치료 중단·재입원할 확률’</b>을 "
              "%로 계산하고, <b>왜 그렇게 봤는지 근거(SHAP)</b>까지 보여줍니다.")
    st.markdown("### XGBoost 위험예측 엔진 + SHAP 설명가능 AI")
    st.markdown(
        "<div class='warn-note'>모델은 <b>진단하지 않습니다</b>. EMR 피처로 "
        "‘90일 내 치료중단/재입원’ <b>위험확률</b>을 산출하고, 임계값으로 Track을 나눕니다. "
        "모든 예측은 <b>SHAP</b>으로 근거를 제시합니다(블랙박스 배제).</div>",
        unsafe_allow_html=True)

    cL, cR = st.columns(2)
    with cL:
        st.markdown("#### 모델 성능 (홀드아웃)")
        st.caption("AUROC=아무나 두 명 뽑았을 때 위험한 사람을 더 위험하다고 맞히는 비율(1에 가까울수록 좋음). "
                   "AUPRC=고위험군을 놓치지 않는 정도.")
        m1, m2, m3 = st.columns(3)
        m1.metric("AUROC", f"{METRICS['auroc']:.3f}")
        m2.metric("AUPRC", f"{METRICS['auprc']:.3f}")
        m3.metric("사건율", f"{METRICS['prevalence']:.1%}")
        fpr, tpr = METRICS["roc"]
        rec, prec = METRICS["pr"]
        roc_fig = go.Figure()
        roc_fig.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines",
                          line=dict(color=SKY, width=3), name="ROC"))
        roc_fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines",
                          line=dict(color="#cbd5e1", dash="dash"), name="무작위"))
        roc_fig.update_layout(height=300, title="ROC 곡선",
                              xaxis_title="위양성률", yaxis_title="민감도",
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(color=BODY), legend=dict(y=0.1, x=0.55))
        st.plotly_chart(roc_fig, use_container_width=True)
        st.caption("⚠️ 위 수치는 ‘합성 데이터’ 기준으로 실전보다 낙관적입니다. 실 EMR 기반 "
                   "정신과 재입원 ML의 문헌 보고 성능은 AUROC 약 0.68~0.75 "
                   "(Morel et al. 2020: XGBoost 0.738; Transl Psychiatry 2021: ~0.68)로, "
                   "실증 단계 목표도 이 범위로 설정합니다(과장 없는 기준).")

    with cR:
        st.markdown("#### 위험확률 분포 · Two-Track 임계값")
        st.caption("환자들을 위험확률(%)별로 세어 그린 그래프. 점선(임계값)보다 오른쪽이 고위험(Track 2)입니다.")
        hist = go.Figure()
        for trk, color in TRACK_COLORS.items():
            sub = DF[DF["track"] == trk]["risk_prob"] * 100
            hist.add_trace(go.Histogram(x=sub, name=trk, marker_color=color,
                                        opacity=0.78, xbins=dict(size=5)))
        hist.add_vline(x=TRACK2_THRESHOLD * 100, line=dict(color=INK, dash="dash"),
                       annotation_text=f"Track 2 임계값 {TRACK2_THRESHOLD*100:.0f}%")
        hist.update_layout(height=300, barmode="overlay", title="예측 위험확률 분포",
                           xaxis_title="위험확률(%)", yaxis_title="환자 수",
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           font=dict(color=BODY), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(hist, use_container_width=True)
        st.caption("임계값은 운영 정책에 따라 조정 가능합니다(민감도 vs 의료사회복지사 업무량 트레이드오프).")

    st.markdown("---")
    st.markdown("#### SHAP 전역 피처 중요도 : 무엇이 위험을 끌어올리나")
    st.caption("막대가 길수록 그 항목이 위험 판단에 더 크게 작용했다는 뜻입니다(전체 환자 평균 기준).")
    gi = global_importance(SHP)[:12][::-1]
    bar = go.Figure(go.Bar(
        x=[v for _, v in gi], y=[l for l, _ in gi], orientation="h",
        marker_color=SKY_DK,
        text=[f"{v:.2f}" for _, v in gi], textposition="outside"))
    bar.update_layout(height=440, xaxis_title="평균 |SHAP| (로그오즈 기여)",
                      margin=dict(l=10, r=10, t=10, b=30),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=BODY))
    st.plotly_chart(bar, use_container_width=True)
    st.caption("과거 치료중단·낮은 복약보유율(PDC)·높은 외래 미방문율·과거 입원력이 핵심 위험요인으로 "
               "학습됨 : 문헌과 일치: 체계적 고찰에서 ‘과거 입원력’이 가장 일관된 재입원 예측인자였고 "
               "(Donisi et al., BMC Psychiatry 2016), 복약 비순응은 재입원과 강하게 연관된 "
               "대표 요인입니다(1년 재입원 독립 예측인자로 반복 보고).")


# ================================================================ ③ Two-Track 분류·상세
with tabs[2]:
    tab_intro("이 탭이 이 플랫폼의 <b>핵심 산출물</b>입니다. 먼저 <b>의료사회복지사가 오늘 "
              "먼저 챙겨야 할 고위험 환자 대기열</b>을 위험 높은 순으로 보여주고, 그 아래에서 "
              "환자 <b>한 명</b>을 골라 위험 근거를 자세히 봅니다.")

    # ---------------- 의료사회복지사 우선개입 대기열 (worklist) ----------------
    st.markdown("### 🗂️ 의료사회복지사 우선개입 대기열")
    st.markdown(
        f"<div class='intro'>퇴원 시점에 AI가 위험도를 계산해 <b>Track 2(고위험)</b> 환자를 "
        f"위험 높은 순으로 자동 정렬합니다. 담당자는 이 목록의 <b>위에서부터</b> 개입하면 "
        f"됩니다 : ‘누구를 먼저 봐야 하나’를 데이터로 답합니다.</div>", unsafe_allow_html=True)

    def _top_drivers(idx, k=3):
        sp = patient_shap(SHP, X, idx)
        drv = [l for l, s, v in sp if s > 0][:k]
        return ", ".join(drv) if drv else "복합 위험요인"

    t2 = DF[DF["track"] == "Track 2"].sort_values("risk_prob", ascending=False)
    total_t2 = len(t2)
    wl = t2.head(15).copy()
    pid_to_pos = {p: patients.index(p) for p in wl["patient_id"]}
    worklist = pd.DataFrame({
        "우선순위": range(1, len(wl) + 1),
        "환자": wl["patient_id"].values,
        "진단": wl["diagnosis"].values,
        "위험%": (wl["risk_prob"] * 100).round(0).astype(int).values,
        "밴드": wl["band"].values,
        "주요 위험요인(SHAP)": [_top_drivers(pid_to_pos[p]) for p in wl["patient_id"]],
        "권고 조치": ["복약·외래 지속 점검 + 정신건강복지센터 연계 검토"] * len(wl),
    })
    wc1, wc2, wc3 = st.columns(3)
    wc1.metric("고위험(Track 2) 총원", f"{total_t2}명")
    wc2.metric("대기열 최상위 위험도", f"{int(wl['risk_prob'].iloc[0]*100)}%" if len(wl) else "-")
    wc3.metric("표시 중", f"상위 {len(wl)}명")
    st.dataframe(
        worklist, use_container_width=True, height=430, hide_index=True,
        column_config={
            "우선순위": st.column_config.NumberColumn(width="small", format="%d"),
            "환자": st.column_config.TextColumn(width="small"),
            "진단": st.column_config.TextColumn(width="small"),
            "위험%": st.column_config.NumberColumn(width="small", format="%d%%"),
            "밴드": st.column_config.TextColumn(width="small"),
            "주요 위험요인(SHAP)": st.column_config.TextColumn(width="large"),
            "권고 조치": st.column_config.TextColumn(width="large"),
        })
    st.caption("이 대기열이 곧 ‘업무 흐름의 시작점’입니다 : 병원(자동 선별) → 의료사회복지사"
               "(위 목록 순 개입) → 정신건강복지센터(환자 동의 기반 연계)로 이어집니다. "
               "실서비스에서는 퇴원 시점에 이 목록이 담당자 화면에 자동으로 뜹니다.")

    st.markdown("---")
    st.markdown("### 🔎 개별 환자 상세 : 위험 근거 확인")
    st.markdown(f"<div class='intro'>대기열에서 확인할 환자를 <b>왼쪽 사이드바</b>에서 고르면 "
                f"아래가 그 환자 기준으로 바뀝니다. 현재 선택: <b>{sel}</b></div>",
                unsafe_allow_html=True)
    i = patients.index(sel)
    row = DF.iloc[i]
    track = row["track"]; band = row["band"]; prob = row["risk_prob"]
    tcolor = TRACK_COLORS[track]

    h1, h2 = st.columns([1, 2])
    with h1:
        st.markdown(f"#### 환자 `{sel}` · {row['diagnosis']}")
        st.markdown(f"<span class='pill-track' style='font-size:1.0rem'>{track}</span>  "
                    f"<span class='pill' style='background:{BAND_COLORS[band]}'>{band}</span>",
                    unsafe_allow_html=True)
        st.metric("치료중단/재입원 위험확률", f"{prob*100:.0f} %")
        st.caption(band_description(band))
        st.markdown("**주요 EMR 값**")
        keyvals = [("연령", f"{int(row['age'])}세"),
                   ("과거 입원", f"{int(row['prior_admissions'])}회"),
                   ("외래 미방문율", f"{row['prior_noshow_rate']*100:.0f}%"),
                   ("복약 보유율(PDC)", f"{row['med_pdc']*100:.0f}%"),
                   ("독거 / 보호자", f"{'예' if row['lives_alone'] else '아니오'}"
                                  f" / {'있음' if row['has_caregiver'] else '없음'}"),
                   ("의료급여", "예" if row["medicaid"] else "아니오")]
        for k, v in keyvals:
            st.markdown(f"- {k}: **{v}**")

    with h2:
        st.markdown("#### 이 환자의 SHAP 기여도 : 왜 이렇게 예측했나")
        sp = patient_shap(SHP, X, i)[:10][::-1]
        colors = [DANGER if s > 0 else SKY for _, s, _ in sp]
        wf = go.Figure(go.Bar(
            x=[s for _, s, _ in sp],
            y=[f"{l} = {v:g}" for l, s, v in sp],
            orientation="h", marker_color=colors,
            text=[f"{s:+.2f}" for _, s, _ in sp], textposition="outside"))
        wf.update_layout(height=440, xaxis_title="SHAP 기여 (→ 위험↑ / ← 위험↓)",
                         margin=dict(l=10, r=10, t=10, b=30),
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color=BODY))
        st.plotly_chart(wf, use_container_width=True)
        st.caption("🔴 빨강 = 위험을 높인 요인 · 🔵 하늘 = 위험을 낮춘 요인. "
                   "담당자는 근거를 보고 개입 우선순위를 판단합니다.")

    st.info(f"**자동 배정 결과:** {sel} 환자는 위험확률 {prob*100:.0f}% 로 "
            f"**{track}** 에 배정되었습니다. "
            + ("→ Track 1: 생성형 AI 건강문해력 지원 대상 (④번 탭)"
               if track == "Track 1"
               else "→ Track 2: 의료사회복지사 컨설트 자동 생성 대상 (④번 탭)"))


# ================================================================ ④ 대응·개입
with tabs[3]:
    tab_intro(f"위험도로 나뉜 <b>두 갈래(Track)</b>에 각각 무엇을 해주는지 보여줍니다. "
              f"Track 1 = <b style='color:{SKY_DK}'>쉬운 건강 설명</b>, "
              f"Track 2 = <b style='color:{VERM}'>사회복지사·센터 연계</b>.")
    i = patients.index(sel)
    row = DF.iloc[i]
    track = row["track"]; prob = row["risk_prob"]

    st.markdown(f"### 대응 · 개입 연계 : `{sel}` ({track})")
    st.markdown(
        f"<div class='intro'>🔗 <b>하나의 업무 흐름</b> : "
        f"<b>병원</b>(EMR로 위험 자동 선별) → <b>의료사회복지사</b>(③ 대기열 순 개입) → "
        f"<b>정신건강복지센터</b>(환자 동의 기반 지역사회 연계). 이 탭은 그 흐름에서 "
        f"선택 환자에게 실제로 무엇을 하는지 보여줍니다.</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='safe-note'>아래 내용은 <b>의료 행위가 아닌 안내·업무지원</b>입니다. "
        "LLM은 기존 문서를 쉬운 말로 풀어줄 뿐 진단·처방하지 않으며, 고위험군도 "
        "‘담당자 확인·연계 권고’ 수준으로만 처리합니다.</div>", unsafe_allow_html=True)
    st.markdown("")

    if track == "Track 1":
        st.markdown("#### 🟦 Track 1 · RAG 기반 생성형 AI 건강 문해력 지원")
        st.caption("퇴원요약지·복약지도서의 어려운 의학용어를 지식베이스에서 검색(retrieval)해 "
                   "근거를 확보한 뒤, 그 근거에만 기반해 쉬운 말로 재구성합니다(RAG).")
        doc = build_document(row)
        rag = plain_rewrite(doc, f"진단 {row['diagnosis']}, 독거={'예' if row['lives_alone'] else '아니오'}")

        d1, d2 = st.columns(2)
        with d1:
            st.markdown("**① 원본 의료문서 (EMR)**")
            st.code(doc, language=None)
            st.markdown(f"**② 검색된 의학용어 근거 ({len(rag['retrieved'])}개)**")
            _SRC_BADGE = {"live": " `식약처 e약은요 · 실시간`",
                          "snapshot": " `식약처 e약은요 · 스냅샷`"}
            for r in rag["retrieved"]:
                badge = _SRC_BADGE.get(r.get("src", ""), "")
                st.markdown(f"- **{r['key']}**{badge} : {r['plain']}")
        with d2:
            st.markdown("**③ 환자·보호자용 쉬운말 재구성**")
            st.markdown(f"<div class='card'>{rag['text']}</div>", unsafe_allow_html=True)
            if rag["source"] == "llm":
                st.caption("✓ Claude(claude-opus)로 생성 · RAG 근거 기반 · 가드레일 적용")
            else:
                st.caption("현재 검색 근거 기반 템플릿으로 생성 중. ANTHROPIC_API_KEY 설정 시 "
                           "Claude가 동일 근거로 더 자연스러운 문장을 실시간 생성합니다.")
    else:
        st.markdown("#### 🟥 Track 2 · 의료사회복지사 컨설트 · 정신건강복지센터 연계")
        sp = patient_shap(SHP, X, i)
        drivers = [f"{l}" for l, s, v in sp if s > 0][:4]
        reason = ", ".join(drivers) if drivers else "복합 위험요인"
        st.markdown(
            f"<div class='card' style='border-left:5px solid {VERM}'>"
            f"<span class='pill' style='background:{VERM}'>자동 컨설트 생성</span>"
            f"<h4 style='margin:10px 0 4px'>의료사회복지사 루틴 컨설트</h4>"
            f"<p>대상 <b>{sel}</b> ({row['diagnosis']}) · 위험확률 "
            f"<b style='color:{VERM}'>{prob*100:.0f}%</b><br>주요 위험요인(SHAP): {reason}<br>"
            f"권고: 퇴원 후 복약·외래 지속 점검, 환자 동의 기반 정신건강복지센터 연계 검토.</p>"
            f"</div>", unsafe_allow_html=True)

        st.markdown("##### 연계 워크플로 (개입의 고리)")
        steps = [
            ("1. 고위험 자동 선별", "XGBoost 위험예측 → Track 2 자동 배정", DANGER),
            ("2. 의료사회복지사 컨설트", "EMR·SHAP 근거 포함 컨설트 자동 생성", ORANGE),
            ("3. 사회복지사 평가", "독거·보호자·경제 상황 등 사회적 요인 확인", CYAN),
            ("4. 환자 동의 기반 연계", "정신건강복지센터·지역사회 자원 연결", SKY),
            ("5. 지속 사후관리", "복약 순응도·외래 추적 모니터링", SKY_DK),
        ]
        scols = st.columns(len(steps))
        for sc, (t, d, c) in zip(scols, steps):
            sc.markdown(f"<div class='card' style='border-top:4px solid {c};min-height:150px'>"
                        f"<b style='color:{c}'>{t}</b><p style='font-size:0.82rem;color:{MUTED}'>{d}</p></div>",
                        unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 의료 규제 안전 설계 체크리스트")
    for label in [
        "진단 라벨 미출력 : 위험 신호·Track 배정만 제공",
        "예측 근거를 SHAP으로 항상 제시 (설명가능 AI, 블랙박스 배제)",
        "전문의 직접 처방 대신 ‘의료사회복지사 확인·연계 권고’",
        "RAG: LLM은 검색된 근거 밖 의학정보를 생성하지 않음(환각 억제)",
        "임의 복약중단 금지·‘판단은 전문가가 수행’ 고지 강제",
        "FHIR 표준·비식별화 저장 설계 (개인정보·민감정보 보호)",
    ]:
        st.markdown(f"✅ {label}")


# ================================================================ ⑤ 차별점·성능
with tabs[4]:
    tab_intro("<b>왜 기존 서비스와 다른지</b>, 그리고 AI 모델 성능은 어떤지 정리한 탭입니다.")
    st.markdown("### 차별점 : 예측에서 끝내지 않고 ‘개입의 고리’를 닫는다")
    st.markdown(
        "기존 정신건강 솔루션의 한계: **① 자발적 참여 의존(고위험군 누락) · "
        "② 의료문서 요약에 그쳐 병원·지역사회 연계 단절 · ③ 신체질환 중심 통합돌봄**. "
        "본 플랫폼은 EMR 위험예측 → Two-Track → (Track1 건강문해력 / Track2 사회복지·센터 연계)로 "
        "병원-의료사회복지사-정신건강복지센터를 하나의 프로세스로 연결합니다.")

    st.markdown("#### 모델 비교 : 성능은 대등, XGBoost는 ‘설명가능성’으로 채택")
    cmp = get_compare()
    names = list(cmp.keys()); vals = [cmp[n] for n in names]
    cc = st.columns(len(cmp))
    for col, n in zip(cc, names):
        col.metric(n, f"{cmp[n]:.3f}")
    barfig = go.Figure(go.Bar(
        x=names, y=vals,
        marker_color=[SKY_DK if n == "XGBoost" else "#cbd5e1" for n in names],
        text=[f"{v:.3f}" for v in vals], textposition="outside"))
    barfig.update_layout(height=360, yaxis_title="AUROC (홀드아웃)",
                         yaxis_range=[0.5, max(vals) + 0.08],
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color=BODY))
    st.plotly_chart(barfig, use_container_width=True)
    st.caption("세 모델의 예측 성능은 대등합니다. XGBoost를 채택한 이유는 ① 정식 SHAP(TreeSHAP) "
               "내장으로 모든 예측에 임상 근거 제시(설명가능 AI), ② 비선형·결측·스케일에 강건, "
               "③ EMR 피처 확장에 용이 : 즉 ‘성능’이 아니라 임상 신뢰·운영성에서의 우위입니다. "
               "정신·물질사용장애 재입원 예측 대규모 연구에서도 XGBoost(AUROC 0.738)가 "
               "정규화 선형모형(0.697)을 상회했습니다(Morel et al., Int J Med Inform 2020). "
               "본 아이디어의 진짜 차별점은 모델이 아니라 아래 Two-Track 연계 구조입니다.")

    st.markdown("---")
    cA, cB = st.columns(2)
    with cA:
        st.markdown("#### 핵심 기술 두 축")
        st.markdown(
            "- **① 위험예측 엔진**: XGBoost + SHAP. EMR(입원·외래·복약·사회경제)로 "
            "치료중단/재입원 위험을 산출하고 근거를 제시.\n"
            "- **② 건강문해력 지원**: RAG 기반 LLM. 퇴원문서를 의학용어 지식베이스에 "
            "근거를 두고 쉬운 말로 재구성(환각 억제).\n"
            "- **FHIR 표준 연동**: Patient·Encounter·Condition·MedicationRequest 매핑으로 "
            "실 병원 EMR 즉시 호환.\n"
            "- **병원별 학습 전략**: 기관 간 모델 이식성이 낮다는 2025년 다기관 연구 결과에 따라 "
            "(Ren et al., JMIR Ment Health 2025) 도입 병원 자체 데이터로 온프레미스 재학습.")
    with cB:
        st.markdown("#### 기대 효과 / 확장")
        st.markdown(
            "- 복약 중단·외래 이탈 감소, 재발·재입원 예방\n"
            "- 의료사회복지 업무 효율화(고위험군 자동 선별)\n"
            "- 정신건강복지센터 연계 활성화, 지역사회 정착 지원\n"
            "- B2B(상급종합·대학·정신병원) + B2G(센터·보건소·지자체) SaaS\n"
            "- 확장: 노인 통합돌봄·치매·만성질환 지속관리로 동일 구조 적용")

    # ---------------- 사업화·실증 로드맵 (데이터 성숙도 단계) ----------------
    st.markdown("---")
    st.markdown("#### 🚀 사업화·실증 로드맵 : ‘합성 PoC → 실데이터 → 병원 실증’ 데이터 성숙도")
    st.markdown(
        f"<div class='intro'>심사에서 가장 중요한 질문은 <b>“합성 데이터로 만든 게 실제로 되겠는가”</b>입니다. "
        f"그 답은 <b>데이터를 갈아끼우는 경로가 이미 설계돼 있다</b>는 것입니다. 아래 3단계는 "
        f"모델·코드를 바꾸지 않고 <b>데이터 소스만 교체</b>하며 성숙도를 올립니다.</div>",
        unsafe_allow_html=True)

    road = pd.DataFrame([
        ["1단계 · 현재 (PoC)",
         "합성 정신과 코호트 1,500건 + UCI 실환자 약 7만 명(파이프라인 검증)",
         "전처리→학습→SHAP→Two-Track 전 과정이 실데이터에서 작동함을 증명(⑥탭)",
         "비용 0 · 규제 이슈 없음 · 즉시 재현 가능"],
        ["2단계 · 국내 공개 실데이터",
         "HIRA 환자표본자료(HIRA-NPS) : 정신·행동장애(ICD-10 F코드) 청구 실데이터",
         "한국 정신질환 재입원을 실제 국내 데이터로 학습·검증(도메인 일치)",
         "연구계획서+소액 수수료로 신청 가능 · 비식별 공개 자료"],
        ["3단계 · 병원 실증 (사업화)",
         "협력병원 정신과 EMR(FHIR) : 도입 병원 자체 데이터로 온프레미스 재학습",
         "site-specific 모델로 실사용 성능 확보 → SaaS 납품",
         "IRB 승인·데이터 심의 필요 · 병원 내 학습(정보 미반출)"],
    ], columns=["단계", "데이터 소스", "무엇을 증명/달성하나", "규제·비용 조건"])
    st.dataframe(road, use_container_width=True, height=210)
    st.caption("핵심: 1→2→3단계에서 XGBoost·SHAP·RAG·Two-Track 코드는 그대로이고 "
               "'데이터 소스'만 바뀝니다. 도메인 불일치(당뇨) 우려는 2단계 HIRA F코드 데이터로 "
               "정신과 도메인에 정렬되며, 3단계에서 병원별(site-specific) 재학습으로 "
               "실사용 성능을 확보합니다 : 기관 간 이식성이 낮다는 최신 근거(Ren et al. 2025)와 "
               "부합하는 현실적 전략입니다.")

    rd1, rd2, rd3 = st.columns(3)
    rd1.markdown(
        f"<div class='card'><b style='color:{SKY_DK}'>🎯 왜 지금 합성인가</b>"
        f"<p style='font-size:0.85rem'>정신과 실 EMR은 IRB·데이터심의로 아이디어 검증 "
        f"단계에선 쓸 수 없습니다. 합성으로 <b>설계 타당성</b>을, UCI로 <b>실데이터 작동</b>을 "
        f"분리 증명한 것이 오히려 정직한 순서입니다.</p></div>", unsafe_allow_html=True)
    rd2.markdown(
        f"<div class='card'><b style='color:{SKY_DK}'>💰 시장·수요</b>"
        f"<p style='font-size:0.85rem'>정신질환 1년 재입원율은 문헌상 40~50% 수준으로 높고, "
        f"재입원은 직접적 비용·질 지표입니다. 고위험군 자동선별로 의료사회복지 업무를 "
        f"줄이는 <b>명확한 비용절감 논리</b>가 있습니다.</p></div>", unsafe_allow_html=True)
    rd3.markdown(
        f"<div class='card'><b style='color:{SKY_DK}'>🔌 도입 장벽 낮음</b>"
        f"<p style='font-size:0.85rem'>FHIR 표준 매핑·EMR 기존 피처만 사용(웨어러블 불필요)·"
        f"병원 내 온프레미스 학습 → 신규 장비/데이터 반출 없이 <b>기존 워크플로에 삽입</b> "
        f"가능합니다.</p></div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        "<div class='safe-note'>데모 데이터는 <b>정신과 퇴원 코호트 구조의 합성 EMR</b>이며, "
        "실제 병원 EMR 연결 시 동일 피처 스키마로 즉시 학습·평가 가능하도록 설계했습니다. "
        "파이프라인의 실데이터 작동 검증은 <b>⑥ 실데이터 검증</b> 탭을, 실데이터로 넘어가는 "
        "구체적 경로는 위 <b>사업화·실증 로드맵</b>을 참고하세요.</div>",
        unsafe_allow_html=True)


# ================================================================ ⑥ 실데이터 검증
@st.cache_resource
def load_uci_all():
    df_u = load_uci()
    res_u = train_and_score_uci(df_u)
    gi_u = uci_global_importance(res_u)
    return res_u, gi_u


with tabs[5]:
    tab_intro("합성(가짜) 데이터가 아니라 <b>진짜 환자 공개 데이터</b>로도 이 파이프라인이 "
              "작동하는지 증명하는 탭입니다.")
    st.markdown("### 실데이터 검증 : 공개 실환자 데이터로 파이프라인이 실제로 작동함을 확인")
    st.markdown(
        "<div class='warn-note'><b>왜 정신과 실데이터가 아닌가?</b> 한국의 정신과 EMR은 "
        "민감정보(개인정보보호법)·IRB 승인 대상이라 아이디어 검증 단계에서 사용할 수 없고, "
        "사용해서도 안 됩니다. 대신 <b>같은 구조의 과제(퇴원 → 30일 내 재입원 예측)</b>인 "
        "공개 실환자 데이터로 전처리→학습→평가→SHAP 파이프라인 전체를 검증했습니다. "
        "<b>솔직한 한계:</b> UCI는 당뇨 코호트라 정신과와 <b>도메인이 다르며</b>, 여기서 "
        "보여주는 것은 ‘예측 정확도’가 아니라 <b>‘실데이터에서 파이프라인이 그대로 돈다’</b>는 "
        "사실입니다. 정신과 도메인 정렬은 다음 단계인 <b>HIRA 환자표본자료(정신·행동장애 "
        "F코드)</b>로, 실사용 성능은 <b>병원 EMR(FHIR) 온프레미스 재학습</b>으로 확보합니다 "
        "(⑤탭 사업화·실증 로드맵 참조).</div>",
        unsafe_allow_html=True)
    st.markdown("")

    with st.spinner("실데이터(약 7만 명) 학습 중… 최초 1회만 수행됩니다"):
        res_u, gi_u = load_uci_all()
    mu = res_u["metrics"]

    st.markdown(
        f"<div class='card'><b>데이터 출처</b> : UCI Machine Learning Repository #296 · "
        "<i>Diabetes 130-US Hospitals (1999–2008)</i><br>"
        "미국 130개 병원의 <b>실제 입원 환자</b> 기록 (비식별 처리 완료 · CC BY 4.0 공개 라이선스)<br>"
        f"전처리 후 <b>{len(res_u['df']):,}명</b> (사망·호스피스 퇴원 제외, 환자당 1건으로 "
        "중복 제거 → 데이터 누수 방지, 인종 등 민감 속성 의도적 제외)<br>"
        f"<span style='color:{MUTED}'>Strack et al., BioMed Research International, 2014 · "
        "<a href='https://archive.ics.uci.edu/dataset/296' target='_blank'>"
        "archive.ics.uci.edu/dataset/296</a></span></div>", unsafe_allow_html=True)
    st.markdown("")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("실데이터 코호트", f"{len(res_u['df']):,}명")
    k2.metric("30일 재입원율", f"{mu['prevalence']:.1%}")
    k3.metric("AUROC", f"{mu['auroc']:.3f}")
    k4.metric("AUPRC", f"{mu['auprc']:.3f}")
    st.caption(f"홀드아웃 {mu['n_test']:,}명 평가. 원 논문(Strack et al. 2014) 보고 성능과 "
               "동일 수준 : 과장 없는 정직한 결과입니다. 30일 재입원은 원래 예측이 어려운 "
               "과제이며(정신과 영역에서도 문헌 보고 AUROC 0.68~0.75 수준), 핵심은 수치가 "
               "아니라 실데이터에서 파이프라인이 작동한다는 사실입니다.")

    cL, cR = st.columns(2)
    with cL:
        st.markdown("#### ROC : 합성 코호트 vs 실데이터")
        fpr_s, tpr_s = METRICS["roc"]
        fpr_u, tpr_u = mu["roc"]
        rocu = go.Figure()
        rocu.add_trace(go.Scatter(x=fpr_s, y=tpr_s, mode="lines", name=f"합성 정신과 코호트 (AUROC {METRICS['auroc']:.2f})",
                                  line=dict(color=SKY_DK, width=3)))
        rocu.add_trace(go.Scatter(x=fpr_u, y=tpr_u, mode="lines", name=f"UCI 실데이터 (AUROC {mu['auroc']:.2f})",
                                  line=dict(color=VERM, width=3)))
        rocu.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="무작위",
                                  line=dict(color="#cbd5e1", dash="dash")))
        rocu.update_layout(height=360, xaxis_title="위양성률", yaxis_title="민감도",
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           font=dict(color=BODY), legend=dict(y=0.08, x=0.35))
        st.plotly_chart(rocu, use_container_width=True)
    with cR:
        st.markdown("#### 실데이터 SHAP 전역 중요도")
        giu = gi_u[:10][::-1]
        baru = go.Figure(go.Bar(
            x=[v for _, v in giu], y=[l for l, _ in giu], orientation="h",
            marker_color=CYAN,
            text=[f"{v:.2f}" for _, v in giu], textposition="outside"))
        baru.update_layout(height=360, xaxis_title="평균 |SHAP|",
                           margin=dict(l=10, r=10, t=10, b=30),
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           font=dict(color=BODY))
        st.plotly_chart(baru, use_container_width=True)
        st.caption("실데이터에서도 ‘과거 입원 횟수·재원일수·퇴원 형태’가 핵심 위험요인으로 "
                   "학습됨 : 합성 코호트의 설계 가정 및 정신과 재입원 ML 문헌의 상위 피처"
                   "(과거입원·의료이용·퇴원형태·동반질환, Morel et al. 2020)와 일치.")

    st.markdown("---")
    st.markdown("#### 피처 스키마 사상 : 합성 정신과 코호트 ↔ 실데이터 (동일 구조 증명)")
    map_df = pd.DataFrame(FEATURE_MAPPING,
                          columns=["개념", "합성 정신과 코호트", "UCI 실데이터"])
    st.dataframe(map_df, use_container_width=True, height=320)
    st.caption("같은 개념 축(입원이력·응급·외래·복약·동반질환)으로 사상되므로, 실 병원 EMR로 "
               "교체 시 스키마 매핑만으로 동일 파이프라인이 학습됩니다.")

    st.markdown("---")
    st.markdown("#### 실데이터 연결 ② : 식약처 ‘의약품개요정보(e약은요)’ 공공 API")
    api_on = drug_api.api_available()
    status = ("🟢 실시간 연동 중 (DATA_GO_KR_API_KEY 설정됨)" if api_on
              else "🟡 오프라인 스냅샷 모드 (키 설정 시 실시간 API로 자동 전환)")
    st.markdown(
        f"<div class='card'>Track 1 건강문해력(RAG)의 약물 설명 근거로 <b>식약처 공식 "
        f"공공 데이터</b>를 사용합니다.<br>상태: <b>{status}</b><br>"
        f"<span style='color:{MUTED}'>공공데이터포털(data.go.kr) · 의약품개요정보(e약은요) · "
        f"개인정보 아님 → 규제 이슈 없음</span></div>", unsafe_allow_html=True)
    st.markdown("")
    pick = st.selectbox("의약품 조회 데모", drug_api.KNOWN_DRUGS, index=0)
    info = drug_api.lookup(pick)
    if info:
        src = "실시간 API" if info["source"] == "live" else "스냅샷(폴백)"
        st.markdown(f"**{info['name']}** : 출처: 식약처 e약은요 · {src}")
        st.markdown(f"- 효능: {info['efficacy']}")
        st.markdown(f"- 복용법: {info['usage']}")
        st.markdown(f"- 주의: {info['caution']}")
    st.caption("조회 결과는 ‘쉬운 설명’에만 사용하며 처방·용량 판단에 사용하지 않습니다(가드레일).")


# ================================================================ ⑦ 신규 환자 입력·예측
def _predict_rows(raw_df):
    """
    원시 입력(진단명 + 수치/이진 피처) DataFrame → 위험확률·Track·밴드 부여.
    학습된 모델을 그대로 사용 : '데이터가 들어오면 즉시 예측'되는 운영 흐름 시연.
    """
    feat = raw_df.copy()
    for d in DIAGNOSES:
        feat[f"dx_{d}"] = (feat["diagnosis"] == d).astype(int)
    X_new = feat[FEATURE_COLS].astype(float)
    prob = res["model"].predict_proba(X_new)[:, 1]
    out = raw_df.copy()
    out["risk_prob"] = prob
    out["track"] = np.where(prob >= TRACK2_THRESHOLD, "Track 2", "Track 1")
    out["band"] = [assign_band(p) for p in prob]
    return out, X_new


with tabs[6]:
    tab_intro("새 환자 값을 <b>직접 넣거나 CSV로 올리면</b>, 학습된 모델이 즉시 위험도를 계산합니다. "
              "값을 바꿔가며 결과가 어떻게 변하는지 직접 실험해 보세요.")
    st.markdown("### 신규 환자 데이터 입력 → 실시간 위험도 예측")
    st.markdown(
        "<div class='safe-note'>실서비스에서는 병원 EMR(FHIR)에서 퇴원 시점에 <b>자동으로 "
        "데이터가 유입</b>되며, 환자 본인의 앱 입력에 의존하지 않습니다(신청서 차별성). "
        "이 탭은 그 유입 순간을 시연합니다 : 담당자가 값을 넣거나 CSV를 올리면 "
        "학습된 모델이 <b>즉시</b> 위험확률과 Track을 산출합니다.</div>",
        unsafe_allow_html=True)
    st.markdown("")

    mode = st.radio("입력 방식", ["직접 입력 (1명)", "CSV 일괄 업로드"],
                    horizontal=True)

    if mode == "직접 입력 (1명)":
        with st.form("new_patient"):
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                st.markdown("**인구학·진단**")
                in_dx = st.selectbox("진단", DIAGNOSES)
                in_age = st.number_input("연령", 18, 90, 46)
                in_male = st.selectbox("성별", ["남", "여"]) == "남"
            with f2:
                st.markdown("**입원·응급 이력**")
                in_adm = st.number_input("과거 입원 횟수", 0, 15, 1)
                in_los = st.number_input("이번 재원일수(일)", 3, 120, 21)
                in_ed = st.number_input("최근 1년 응급실 방문", 0, 10, 1)
                in_invol = st.checkbox("비자발(강제) 입원")
            with f3:
                st.markdown("**외래·복약**")
                in_opv = st.number_input("최근 1년 외래 방문", 0, 30, 5)
                in_noshow = st.slider("외래 미방문율(no-show)", 0.0, 1.0, 0.25)
                in_meds = st.number_input("정신과 약물 수", 1, 8, 2)
                in_pdc = st.slider("복약 보유율(PDC)", 0.0, 1.0, 0.70)
                in_disc = st.checkbox("과거 치료중단 이력")
            with f4:
                st.markdown("**사회경제·접근성**")
                in_alone = st.checkbox("독거")
                in_care = st.checkbox("보호자 있음", value=True)
                in_medicaid = st.checkbox("의료급여 수급")
                in_subst = st.checkbox("물질사용 동반")
                in_dist = st.number_input("거주지-시설 거리(km)", 0.5, 90.0, 12.0)
                in_cci = st.number_input("동반질환 지수(Charlson)", 0, 6, 0)
            submitted = st.form_submit_button("위험도 예측", type="primary",
                                              use_container_width=True)

        if submitted:
            raw = pd.DataFrame([{
                "diagnosis": in_dx, "age": in_age, "sex_male": int(in_male),
                "prior_admissions": in_adm, "index_los": in_los,
                "prior_ed_visits": in_ed, "outpatient_visits_1y": in_opv,
                "prior_noshow_rate": in_noshow, "n_psych_meds": in_meds,
                "med_pdc": in_pdc, "distance_km": in_dist, "charlson": in_cci,
                "prior_discontinuation": int(in_disc), "lives_alone": int(in_alone),
                "has_caregiver": int(in_care), "medicaid": int(in_medicaid),
                "involuntary_admission": int(in_invol),
                "substance_use": int(in_subst),
            }])
            pred, X_new = _predict_rows(raw)
            p = float(pred.loc[0, "risk_prob"])
            trk = pred.loc[0, "track"]; bnd = pred.loc[0, "band"]

            r1, r2 = st.columns([1, 2])
            with r1:
                st.markdown(f"<span class='pill-track' style='font-size:1.0rem'>{trk}</span>  "
                            f"<span class='pill' style='background:{BAND_COLORS[bnd]}'>{bnd}</span>",
                            unsafe_allow_html=True)
                st.metric("치료중단/재입원 위험확률", f"{p*100:.0f} %")
                st.caption(band_description(bnd))
                st.markdown("**권고 경로**")
                st.markdown("- Track 1 → 생성형 AI 건강문해력 지원 (④ 탭)"
                            if trk == "Track 1" else
                            "- Track 2 → 의료사회복지사 컨설트 자동 생성 (④ 탭)")
            with r2:
                st.markdown("**이 예측의 SHAP 근거 (top 8)**")
                pack_new = compute_shap(res["model"], X_new)
                sp_new = patient_shap(pack_new, X_new, 0)[:8][::-1]
                colors = [DANGER if s > 0 else SKY for _, s, _ in sp_new]
                wfn = go.Figure(go.Bar(
                    x=[s for _, s, _ in sp_new],
                    y=[f"{l} = {v:g}" for l, s, v in sp_new],
                    orientation="h", marker_color=colors,
                    text=[f"{s:+.2f}" for _, s, _ in sp_new], textposition="outside"))
                wfn.update_layout(height=340, xaxis_title="SHAP 기여 (→ 위험↑ / ← 위험↓)",
                                  margin=dict(l=10, r=10, t=10, b=30),
                                  paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)",
                                  font=dict(color=BODY))
                st.plotly_chart(wfn, use_container_width=True)
            st.caption("PDC·no-show·독거 값을 바꿔 다시 예측해 보세요 : 위험확률과 "
                       "SHAP 근거가 실시간으로 바뀝니다.")

    else:
        RAW_COLS = ["diagnosis"] + NUMERIC_COLS + BINARY_COLS
        st.markdown("**① 템플릿을 내려받아 → ② 환자 행을 채워 → ③ 업로드하면 일괄 예측됩니다.**")
        template = DF[RAW_COLS].head(5).copy()
        st.download_button("입력 템플릿 CSV 내려받기 (예시 5행 포함)",
                           template.to_csv(index=False).encode("utf-8-sig"),
                           file_name="신규환자_입력템플릿.csv", mime="text/csv")
        up = st.file_uploader("환자 데이터 CSV 업로드", type=["csv"])
        if up is not None:
            try:
                raw = pd.read_csv(up)
            except Exception as e:
                st.error(f"CSV를 읽을 수 없습니다: {e}")
                raw = None
            if raw is not None:
                missing = [c for c in RAW_COLS if c not in raw.columns]
                if missing:
                    st.error(f"필수 컬럼 누락: {', '.join(missing)} : 템플릿 형식을 사용해 주세요.")
                elif not raw["diagnosis"].isin(DIAGNOSES).all():
                    bad = raw.loc[~raw["diagnosis"].isin(DIAGNOSES), "diagnosis"].unique()
                    st.error(f"알 수 없는 진단명: {', '.join(map(str, bad))} "
                             f"(가능: {', '.join(DIAGNOSES)})")
                else:
                    try:
                        pred, _ = _predict_rows(raw[RAW_COLS])
                    except (ValueError, TypeError) as e:
                        st.error("수치 컬럼에 숫자로 변환할 수 없는 값이 있습니다. "
                                 f"템플릿 형식(숫자/0·1)을 확인해 주세요. (상세: {e})")
                        pred = None
                    if pred is not None:
                        n2 = int((pred["track"] == "Track 2").sum())
                        st.success(f"{len(pred)}명 예측 완료 : Track 2(고위험) {n2}명 · "
                                   f"Track 1 {len(pred)-n2}명")
                        view = pred.copy()
                        view["위험%"] = (view["risk_prob"] * 100).round(0)
                        view = view.rename(columns={
                            "diagnosis": "진단", "track": "Track", "band": "위험밴드",
                            "age": "연령", "prior_admissions": "과거입원",
                            "prior_noshow_rate": "외래미방문율", "med_pdc": "복약보유율",
                            "lives_alone": "독거"})
                        show = ["진단", "연령", "과거입원", "외래미방문율",
                                "복약보유율", "독거", "위험%", "위험밴드", "Track"]
                        st.dataframe(view[show].sort_values("위험%", ascending=False),
                                     use_container_width=True, height=380)
                        st.download_button("예측 결과 CSV 내려받기",
                                           pred.to_csv(index=False).encode("utf-8-sig"),
                                           file_name="예측결과.csv", mime="text/csv")
        st.caption("실서비스에서는 이 단계가 병원 EMR(FHIR Bundle) 수신으로 자동화됩니다 : "
                   "CSV 업로드는 그 유입 지점을 대신 시연하는 것입니다.")


# ================================================================ 출처·라이선스·참고문헌
st.markdown("---")
st.markdown(
    f"<div class='card' style='background:{SURFACE}'>"
    f"<b style='color:{INK};font-size:1.02rem'>📚 데이터 출처 · 라이선스 · 참고문헌</b>"
    f"<ul style='margin:10px 0 2px;font-size:0.86rem;line-height:1.85'>"
    f"<li><b>합성 정신과 퇴원 코호트</b> (본문 대시보드, 1,500건) : 자체 생성"
    f" (<code>data_generator.py</code>). 임상적으로 알려진 위험요인(복약순응도·과거입원·"
    f"독거·외래 미방문 등)의 <b>방향성</b>을 반영해 설계한 <b>가상 데이터이며, 실제 환자 자료가"
    f" 아닙니다</b>(특정 논문 수치를 그대로 인용하지 않음).</li>"
    f"<li><b>UCI #296 · Diabetes 130-US Hospitals (1999–2008)</b> : 미국 130개 병원 "
    f"실환자 공개데이터 · 라이선스 <b>CC BY 4.0</b> · Strack et al., <i>BioMed Research "
    f"International</i>, 2014 · "
    f"<a href='https://archive.ics.uci.edu/dataset/296' target='_blank'>"
    f"archive.ics.uci.edu/dataset/296</a></li>"
    f"<li><b>식약처 의약품개요정보(e약은요)</b> : 공공데이터포털 공개 API(개인정보 아님) · "
    f"<a href='https://www.data.go.kr' target='_blank'>data.go.kr</a></li>"
    f"<li><b>글꼴</b> : 아리따 부리(Arita Buri), 아모레퍼시픽 무료 배포 · "
    f"<a href='https://www.apgroup.com/int/ko/about-us/visual-identity/arita-typeface/"
    f"arita-typeface.html' target='_blank'>apgroup.com</a></li>"
    f"<li><b>소스 코드</b> : GitHub 공개 저장소 · "
    f"<a href='https://github.com/tiltis/bio-challenge-2026' target='_blank'>"
    f"github.com/tiltis/bio-challenge-2026</a></li>"
    f"</ul>"
    f"<div class='refs' style='margin-top:10px;border-top:1px solid {BORDER};padding-top:10px'>"
    f"<b>피처 설계·모델 선택·성능 기준의 학술 근거</b> "
    f"<span style='font-size:0.94em'>(서지·수치 원문 대조 완료)</span><br>"
    f"[1] Donisi V, Tedeschi F, Wahlbeck K, Haaramo P, Amaddeo F. Pre-discharge factors "
    f"predicting readmissions of psychiatric patients: a systematic review of the literature. "
    f"<i>BMC Psychiatry</i>. 2016 Dec 16;16(1):449. doi:10.1186/s12888-016-1114-0. "
    f"PMID:27986079. : 과거 입원력이 가장 일관된 재입원 예측인자.<br>"
    f"[2] Morel D, Yu KC, Liu-Ferrara A, Caceres-Suriel AJ, Kurtz SG, Tabak YP. Predicting "
    f"hospital readmission in patients with mental or substance use disorders: a machine "
    f"learning approach. <i>Int J Med Inform</i>. 2020 Jul;139:104136. "
    f"doi:10.1016/j.ijmedinf.2020.104136. PMID:32353752. : 65,426명 분석, "
    f"XGBoost AUROC 0.738 vs GLMNet 0.697; 상위 피처: 과거입원·의료이용·퇴원형태·진단·동반질환.<br>"
    f"[3] Boag W, Kovaleva O, McCoy TH Jr, Rumshisky A, Szolovits P, Perlis RH. Hard for "
    f"humans, hard for machines: predicting readmission after psychiatric hospitalization "
    f"using narrative notes. <i>Transl Psychiatry</i>. 2021 Jan 11;11(1):32. "
    f"doi:10.1038/s41398-020-01104-w. PMID:33431794. : 인구학 기반 AUC 0.675로 "
    f"정신과 재입원 예측의 본질적 난이도 확인.<br>"
    f"[4] Ren B, Yoon W, Thomas S, Savova G, Miller T, Hall MH. Cross-site predictions of "
    f"readmission after psychiatric hospitalization with mood or psychotic disorders: "
    f"retrospective study. <i>JMIR Ment Health</i>. 2025 Sep 12;12:e71630. "
    f"doi:10.2196/71630. PMID:40939119. : 기관 간 모델 이식성 한계 → 병원별 "
    f"site-specific 학습 필요.<br>"
    f"[5] Strack B, DeShazo JP, Gennings C, et al. Impact of HbA1c measurement on hospital "
    f"readmission rates: analysis of 70,000 clinical database patient records. "
    f"<i>BioMed Res Int</i>. 2014;2014:781670. doi:10.1155/2014/781670. : ⑥ 탭 실데이터"
    f"(UCI #296) 원 논문."
    f"</div></div>", unsafe_allow_html=True)
st.caption("2026 연구 아이디어 기술사업화 챌린지 · 경북대학교병원 팀 · 개념검증(PoC) 데모")
