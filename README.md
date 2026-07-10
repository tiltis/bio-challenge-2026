# AI 기반 Two-Track Care Coordination Platform (PoC 데모)

정신질환 퇴원환자의 90일 내 치료중단·재입원 위험을 병원 EMR로 예측(XGBoost + SHAP)하고,
일반군(Track 1)/고위험군(Track 2)으로 분류해 맞춤 개입을 연계하는 Streamlit 데모입니다.

> 2026 연구 아이디어 기술사업화 챌린지 · 경북대학교병원 팀
> 본 시스템은 **진단 도구가 아니며**, 위험 신호와 Track 배정만 제공합니다.
> 모든 임상·연계 결정은 의료진과 의료사회복지사가 수행합니다.

## 🚀 처음이신가요? 이것만 하면 됩니다

이 저장소에는 **실행하는 것 1개**와 **그냥 여는 것 1개**가 있습니다.

| 보고 싶은 것 | 방법 |
|---|---|
| **① 데모 대시보드** (위험예측 PoC 본체) | 아래 [실행](#실행) 순서로 설치 후 `run.bat` 더블클릭 → 브라우저가 자동으로 열림 |
| **② LinkCure(링큐어) 앱 목업** (모바일 화면 시안) | 설치·실행 필요 없음. [`mockup/linkcure_mockup_annotated.html`](mockup/linkcure_mockup_annotated.html)을 내려받아 **더블클릭**하면 끝 |

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py     # http://localhost:8501
```

- Python 3.12 / Streamlit 1.37 기준. `numpy<2` 핀 유지 필요.
- `python app.py` 직접 실행은 동작하지 않습니다 : 반드시 `streamlit run`.

## 구성

| 파일 | 역할 |
|---|---|
| `app.py` | 7탭 대시보드 (EMR → 위험예측 → 우선개입 대기열 → 개입 연계 → 차별점 → 실데이터 검증 → 신규 입력) |
| `data_generator.py` | 합성 정신과 퇴원 EMR 1,500건 생성 (FHIR 매핑 설계) |
| `pipeline.py` | XGBoost 위험예측 + TreeSHAP 설명 + Two-Track 분류 |
| `rag_literacy.py` | RAG 기반 건강문해력 지원 (Track 1) : `ANTHROPIC_API_KEY` 설정 시 Claude 실시간 생성 |
| `drug_api.py` | 식약처 e약은요 공공 API (`DATA_GO_KR_API_KEY` 없으면 스냅샷 폴백) |
| `real_data.py` | UCI #296 실환자 약 7만 명 로더 + 학습 (최초 실행 시 자동 다운로드) |
| `mockup/` | LinkCure 모바일 앱 목업 3종(설명용·흰배경·편집용) + 코드 편집용 분리 소스 : [mockup/README.md](mockup/README.md) |

## 데이터·라이선스

- **합성 코호트**: 자체 생성 가상 데이터 (실제 환자 자료가 아닙니다).
- **UCI #296** Diabetes 130-US Hospitals : CC BY 4.0, Strack et al. 2014.
  `data_cache/`는 저장소에 포함하지 않으며 최초 실행 시 자동 다운로드됩니다.
- **식약처 e약은요** : 공공데이터포털 공개 API (개인정보 아님).
- **글꼴 (대시보드)**: 아리따 부리(무료 배포)는 저장소에 포함하지 않습니다.
  [아모레퍼시픽 배포 페이지](https://www.apgroup.com/int/ko/about-us/visual-identity/arita-typeface/arita-typeface.html)에서
  받아 `static/fonts/AritaBuriKR-{Medium,SemiBold,Bold}.ttf`로 두면 적용되고, 없으면 시스템 serif로 폴백합니다.
- **글꼴 (앱 목업)**: 한글은 페이퍼로지(Paperlogy, 무료 글꼴·HTML에 내장), 영문·숫자는 Times New Roman 두 가지만 사용합니다.

상세 개발 기록은 `작업일지.txt` 참조.
