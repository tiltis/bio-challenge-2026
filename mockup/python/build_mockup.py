# -*- coding: utf-8 -*-
# LinkCure 앱 목업 생성기.
# mockup_config.py 의 값을 수정한 뒤 이 파일을 실행하면(python build_mockup.py)
# 같은 폴더에 목업 HTML이 생성된다. ../src/ 폴더(fonts.css, styles.css, editor.js) 필요.
from pathlib import Path
import mockup_config as C

SRC = Path(__file__).resolve().parent.parent / "src"

# mockup_config.py 의 icon 이름과 대응하는 SVG
ICONS = {
    "patients": '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "pulse": '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
    "pill": '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M10.5 20.5L3 13a5 5 0 0 1 7-7l.5.5.5-.5a5 5 0 0 1 7 7l-3 3"/><rect x="13" y="13" width="8" height="8" rx="2"/><path d="M17 15v4M15 17h4"/></svg>',
    "home": '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/></svg>',
    "share": '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/></svg>',
    "chat": '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "calendar": '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
    "bell": '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>',
    "gear": '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8"/><circle cx="12" cy="12" r="3"/></svg>',
}
TILE_ICONS = {
    "b": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.7"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
    "r": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.7"><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></svg>',
    "g": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.7"><path d="M4 12h10M10 6l6 6-6 6"/><path d="M20 4v16"/></svg>',
}
LIFE_ICONS = {
    "calendar_check": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/><path d="M9 16l2 2 4-4"/></svg>',
    "moon": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z"/></svg>',
    "bell": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>',
    "share": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 12h10M10 6l6 6-6 6"/><path d="M20 4v16"/></svg>',
}
NAV = [
    ("홈",   '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'),
    ("환자", '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'),
    ("지도", '<path d="M10.5 20.5L3 13a5 5 0 0 1 7-7l2 2 2-2a5 5 0 0 1 7 7l-7.5 7.5z"/>'),
    ("알림", '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/>'),
    ("내정보", '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 12 0v1"/>'),
]

STATUS_BAR = '''<div class="status">
  <span>9:41</span>
  <span class="dots">
    <svg width="17" height="12" viewBox="0 0 17 12"><g fill="#1b2432"><rect x="0" y="7" width="3" height="5" rx="1"/><rect x="4.5" y="4.5" width="3" height="7.5" rx="1"/><rect x="9" y="2" width="3" height="10" rx="1"/><rect x="13.5" y="0" width="3" height="12" rx="1"/></g></svg>
    <svg width="22" height="12" viewBox="0 0 22 12"><rect x="0.5" y="1" width="18" height="10" rx="2.5" fill="none" stroke="#1b2432" stroke-width="1.2"/><rect x="2" y="2.5" width="13" height="7" rx="1" fill="#1b2432"/><rect x="19.5" y="4" width="2" height="4" rx="1" fill="#1b2432"/></svg>
  </span>
</div>'''


def nav_bar(active):
    out = ['<div class="nav">']
    for label, path in NAV:
        cls = ' class="on"' if label == active else ''
        out.append(f'<a{cls}><svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">{path}</svg><span class="nl">{label}</span></a>')
    out.append('</div>')
    return "\n".join(out)


def risk_badge(risk):
    arrow = "▲" if risk == "hi" else "▼"
    text = "관리취약" if risk == "hi" else "관리일반"
    return f'<span class="risk {risk}"><span class="ar">{arrow}</span>{text}</span>'


def phone1():
    tiles = "".join(
        f'<div class="tile {t["color"]}"><span class="lab">{t["label"]}</span>'
        f'<span class="big">{t["value"]}<span class="u">{t["unit"]}</span></span>'
        f'<span class="ti">{TILE_ICONS[t["color"]]}</span></div>'
        for t in C.TILES)
    on = ' class="on"'
    tabs = "".join(f'<span{on if i == 0 else ""}>{t}</span>' for i, t in enumerate(C.HOME_TABS))
    grid = ""
    for g in C.GRID:
        badge = f'<span class="dot">{g["badge"]}</span>' if g["badge"] else ""
        cls = "ci badge" if g["badge"] else "ci"
        grid += f'<div class="gitem"><div class="{cls}">{badge}{ICONS[g["icon"]]}</div><span class="gl">{g["label"]}</span></div>'
    pv = "".join(f'<li><b>{k}</b>: {v}</li>' for k, v in C.PRIVACY_ITEMS)
    return f'''<div class="phone"><div class="notch"></div><div class="screen">
{STATUS_BAR}
<div class="body">
  <div class="hdr-home">
    <div class="brand"><span class="kr">{C.HOSPITAL_KR}</span><span class="en">{C.HOSPITAL_EN}</span></div>
    <span class="role-chip">{C.ROLE_CHIP}</span>
  </div>
  <div class="tiles">{tiles}</div>
  <div class="htabs">{tabs}</div>
  <div class="grid">{grid}</div>
  <div class="home-foot"><div class="privacy">
    <div class="pv-head">
      <span class="pv-ic"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg></span>
      <span class="pv-t">{C.PRIVACY_TITLE}</span><span class="pv-badge">{C.PRIVACY_BADGE}</span>
    </div>
    <ul class="pv-list">{pv}</ul>
    <div class="pv-foot">
      <span class="ck"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg></span>
      <span>{C.PRIVACY_AGREE}</span><span class="mng">동의 관리<span class="cv"></span></span>
    </div>
  </div></div>
</div>
{nav_bar("홈")}
</div></div>'''


def phone2():
    sums = "".join(
        f'<div class="s"><div class="sv{(" " + s["tone"]) if s["tone"] else ""}">{s["value"]}</div><div class="sl">{s["label"]}</div></div>'
        for s in C.SUMMARY)
    chips = "".join(f'<span class="chip{" on" if i == 0 else ""}">{c}</span>' for i, c in enumerate(C.CHIPS))
    cards = ""
    for p in C.PATIENTS:
        edge = "hiedge" if p["risk"] == "hi" else "loedge"
        ins_cls, ins_txt = p["insurance"]
        tags = "".join(f'<span class="tag">{t}</span>' for t in p["tags"])
        cards += f'''<div class="pcard {edge}">
  <div class="prow1"><span class="pname">{p["name"]}<span class="meta">{p["meta"]}</span></span>{risk_badge(p["risk"])}</div>
  <div class="prow2"><span class="ins {ins_cls}">{ins_txt}</span>{tags}</div>
  <div class="prow3"><span class="risknum">{p["dday"]}</span><span class="go">복약·생활지도<span class="cv"></span></span></div>
</div>'''
    return f'''<div class="phone"><div class="notch"></div><div class="screen">
{STATUS_BAR}
<div class="hdr-bar"><span class="ic-back"></span><span class="t">{C.PHONE2_TITLE}</span><span class="hmb"></span></div>
<div class="body">
  <div class="sum">{sums}</div>
  <div class="chips">{chips}</div>
  <div class="plist">{cards}</div>
</div>
{nav_bar("환자")}
</div></div>'''


def phone3():
    life = "".join(
        f'<div class="lrow"><span class="lic">{LIFE_ICONS[i["icon"]]}</span>'
        f'<span class="lt"><span class="lh">{i["title"]}</span><span class="lp">{i["desc"]}</span></span></div>'
        for i in C.LIFE_ITEMS)
    return f'''<div class="phone"><div class="notch"></div><div class="screen">
{STATUS_BAR}
<div class="hdr-bar"><span class="ic-back"></span><span class="t">{C.PHONE3_TITLE}</span><span class="hmb"></span></div>
<div class="body">
  <div class="pt-head">
    <span class="avatar">{C.PT_AVATAR}</span>
    <span class="info"><span class="nm">{C.PT_NAME}</span><span class="mt">{C.PT_META}</span></span>
    {risk_badge(C.PT_RISK)}
  </div>
  <div class="sec">
    <div class="sec-t"><span class="ai">AI</span><h4>{C.MED_SECTION_TITLE}</h4></div>
    <div class="gcard">
      <div class="orig"><div class="ol">퇴원 처방 원문</div><div class="ot">{C.MED_ORIGINAL}</div></div>
      <div class="plain">
        <div class="pl"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>쉬운 설명</div>
        <div class="pt">{C.MED_PLAIN}</div>
        <div class="warn"><span class="k"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></svg></span>{C.MED_WARNING}</div>
      </div>
    </div>
  </div>
  <div class="sec">
    <div class="sec-t"><span class="ai">AI</span><h4>{C.LIFE_SECTION_TITLE}</h4></div>
    <div class="life">{life}</div>
  </div>
  <div class="guard">
    <span class="k"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></span>
    <span>{C.GUARD_TEXT}</span>
  </div>
  <div class="deliver"><button class="primary">{C.BUTTON_PRIMARY}</button><button class="ghost">{C.BUTTON_GHOST}</button></div>
</div>
{nav_bar("지도")}
</div></div>'''


def build():
    fonts = (SRC / "fonts.css").read_text(encoding="utf-8")
    styles = (SRC / "styles.css").read_text(encoding="utf-8")
    editor = (SRC / "editor.js").read_text(encoding="utf-8")
    white = ".wrap{background:#ffffff !important}" if C.WHITE_BACKGROUND else ""

    cols = ""
    for phone, cap in zip((phone1(), phone2(), phone3()), C.CAPTIONS):
        cols += f'<div class="col">{phone}<div class="cap"><span class="n">{cap["n"]}</span><h3>{cap["title"]}</h3><p>{cap["desc"]}</p></div></div>\n'

    html = f'''<meta charset="utf-8">
<title>{C.TITLE}</title>
<!-- 이 파일은 build_mockup.py 가 자동 생성했습니다. 직접 고치지 말고 mockup_config.py 를 수정하세요. -->
<style>
{fonts}
{styles}
{white}
</style>
<div class="wrap">
  <div class="ribbon-row"><div class="ribbon">{C.RIBBON}<span class="rib-sub">{C.RIBBON_SUB}</span></div></div>
  <p class="deck">{C.DECK}</p>
  <div class="board">
{cols}
  </div>
  <p class="foot">{C.FOOT}</p>
</div>
<div id="mk-toolbar">
  <button id="mk-edit">✏️ 편집 모드</button>
  <button id="mk-save">💾 저장</button>
  <button id="mk-reset">↺ 처음으로</button>
</div>
<div id="mk-hint"><b>꾹(0.4초) 누른 채 끌기 = 자유 이동</b> · 글자 클릭 = 수정 · 빠른 드래그 = 순서 · Shift+클릭 = 위치 원상복구 · Alt+클릭 = 삭제</div>
<script>
{editor}
</script>
'''
    out = Path(__file__).resolve().parent / C.OUTPUT_FILE
    out.write_text(html, encoding="utf-8")
    print(f"생성 완료: {out}")


if __name__ == "__main__":
    build()
