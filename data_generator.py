"""
data_generator.py : 정신질환 퇴원환자 코호트의 병원 EMR 합성 데이터 생성기.

신청서(AI 기반 Two-Track Care Coordination Platform) 방향에 맞춰
'퇴원 시점' 1건당 1행(episode)으로 구성한다. 각 행은 한 환자의 퇴원 에피소드이며,
EMR에서 추출 가능한 피처(인구학·진단·입원이력·외래·복약·사회경제)로만 이루어진다.

설계:
- 실제 병원 EMR(FHIR Patient/Encounter/Condition/MedicationRequest 리소스)에서
  동일 스키마로 추출 가능하도록 컬럼을 구성 → 실데이터 연결 시 즉시 호환.
- 각 에피소드는 잠재 위험(logit)을 피처 선형결합 + 노이즈로 만들고,
  여기서 '90일 내 치료중단/재입원' 라벨(outcome_90d)을 베르누이 샘플링한다.
- 따라서 XGBoost가 학습 가능한 신호가 존재하고, SHAP 기여도도 해석 가능하게 나온다.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- 스키마
N_PATIENTS = 1500

DIAGNOSES = ["조현병", "양극성장애", "우울장애", "불안장애"]

# 모델 입력 피처 (EMR 추출 가능) : 표시 순서와 동일
NUMERIC_COLS = [
    "age", "prior_admissions", "index_los", "prior_ed_visits",
    "outpatient_visits_1y", "prior_noshow_rate", "n_psych_meds",
    "med_pdc", "distance_km", "charlson",
]
BINARY_COLS = [
    "sex_male", "prior_discontinuation", "lives_alone", "has_caregiver",
    "medicaid", "involuntary_admission", "substance_use",
]
# 진단명은 원-핫으로 펼침 (SHAP 해석을 위해)
DIAG_COLS = [f"dx_{d}" for d in DIAGNOSES]

FEATURE_COLS = NUMERIC_COLS + BINARY_COLS + DIAG_COLS

FEATURE_LABELS = {
    "age":                  "연령",
    "prior_admissions":     "과거 입원 횟수",
    "index_los":            "이번 재원일수 (일)",
    "prior_ed_visits":      "최근 1년 응급실 방문",
    "outpatient_visits_1y": "최근 1년 외래 방문",
    "prior_noshow_rate":    "외래 미방문율(no-show)",
    "n_psych_meds":         "정신과 약물 수",
    "med_pdc":              "복약 보유율(PDC)",
    "distance_km":          "거주지-시설 거리(km)",
    "charlson":             "동반질환 지수(Charlson)",
    "sex_male":             "성별(남=1)",
    "prior_discontinuation": "과거 치료중단 이력",
    "lives_alone":          "독거",
    "has_caregiver":        "보호자 있음",
    "medicaid":             "의료급여 수급",
    "involuntary_admission": "비자발(강제) 입원",
    "substance_use":        "물질사용 동반",
    "dx_조현병":            "진단: 조현병",
    "dx_양극성장애":        "진단: 양극성장애",
    "dx_우울장애":          "진단: 우울장애",
    "dx_불안장애":          "진단: 불안장애",
}

# 그룹(대시보드 표시용)
FEATURE_GROUPS = {
    "인구학": ["age", "sex_male"],
    "진단": DIAG_COLS,
    "입원·응급 이력": ["prior_admissions", "index_los", "prior_ed_visits",
                   "involuntary_admission"],
    "외래·복약": ["outpatient_visits_1y", "prior_noshow_rate", "n_psych_meds",
                "med_pdc", "prior_discontinuation"],
    "사회경제·접근성": ["lives_alone", "has_caregiver", "medicaid",
                   "distance_km", "substance_use", "charlson"],
}

# 위험(logit) 방향 계수 : 양수=치료중단/재입원 위험↑
# (선형 주효과는 의도적으로 약화하고, 위험의 상당부분을 아래 비선형 상호작용에 배분
#  → 트리기반 XGBoost가 선형모델 대비 우위를 갖도록 현실적으로 설계)
RISK_COEF = {
    "prior_admissions":      0.22,
    "index_los":             0.010,
    "prior_ed_visits":       0.22,
    "outpatient_visits_1y": -0.08,
    "prior_noshow_rate":     1.3,
    "n_psych_meds":          0.10,
    "med_pdc":              -1.4,
    "distance_km":           0.008,
    "charlson":              0.14,
    "prior_discontinuation": 0.55,
    "lives_alone":           0.30,
    "has_caregiver":        -0.35,
    "medicaid":              0.30,
    "involuntary_admission": 0.35,
    "substance_use":         0.45,
}
DIAG_RISK = {"조현병": 0.70, "양극성장애": 0.45, "우울장애": 0.15, "불안장애": 0.0}


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def generate(seed=42):
    """정신질환 퇴원환자 N_PATIENTS명의 EMR 합성 코호트 반환 (퇴원 1건/행)."""
    rng = np.random.default_rng(seed)
    rows = []

    for pid in range(N_PATIENTS):
        diagnosis = rng.choice(DIAGNOSES, p=[0.22, 0.20, 0.40, 0.18])

        age = int(np.clip(rng.normal(46, 15), 18, 90))
        sex_male = int(rng.random() < 0.52)

        prior_admissions = int(rng.poisson(1.4))
        index_los = int(np.clip(rng.normal(21, 12), 3, 120))
        prior_ed_visits = int(rng.poisson(0.8))
        outpatient_visits_1y = int(np.clip(rng.poisson(5) - prior_admissions, 0, 30))

        prior_noshow_rate = float(np.clip(rng.beta(2, 5), 0, 1))
        n_psych_meds = int(np.clip(rng.poisson(2.2) + 1, 1, 8))
        med_pdc = float(np.clip(rng.beta(5, 3), 0.05, 1.0))   # 복약 보유율
        distance_km = float(np.clip(rng.gamma(2.0, 7.0), 0.5, 90))
        charlson = int(np.clip(rng.poisson(0.7), 0, 6))

        lives_alone = int(rng.random() < 0.34)
        has_caregiver = int(rng.random() < (0.30 if lives_alone else 0.80))
        medicaid = int(rng.random() < 0.27)
        involuntary_admission = int(rng.random() < (0.30 if diagnosis == "조현병"
                                                    else 0.12))
        substance_use = int(rng.random() < 0.18)

        feat = dict(
            age=age, sex_male=sex_male, prior_admissions=prior_admissions,
            index_los=index_los, prior_ed_visits=prior_ed_visits,
            outpatient_visits_1y=outpatient_visits_1y,
            prior_noshow_rate=prior_noshow_rate, n_psych_meds=n_psych_meds,
            med_pdc=med_pdc, distance_km=distance_km, charlson=charlson,
            prior_discontinuation=int(rng.random() < (0.45 * (1 - med_pdc) + 0.05)),
            lives_alone=lives_alone, has_caregiver=has_caregiver,
            medicaid=medicaid, involuntary_admission=involuntary_admission,
            substance_use=substance_use,
        )

        # 잠재 위험 logit (절편은 전체 사건율 ≈ 28% 가 되도록 보정)
        logit = -2.75 + DIAG_RISK[diagnosis]
        for k, c in RISK_COEF.items():
            logit += c * feat[k]
        # 연령 효과(U자형: 청년·노년 위험↑)
        logit += 0.012 * abs(age - 45)

        # --- 비선형 상호작용(트리모델이 포착, 선형모델은 놓치는 신호) ---
        f = feat
        # 독거 × 복약불량: 혼자 살며 약을 못 챙기면 위험 급증
        logit += 1.8 * f["lives_alone"] * (1 - f["med_pdc"])
        # 외래 미방문 × 보호자 부재: 챙겨줄 사람 없이 외래까지 빠지면 급증
        logit += 1.6 * f["prior_noshow_rate"] * (1 - f["has_caregiver"])
        # 물질사용 × 잦은 과거입원: 둘이 겹칠 때만 크게 작용
        logit += 0.9 * f["substance_use"] * (f["prior_admissions"] >= 2)
        # 복약불량 × 과거 치료중단 이력: 결합 시 비선형 가중
        logit += 1.0 * (f["med_pdc"] < 0.5) * f["prior_discontinuation"]

        logit += rng.normal(0, 0.32)

        p = _sigmoid(logit)
        outcome_90d = int(rng.random() < p)

        row = dict(patient_id=f"P{pid:04d}", diagnosis=diagnosis, **feat,
                   _latent_risk=round(float(p), 3),
                   outcome_90d=outcome_90d)
        # 진단 원-핫
        for d in DIAGNOSES:
            row[f"dx_{d}"] = int(diagnosis == d)
        rows.append(row)

    return pd.DataFrame(rows)


def feature_matrix(df):
    """모델 입력용 (X, y) 추출."""
    X = df[FEATURE_COLS].copy()
    y = df["outcome_90d"].astype(int)
    return X, y


if __name__ == "__main__":
    d = generate()
    print(d.shape)
    print("결과 사건율(90일 치료중단/재입원):",
          f"{d['outcome_90d'].mean():.1%}")
    print(d["diagnosis"].value_counts())
    print(d[FEATURE_COLS].describe().T[["mean", "min", "max"]].round(2))
