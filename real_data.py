"""
real_data.py : 실제 병원 데이터로 위험예측 파이프라인을 검증하는 모듈.

데이터: UCI ML Repository #296 "Diabetes 130-US Hospitals (1999-2008)"
- 미국 130개 병원의 실제 입원 10만 건(비식별 처리 완료, 공개 라이선스 CC BY 4.0).
- 라벨: 퇴원 후 30일 내 재입원 여부 → 본 플랫폼의 '재입원 위험 예측'과 동일 과제.
- 출처: Strack et al., BioMed Research International, 2014.
  https://archive.ics.uci.edu/dataset/296

왜 이 데이터인가 (심사 대응 논리):
- 한국의 실제 정신과 EMR은 민감정보(개인정보보호법)·IRB 승인 대상이라
  아이디어 검증 단계에서 사용할 수 없고, 사용해서도 안 된다.
- 대신 '같은 구조의 과제(퇴원 → 30일 재입원 예측)'인 공개 실데이터로
  파이프라인 전체(전처리→학습→평가→SHAP)가 실데이터에서 작동함을 검증한다.
- 실증 단계에서 병원 EMR(FHIR)로 교체하면 동일 코드가 그대로 학습된다.

전처리 기준(문헌 표준 관행을 따름):
- 사망/호스피스 퇴원 제외(재입원이 정의상 불가능한 케이스).
- 환자당 첫 입원 1건만 사용(동일 환자 중복으로 인한 데이터 누수 방지).
- 인종(race) 등 민감 속성은 의도적으로 제외 → 공정성·규제 안전 설계.
"""

import os
import numpy as np
import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache")
CSV_PATH = os.path.join(CACHE_DIR, "uci296", "diabetic_data.csv")
ZIP_URL = ("https://archive.ics.uci.edu/static/public/296/"
           "diabetes+130-us+hospitals+for+years+1999-2008.zip")

# 사망·호스피스 퇴원 코드 (IDS_mapping.csv 기준) : 재입원 정의 불가능 케이스
_EXCLUDE_DISPOSITION = {11, 13, 14, 19, 20, 21}

# 연령 구간 → 중앙값 (예: "[50-60)" → 55)
_AGE_MID = {f"[{a}-{a+10})": a + 5 for a in range(0, 100, 10)}

UCI_FEATURE_LABELS = {
    "age":               "연령",
    "sex_male":          "성별(남=1)",
    "time_in_hospital":  "이번 재원일수 (일)",
    "number_inpatient":  "최근 1년 입원 횟수",
    "number_emergency":  "최근 1년 응급실 방문",
    "number_outpatient": "최근 1년 외래 방문",
    "num_medications":   "처방 약물 수",
    "number_diagnoses":  "진단 수(동반질환)",
    "num_lab_procedures": "검사 시행 수",
    "num_procedures":    "처치 시행 수",
    "on_insulin":        "인슐린 처방",
    "med_changed":       "약물 변경됨",
    "on_diabetes_med":   "당뇨약 복용 중",
    "a1c_high":          "HbA1c 높음(>7)",
    "glucose_high":      "혈당 높음(>200)",
    "emergency_admit":   "응급 경로 입원",
    "discharged_home":   "자택 퇴원(시설이송 아님)",
    "prior_visits_total": "최근 1년 의료이용 총합",
}
UCI_FEATURE_COLS = list(UCI_FEATURE_LABELS.keys())

# 합성 정신과 코호트 ↔ UCI 실데이터 : 개념적으로 동일한 피처 매핑
# (실데이터 검증 탭에서 "같은 스키마 사상으로 즉시 이식 가능"을 보여주는 표)
FEATURE_MAPPING = [
    ("연령 / 성별",            "age, sex_male",             "age, gender"),
    ("이번 재원일수",           "index_los",                 "time_in_hospital"),
    ("과거 입원 횟수",          "prior_admissions",          "number_inpatient"),
    ("응급실 방문",            "prior_ed_visits",           "number_emergency"),
    ("외래 방문",              "outpatient_visits_1y",      "number_outpatient"),
    ("복약 관련",              "n_psych_meds, med_pdc",     "num_medications, insulin/change"),
    ("동반질환 부담",           "charlson",                  "number_diagnoses"),
    ("입원 경로(비자발/응급)",   "involuntary_admission",     "emergency_admit"),
]


def load_uci(csv_path=CSV_PATH):
    """UCI 실데이터 로드 + 표준 전처리 → 모델 입력 DataFrame 반환."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"UCI 데이터가 없습니다: {csv_path}\n"
            f"다운로드: {ZIP_URL} 을 받아 data_cache/uci296/ 에 압축 해제하세요.")

    df = pd.read_csv(csv_path, low_memory=False)

    # 1) 사망·호스피스 퇴원 제외 (재입원 정의 불가)
    df = df[~df["discharge_disposition_id"].isin(_EXCLUDE_DISPOSITION)]
    # 2) 환자당 첫 입원 1건 (동일 환자 중복 → 데이터 누수 방지)
    df = df.sort_values("encounter_id").drop_duplicates("patient_nbr", keep="first")
    # 3) 성별 불명 제거
    df = df[df["gender"].isin(["Male", "Female"])]

    out = pd.DataFrame(index=df.index)
    out["age"] = df["age"].map(_AGE_MID).astype(float)
    out["sex_male"] = (df["gender"] == "Male").astype(int)
    for c in ["time_in_hospital", "number_inpatient", "number_emergency",
              "number_outpatient", "num_medications", "number_diagnoses",
              "num_lab_procedures", "num_procedures"]:
        out[c] = df[c].astype(float)
    out["on_insulin"] = (df["insulin"] != "No").astype(int)
    out["med_changed"] = (df["change"] == "Ch").astype(int)
    out["on_diabetes_med"] = (df["diabetesMed"] == "Yes").astype(int)
    out["a1c_high"] = df["A1Cresult"].isin([">7", ">8"]).astype(int)
    out["glucose_high"] = df["max_glu_serum"].isin([">200", ">300"]).astype(int)
    out["emergency_admit"] = (df["admission_type_id"] == 1).astype(int)
    out["discharged_home"] = (df["discharge_disposition_id"] == 1).astype(int)
    out["prior_visits_total"] = (df["number_inpatient"] + df["number_emergency"]
                                 + df["number_outpatient"]).astype(float)

    out["outcome_30d"] = (df["readmitted"] == "<30").astype(int)
    return out.reset_index(drop=True)


def train_and_score_uci(df=None, test_size=0.25, seed=42):
    """
    실데이터로 pipeline.py 와 동일한 절차(XGBoost·홀드아웃·SHAP)를 수행.
    반환 구조는 pipeline.train_and_score 와 동일 키(metrics 등)를 사용.
    """
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (roc_auc_score, average_precision_score,
                                 roc_curve, precision_recall_curve)
    from pipeline import _make_model

    if df is None:
        df = load_uci()
    X = df[UCI_FEATURE_COLS]
    y = df["outcome_30d"].astype(int)

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=test_size,
                                          random_state=seed, stratify=y)
    spw = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
    model = _make_model(scale_pos_weight=spw)
    model.fit(Xtr, ytr)

    prob_te = model.predict_proba(Xte)[:, 1]
    fpr, tpr, _ = roc_curve(yte, prob_te)
    prec, rec, _ = precision_recall_curve(yte, prob_te)
    metrics = {
        "auroc": float(roc_auc_score(yte, prob_te)),
        "auprc": float(average_precision_score(yte, prob_te)),
        "prevalence": float(y.mean()),
        "n_train": int(len(Xtr)), "n_test": int(len(Xte)),
        "roc": (fpr.tolist(), tpr.tolist()),
        "pr": (rec.tolist(), prec.tolist()),
    }
    return {"model": model, "df": df, "metrics": metrics, "X": X}


def uci_global_importance(res):
    """실데이터 모델의 SHAP 전역 중요도 (라벨, 값) 내림차순."""
    from pipeline import compute_shap
    # SHAP 계산은 표본 5,000건이면 전역 경향 파악에 충분 (속도 절충)
    Xs = res["X"].sample(n=min(5000, len(res["X"])), random_state=42)
    pack = compute_shap(res["model"], Xs)
    vals = np.abs(pack["values"]).mean(axis=0)
    items = [(UCI_FEATURE_LABELS.get(c, c), float(m))
             for c, m in zip(pack["cols"], vals)]
    items.sort(key=lambda x: -x[1])
    return items


if __name__ == "__main__":
    d = load_uci()
    print(f"실데이터 코호트: {len(d):,}명 (환자당 1건)")
    print(f"30일 재입원율: {d['outcome_30d'].mean():.1%}")
    res = train_and_score_uci(d)
    m = res["metrics"]
    print(f"AUROC = {m['auroc']:.3f}   AUPRC = {m['auprc']:.3f} "
          f"(train {m['n_train']:,} / test {m['n_test']:,})")
    print("\n[실데이터 SHAP 전역 중요도 top8]")
    for lbl, g in uci_global_importance(res)[:8]:
        print(f"  {lbl:20} {g:8.3f}")
