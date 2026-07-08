"""
drug_api.py — 식약처 '의약품개요정보(e약은요)' 공공 API 연동 (실데이터 연결 ②).

실제 데이터 소스:
- 식품의약품안전처 공공데이터 개방 API (공공데이터포털 data.go.kr, 승인형 무료 키).
  서비스명: DrbEasyDrugInfoService / getDrbEasyDrugList
- 국민 누구나 쓰라고 만든 '쉬운 의약품 설명' 공식 DB → 본 플랫폼 RAG의
  건강 문해력 지식베이스로 그대로 사용 가능 (개인정보 아님 → 규제 이슈 없음).

동작 방식:
- 환경변수 DATA_GO_KR_API_KEY 가 있으면 → 실시간 API 조회 (source="live")
- 없거나 실패하면 → drug_snapshot.json (동일 서비스 내용 요약 스냅샷)으로 폴백
  (source="snapshot") — 데모가 인터넷·키 없이도 항상 동작하도록.

가드레일: 조회 결과는 '설명'에만 사용하며 처방·용량 판단에 사용하지 않는다.
"""

import json
import os
import re
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_PATH = os.path.join(_HERE, "drug_snapshot.json")

API_ENDPOINT = ("http://apis.data.go.kr/1471000/DrbEasyDrugInfoService/"
                "getDrbEasyDrugList")
API_INFO_URL = "https://www.data.go.kr/data/15075057/openapi.do"


def _load_snapshot():
    with open(SNAPSHOT_PATH, encoding="utf-8") as f:
        return json.load(f)


_SNAPSHOT = _load_snapshot()

# 별칭 → 스냅샷 항목 (긴 별칭 우선 매칭)
_ALIAS_INDEX = []
for _d in _SNAPSHOT["drugs"]:
    for _a in [_d["name"]] + _d.get("aliases", []):
        _ALIAS_INDEX.append((_a, _d))
_ALIAS_INDEX.sort(key=lambda t: -len(t[0]))

KNOWN_DRUGS = [d["name"] for d in _SNAPSHOT["drugs"]]


def api_key():
    return os.environ.get("DATA_GO_KR_API_KEY", "").strip()


def api_available():
    return bool(api_key())


def _strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _first_sentences(s, n=2):
    """API 원문(문단)에서 앞 n문장만 추출해 화면용으로 요약."""
    s = _strip_html(s)
    parts = [p.strip() for p in re.split(r"(?<=[.다요])\s+", s) if p.strip()]
    return " ".join(parts[:n])


def fetch_live(item_name, timeout=6):
    """
    e약은요 API 실시간 조회. 성공 시 표준화된 dict, 실패 시 None.
    (승인형 키 필요 — data.go.kr 에서 '의약품개요정보(e약은요)' 활용신청)
    """
    key = api_key()
    if not key:
        return None
    params = urllib.parse.urlencode({
        "serviceKey": key, "itemName": item_name,
        "type": "json", "numOfRows": 1, "pageNo": 1,
    }, safe="%")  # 포털 키는 이미 인코딩된 형태가 흔함
    url = f"{API_ENDPOINT}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        items = (data.get("body") or {}).get("items") or []
        if not items:
            return None
        it = items[0]
        return {
            "name": _strip_html(it.get("itemName", item_name)),
            "efficacy": _first_sentences(it.get("efcyQesitm", "")),
            "usage": _first_sentences(it.get("useMethodQesitm", "")),
            "caution": _first_sentences(it.get("atpnQesitm", "")),
            "source": "live",
        }
    except Exception:
        return None


def lookup(name):
    """
    의약품 1건 조회: 실시간 API 우선, 실패 시 스냅샷 폴백. 없으면 None.
    반환: {"name","efficacy","usage","caution","source"}
    """
    live = fetch_live(name)
    if live and (live["efficacy"] or live["usage"]):
        return live
    low = name.lower()
    for alias, d in _ALIAS_INDEX:
        if alias.lower() in low or low in alias.lower():
            return {"name": d["name"], "efficacy": d["efficacy"],
                    "usage": d["usage"], "caution": d["caution"],
                    "source": "snapshot"}
    return None


def retrieve_drug_info(document_text):
    """
    문서에서 알려진 의약품명을 찾아 각각 조회 (RAG 'R' 단계의 실데이터 소스).
    반환: rag_literacy.retrieve() 와 같은 모양의 리스트
          [{"key","plain","caution","src"}...]  (등장 순서, 중복 제거)
    """
    text = (document_text or "").lower()
    hits, seen = [], set()
    for alias, d in _ALIAS_INDEX:
        pos = text.find(alias.lower())
        if pos != -1 and d["name"] not in seen:
            seen.add(d["name"])
            hits.append((pos, d["name"]))
    hits.sort(key=lambda t: t[0])

    out = []
    for _, name in hits:
        info = lookup(name)
        if info:
            plain = info["efficacy"]
            if info["usage"]:
                plain += f" 복용법: {info['usage']}"
            out.append({"key": f"약물: {info['name']}", "plain": plain,
                        "caution": info["caution"], "src": info["source"]})
    return out


if __name__ == "__main__":
    print(f"API 키 설정됨: {api_available()}  (미설정 시 스냅샷 폴백)")
    doc = "퇴원 약물: 올란자핀 1일 2회, 탄산리튬 1일 2회, 취침 전 졸피뎀."
    for e in retrieve_drug_info(doc):
        print(f"\n[{e['key']}] ({e['src']})")
        print(" ", e["plain"])
        print("  주의:", e["caution"])
