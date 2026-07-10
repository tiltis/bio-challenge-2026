# LinkCure(링큐어) : 정신질환 퇴원환자 사례관리 앱 목업

정신질환 퇴원환자의 **사후관리 취약도**를 퇴원요약지로 산출해, 의료사회복지사가
**우선 개입할 환자**를 확인하고 **복약·생활지도를 쉬운 말로** 전달하는 모바일 앱의 화면 시안입니다.

> 2026 연구 아이디어 기술사업화 챌린지 · 경북대학교병원 팀
> 화면·인물·수치는 전부 **예시**이며 실제 환자 데이터가 아닙니다.

## 이 깃허브를 보시는 팀원분께 ...

**설치·실행 필요 없습니다.** [`mockup/linkcure_mockup_annotated.html`](mockup/linkcure_mockup_annotated.html)을 내려받아 **더블클릭**하면 아래 화면이 브라우저에 바로 열립니다. << 이게 예시 사진으로 보여드린것

<img width="1322" height="1125" alt="image" src="https://github.com/user-attachments/assets/358c13e2-1d88-4fe7-90e2-f82f716ad16f" />

## 목업 화면 구성 (폰 3대)

1. **메인화면 · 오늘의 사례관리** : 담당 현황 타일(오늘 관리 대상 / 신규 관리취약 / 센터 연계 대기), 기능 아이콘, 개인정보 사전 동의 안내
2. **환자 관리 · 관리취약도 & 의료보험** : 관리취약(빨강)/관리일반(초록) 배지, 건강보험·의료급여 구분, 환자 카드 목록
3. **복약·생활지도 · AI 쉬운 해석** : 퇴원 처방 원문 → 쉬운 설명 변환, 생활수칙, 가드레일 문구

## 목업 파일 안내 (`mockup/` 폴더)

| 파일 | 용도 |
|---|---|
| [`linkcure_mockup_annotated.html`](mockup/linkcure_mockup_annotated.html) | **설명용** : 발표·서류 첨부용 기본 시안 |
| [`linkcure_mockup_white.html`](mockup/linkcure_mockup_white.html) | **흰 배경용** : 인쇄·문서 삽입용 |
| [`linkcure_mockup_editor.html`](mockup/linkcure_mockup_editor.html) | **편집용** : 브라우저에서 마우스로 글자·배치 수정 (우측 하단 ✏️) |
| [`src/`](mockup/src/) | **코드 편집용** : HTML/CSS 직접 수정 |
| [`python/`](mockup/python/) | **파이썬 편집용** : PyCharm·VS Code에서 `mockup_config.py` 값만 고쳐서 목업 생성 |

**직접 수정하는 법(A to Z), 캡처·PDF로 만드는 법**은 → **[mockup/README.md](mockup/README.md)** 에 전부 정리되어 있습니다.

**글꼴**: 한글은 페이퍼로지(Paperlogy, HTML에 내장되어 설치 불필요), 영문·숫자는 Times New Roman 두 가지만 사용합니다.

---

## (참고) PoC 데모 대시보드

정신질환 퇴원환자의 90일 내 치료중단·재입원 위험을 병원 EMR로 예측(XGBoost + SHAP)하고,
일반군(Track 1)/고위험군(Track 2)으로 분류해 맞춤 개입을 연계하는 Streamlit 데모입니다.
본 시스템은 **진단 도구가 아니며**, 위험 신호와 Track 배정만 제공합니다.
모든 임상·연계 결정은 의료진과 의료사회복지사가 수행합니다.

### 실행

```bash
pip install -r requirements.txt
streamlit run app.py     # http://localhost:8501
```

- 설치 후에는 `run.bat` 더블클릭으로도 실행됩니다.
- Python 3.12 / Streamlit 1.37 기준. `numpy<2` 핀 유지 필요.
- `python app.py` 직접 실행은 동작하지 않습니다 : 반드시 `streamlit run`.

### 구성

| 파일 | 역할 |
|---|---|
| `app.py` | 7탭 대시보드 (EMR → 위험예측 → 우선개입 대기열 → 개입 연계 → 차별점 → 실데이터 검증 → 신규 입력) |
| `data_generator.py` | 합성 정신과 퇴원 EMR 1,500건 생성 (FHIR 매핑 설계) |
| `pipeline.py` | XGBoost 위험예측 + TreeSHAP 설명 + Two-Track 분류 |
| `rag_literacy.py` | RAG 기반 건강문해력 지원 (Track 1) : `ANTHROPIC_API_KEY` 설정 시 실시간 생성 |
| `drug_api.py` | 식약처 e약은요 공공 API (`DATA_GO_KR_API_KEY` 없으면 스냅샷 폴백) |
| `real_data.py` | UCI #296 실환자 약 7만 명 로더 + 학습 (최초 실행 시 자동 다운로드) |

### 데이터·라이선스

- **합성 코호트**: 자체 생성 가상 데이터 (실제 환자 자료가 아닙니다).
- **UCI #296** Diabetes 130-US Hospitals : CC BY 4.0, Strack et al. 2014.
  `data_cache/`는 저장소에 포함하지 않으며 최초 실행 시 자동 다운로드됩니다.
- **식약처 e약은요** : 공공데이터포털 공개 API (개인정보 아님).
- **글꼴 (대시보드)**: 아리따 부리(무료 배포)는 저장소에 포함하지 않습니다.
  [아모레퍼시픽 배포 페이지](https://www.apgroup.com/int/ko/about-us/visual-identity/arita-typeface/arita-typeface.html)에서
  받아 `static/fonts/AritaBuriKR-{Medium,SemiBold,Bold}.ttf`로 두면 적용되고, 없으면 시스템 serif로 폴백합니다.
