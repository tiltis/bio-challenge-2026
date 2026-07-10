"""
rag_literacy.py : RAG 기반 건강 문해력 지원 모듈 (Track 1 핵심 기술).

신청서 핵심기술 ②: 생성형 AI 기반 건강 문해력 지원 시스템
- 퇴원요약지·처방전·복약지도서의 어려운 의학용어를 '지식베이스에서 검색(retrieval)'해
  근거를 확보한 뒤, LLM이 그 근거에만 기반해 환자·보호자가 이해하기 쉬운 말로 재구성한다.
- 이것이 RAG(Retrieval-Augmented Generation)다: 환각을 줄이고 설명을 의학적 근거에 고정.

구성:
  1) MEDICAL_KB        : 정신과 퇴원 맥락의 용어 지식베이스(검색 대상 코퍼스)
  2) retrieve()        : 문서에서 등장하는 용어를 검색(근거 수집). API 없이도 항상 동작.
  3) build_document()  : 환자 EMR로부터 합성 퇴원요약/처방 문서 생성(데모 입력)
  4) plain_rewrite()   : 검색 근거 + LLM 으로 쉬운말 재구성. 키 없으면 근거 기반 템플릿 폴백.

규제 가드레일: 진단·처방 변경을 하지 않는다. 기존 문서를 '쉽게 풀어 설명'만 한다.
"""

import os
import re

# ---------------------------------------------------------------- 1) 지식베이스
# 각 항목: key 표준어, aliases 동의어, plain 쉬운설명, caution 주의(선택)
MEDICAL_KB = [
    {"key": "항정신병약물", "aliases": ["항정신병약", "antipsychotic"],
     "plain": "조현병·양극성장애에서 환청·망상 같은 증상을 줄여주는 약입니다.",
     "caution": "임의로 끊으면 증상이 재발할 수 있어, 끊거나 줄일 때는 꼭 의료진과 상의하세요."},
    {"key": "클로자핀", "aliases": ["clozapine", "클로자릴"],
     "plain": "다른 약으로 잘 조절되지 않을 때 쓰는 강력한 조현병 치료제입니다.",
     "caution": "정기적인 혈액검사가 필요하니 예약된 검사일을 꼭 지켜 주세요."},
    {"key": "리튬", "aliases": ["lithium", "탄산리튬"],
     "plain": "기분의 큰 오르내림(조증·우울)을 안정시키는 양극성장애 치료제입니다.",
     "caution": "물을 충분히 마시고, 혈중농도 검사를 정기적으로 받아야 합니다."},
    {"key": "SSRI", "aliases": ["에스에스알아이", "선택적세로토닌재흡수억제제"],
     "plain": "우울·불안을 완화하는 대표적인 항우울제 계열입니다.",
     "caution": "효과는 보통 2~4주 뒤 나타나니, 바로 효과가 없어도 임의 중단하지 마세요."},
    {"key": "데포주사", "aliases": ["장기지속형주사", "depot", "LAI", "장기지속형"],
     "plain": "매일 약을 챙기기 어려울 때, 2~4주에 한 번 맞아 효과가 유지되는 주사입니다.",
     "caution": "다음 주사 예약일을 놓치지 않는 것이 가장 중요합니다."},
    {"key": "기분조절제", "aliases": ["기분안정제", "mood stabilizer"],
     "plain": "기분이 지나치게 들뜨거나 가라앉지 않도록 잡아주는 약입니다."},
    {"key": "벤조디아제핀", "aliases": ["benzodiazepine", "항불안제", "신경안정제"],
     "plain": "불안·불면을 빠르게 완화하는 약입니다.",
     "caution": "오래 쓰면 의존이 생길 수 있어, 정해진 양만 드세요."},
    {"key": "PRN", "aliases": ["피알엔", "필요시"],
     "plain": "정해진 시간이 아니라 '증상이 있을 때만' 먹는 약이라는 뜻입니다."},
    {"key": "1일 2회", "aliases": ["bid", "하루 두 번", "1일2회"],
     "plain": "하루에 두 번, 보통 아침과 저녁에 드시는 것을 의미합니다."},
    {"key": "1일 3회", "aliases": ["tid", "하루 세 번", "1일3회"],
     "plain": "하루에 세 번, 보통 아침·점심·저녁 식후에 드시는 것을 의미합니다."},
    {"key": "취침 전", "aliases": ["hs", "자기 전", "취침전"],
     "plain": "잠자리에 들기 직전에 드시라는 뜻입니다."},
    {"key": "추체외로증상", "aliases": ["EPS", "이상운동", "떨림"],
     "plain": "약 때문에 손 떨림·근육 뻣뻣함·안절부절 같은 부작용이 생기는 것을 말합니다.",
     "caution": "이런 증상이 생기면 참지 말고 담당 의료진에게 알려 주세요."},
    {"key": "외래 추적관찰", "aliases": ["외래", "f/u", "추적관찰", "외래 예약"],
     "plain": "퇴원 후에도 병원에 정기적으로 방문해 상태를 점검하는 것을 말합니다.",
     "caution": "예약된 외래 방문을 빠뜨리면 재발 위험이 커집니다."},
    {"key": "복약 순응도", "aliases": ["복약순응도", "adherence", "복약 이행"],
     "plain": "처방받은 약을 정해진 대로 잘 챙겨 먹는 정도를 뜻합니다."},
    {"key": "재발 징후", "aliases": ["재발징후", "warning sign", "조기경고증상"],
     "plain": "병이 다시 나빠지기 전에 나타나는 신호(불면·불안·환청 재출현 등)입니다.",
     "caution": "이런 신호가 보이면 다음 예약을 기다리지 말고 빨리 연락하세요."},
    {"key": "정신건강복지센터", "aliases": ["정신건강복지센터", "정신건강센터"],
     "plain": "지역사회에서 정신질환자의 회복과 생활을 돕는 공공 기관입니다."},
]

# 빠른 검색용 (별칭 → 항목)
_ALIAS_INDEX = []
for _e in MEDICAL_KB:
    for _a in [_e["key"]] + _e["aliases"]:
        _ALIAS_INDEX.append((_a, _e))
# 긴 별칭 먼저 매칭(부분 겹침 방지)
_ALIAS_INDEX.sort(key=lambda t: -len(t[0]))


# ---------------------------------------------------------------- 2) 검색(retrieval)
def retrieve(document_text):
    """
    문서에서 지식베이스 용어를 검색해 근거 목록 반환(중복 제거, 등장 순서 유지).
    반환: [{"key","plain","caution"}...]  : RAG의 'R' 단계, 오프라인에서도 항상 동작.
    """
    text = document_text or ""
    found, seen = [], set()
    # 등장 위치 기준 정렬
    hits = []
    low = text.lower()
    for alias, entry in _ALIAS_INDEX:
        pos = low.find(alias.lower())
        if pos != -1 and entry["key"] not in seen:
            seen.add(entry["key"])
            hits.append((pos, entry))
    hits.sort(key=lambda t: t[0])
    for _, entry in hits:
        found.append({"key": entry["key"], "plain": entry["plain"],
                      "caution": entry.get("caution", "")})
    return found


# ---------------------------------------------------------------- 3) 데모 문서 생성
# 실제 성분명 표기 → drug_api(식약처 e약은요)에서 약물 정보를 조회할 수 있게 함
_DIAG_MEDS = {
    "조현병": ["항정신병약물(올란자핀) 1일 2회", "데포주사(팔리페리돈, 4주 간격)",
             "PRN 항불안제(로라제팜)"],
    "양극성장애": ["탄산리튬 1일 2회", "기분조절제(발프로산) 1일 2회",
               "취침 전 수면제(졸피뎀)"],
    "우울장애": ["SSRI(에스시탈로프람) 1일 1회", "벤조디아제핀(로라제팜) PRN",
             "취침 전 수면제(졸피뎀)"],
    "불안장애": ["SSRI(에스시탈로프람) 1일 1회", "벤조디아제핀(알프라졸람) 1일 2회 PRN"],
}


def build_document(patient_row):
    """환자 EMR 한 행으로부터 합성 '퇴원요약/복약지도' 문서(원문) 생성."""
    dx = patient_row.get("diagnosis", "우울장애")
    meds = _DIAG_MEDS.get(dx, _DIAG_MEDS["우울장애"])
    los = int(patient_row.get("index_los", 14))
    lines = [
        f"[퇴원요약지] 진단: {dx}. 금번 입원기간 {los}일.",
        f"퇴원 약물: {', '.join(meds)}.",
        "추체외로증상(손 떨림 등) 발생 시 외래 추적관찰 시 보고 요망.",
        "복약 순응도 유지가 중요하며, 재발 징후 발생 시 즉시 내원 권고.",
        "퇴원 2주 내 정신건강의학과 외래 예약 확인. 필요시 정신건강복지센터 연계.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- 4) LLM 재구성(RAG)
SYSTEM_PROMPT = (
    "너는 정신과 퇴원환자와 보호자를 위한 '건강 문해력 지원' 도우미다. "
    "주어진 의료문서를, 함께 제공되는 [의학용어 근거]에만 기반해 쉬운 한국어로 풀어 설명한다.\n"
    "가드레일(반드시 준수):\n"
    "1) 새로 진단하거나 병명을 추정하지 않는다. 문서에 있는 내용만 쉽게 풀어준다.\n"
    "2) 약의 용량·복용법을 바꾸라고 하지 않는다. 임의 중단 금지를 안내한다.\n"
    "3) [의학용어 근거]에 없는 의학 정보를 지어내지 않는다.\n"
    "4) 따뜻하고 차분한 말투로, 중학생도 이해할 수준으로 쓴다.\n"
    "출력 형식: ①한줄 요약 ②약 복용 안내 ③꼭 지킬 점(외래·재발징후) 순의 짧은 단락."
)

MODEL = "claude-opus-4-8"


def plain_rewrite(document_text, patient_context=""):
    """
    검색 근거 + LLM 으로 문서를 쉬운말로 재구성.
    반환: dict(retrieved=[...], text=쉬운말 결과, source="llm"|"template")
    키 없거나 실패 시 근거 기반 템플릿으로 폴백.

    근거는 두 소스를 병합한다:
    ① MEDICAL_KB (정신과 퇴원 맥락 용어)
    ② 식약처 e약은요 실데이터 (문서에 등장하는 실제 약물 : drug_api)
    """
    retrieved = retrieve(document_text)
    try:
        from drug_api import retrieve_drug_info
        retrieved = retrieved + retrieve_drug_info(document_text)
    except Exception:
        pass  # 약물 조회 실패해도 용어 근거만으로 계속 동작
    grounding = "\n".join(
        f"- {r['key']}: {r['plain']}"
        + (f" (주의: {r['caution']})" if r["caution"] else "")
        for r in retrieved)

    text = _llm_rewrite(document_text, grounding, patient_context)
    if text:
        return {"retrieved": retrieved, "text": text, "source": "llm"}
    return {"retrieved": retrieved,
            "text": _template_rewrite(retrieved), "source": "template"}


def _llm_rewrite(document_text, grounding, patient_context):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    user_prompt = (
        f"[환자 맥락] {patient_context}\n\n"
        f"[원본 의료문서]\n{document_text}\n\n"
        f"[의학용어 근거]\n{grounding}\n\n"
        "위 근거에만 기반해, 가드레일을 지키며 환자·보호자가 이해하기 쉬운 "
        "안내문으로 재구성하라."
    )
    try:
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model=MODEL, max_tokens=600, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
        return "".join(parts).strip() or None
    except Exception:
        return None


def _template_rewrite(retrieved):
    """API 없이 검색 근거만으로 쉬운말 안내문 조립(폴백)."""
    if not retrieved:
        return "이 문서에서 풀어 설명할 의학용어를 찾지 못했습니다."
    lines = ["**쉽게 풀어 쓴 안내** (의학용어 근거 기반 자동 생성)\n"]
    cautions = []
    for r in retrieved:
        lines.append(f"- **{r['key']}**: {r['plain']}")
        if r["caution"]:
            cautions.append(f"- {r['key']}: {r['caution']}")
    if cautions:
        lines.append("\n**꼭 지켜 주세요**")
        lines.extend(cautions)
    lines.append("\n※ 이 안내는 기존 퇴원 문서를 쉽게 풀어 설명한 것으로, "
                 "진단·처방을 바꾸지 않습니다. 궁금한 점은 담당 의료진에게 문의하세요.")
    return "\n".join(lines)


if __name__ == "__main__":
    from data_generator import generate
    d = generate()
    row = d.iloc[0]
    doc = build_document(row)
    print("=== 원본 문서 ===\n", doc)
    res = plain_rewrite(doc, f"진단 {row['diagnosis']}, 독거={row['lives_alone']}")
    print(f"\n검색된 용어 {len(res['retrieved'])}개:",
          [r["key"] for r in res["retrieved"]])
    print(f"\n=== 재구성({res['source']}) ===\n", res["text"])
