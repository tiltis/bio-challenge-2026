"""
pipeline.py — XGBoost 위험예측 엔진 + SHAP 설명가능 AI + Two-Track 분류.

신청서 핵심기술 ①: 위험도 예측 엔진(Risk Stratification Engine)
- 병원 EMR 피처로 '90일 내 치료중단/재입원' 위험을 XGBoost로 예측.
- 홀드아웃 평가로 AUROC·AUPRC 산출 (데이터 누수 없이 환자 단위 분할).
- SHAP(TreeExplainer)로 전역 중요도 + 환자별 기여도(설명가능 AI) 제공.
- 사전 정의 임계값으로 Track 1(일반 관리군) / Track 2(고위험군) 자동 분류.

설계 철학(규제 안전):
- 모델은 '진단'하지 않는다. '치료중단/재입원 위험 신호'와 Track 배정만 제공하며,
  최종 임상 판단·연계 결정은 의료진/의료사회복지사가 수행한다.
"""

import numpy as np
import pandas as pd

from data_generator import FEATURE_COLS, FEATURE_LABELS, feature_matrix

# Two-Track 임계값 (예측 위험확률 기준)
TRACK2_THRESHOLD = 0.50     # 이상이면 고위험군(Track 2)
TRACK_COLORS = {"Track 1": "#1f6feb", "Track 2": "#dc2626"}

# 위험 밴드(설명·표시용) — 분류 자체는 Track 2 임계값으로 이분
RISK_BANDS = [
    ("낮음",   0.00, 0.25, "Track 1 · 자가관리 가능군"),
    ("중간",   0.25, 0.50, "Track 1 · 건강문해력 집중 지원"),
    ("높음",   0.50, 0.75, "Track 2 · 사회복지사 컨설트"),
    ("매우높음", 0.75, 1.01, "Track 2 · 우선 연계 대상"),
]
BAND_COLORS = {
    "낮음": "#16a34a", "중간": "#eab308", "높음": "#f97316", "매우높음": "#dc2626",
}


def _make_model(scale_pos_weight=1.0):
    from xgboost import XGBClassifier
    return XGBClassifier(
        n_estimators=320, max_depth=4, learning_rate=0.05,
        subsample=0.85, colsample_bytree=0.85,
        reg_lambda=1.2, min_child_weight=3,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss", n_jobs=4, random_state=42,
    )


def train_and_score(df, test_size=0.25, seed=42):
    """
    환자 단위 홀드아웃으로 XGBoost 학습 → 전체 코호트에 위험확률 예측.
    반환: dict(model, df(위험확률·Track 부여), metrics, X_train, X_test, ...)
    """
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (roc_auc_score, average_precision_score,
                                 roc_curve, precision_recall_curve)

    X, y = feature_matrix(df)
    idx = np.arange(len(df))
    tr, te = train_test_split(idx, test_size=test_size, random_state=seed,
                              stratify=y)

    spw = float((y.iloc[tr] == 0).sum() / max(1, (y.iloc[tr] == 1).sum()))
    model = _make_model(scale_pos_weight=spw)
    model.fit(X.iloc[tr], y.iloc[tr])

    prob_all = model.predict_proba(X)[:, 1]
    prob_te = prob_all[te]
    y_te = y.iloc[te].values

    fpr, tpr, _ = roc_curve(y_te, prob_te)
    prec, rec, _ = precision_recall_curve(y_te, prob_te)
    metrics = {
        "auroc": float(roc_auc_score(y_te, prob_te)),
        "auprc": float(average_precision_score(y_te, prob_te)),
        "prevalence": float(y.mean()),
        "n_train": int(len(tr)), "n_test": int(len(te)),
        "roc": (fpr.tolist(), tpr.tolist()),
        "pr": (rec.tolist(), prec.tolist()),
    }

    out = df.copy()
    out["risk_prob"] = prob_all
    out["track"] = np.where(out["risk_prob"] >= TRACK2_THRESHOLD,
                            "Track 2", "Track 1")
    out["band"] = out["risk_prob"].apply(assign_band)
    out["_is_test"] = False
    out.iloc[te, out.columns.get_loc("_is_test")] = True

    return {"model": model, "df": out, "metrics": metrics,
            "X": X, "test_idx": te, "train_idx": tr}


def assign_band(p):
    for name, lo, hi, _ in RISK_BANDS:
        if lo <= p < hi:
            return name
    return "매우높음"


def band_description(band):
    for name, _, _, desc in RISK_BANDS:
        if name == band:
            return desc
    return ""


# ---------------------------------------------------------------- SHAP (TreeSHAP)
# 외부 shap 패키지 대신 XGBoost 내장 TreeSHAP(pred_contribs)을 사용한다.
# → 정식 SHAP 구현이며 버전 충돌이 없고, 로그-오즈 공간의 가법적 기여도를 보장한다.
def compute_shap(model, X):
    """
    코호트 전체의 SHAP 행렬 계산.
    반환: dict(values=(n, n_features) 배열, base=기준값(로그오즈), cols=피처리스트)
    """
    import xgboost as xgb
    booster = model.get_booster()
    dm = xgb.DMatrix(X.values, feature_names=list(X.columns))
    contribs = booster.predict(dm, pred_contribs=True)  # (n, n_feat+1)
    return {"values": contribs[:, :-1], "base": float(contribs[0, -1]),
            "cols": list(X.columns)}


def global_importance(shap_pack):
    """SHAP 평균 절대 기여도 기반 전역 피처 중요도 (라벨, 값) 내림차순."""
    vals = shap_pack["values"]
    mean_abs = np.abs(vals).mean(axis=0)
    items = [(FEATURE_LABELS.get(c, c), float(m))
             for c, m in zip(shap_pack["cols"], mean_abs)]
    items.sort(key=lambda x: -x[1])
    return items


def patient_shap(shap_pack, X, i):
    """
    i번째 환자의 SHAP 기여도 → [(라벨, shap값, 원본값), ...] 절대값 내림차순.
    """
    vals = shap_pack["values"][i]
    cols = shap_pack["cols"]
    row = X.iloc[i]
    items = [(FEATURE_LABELS.get(c, c), float(s), float(row[c]))
             for c, s in zip(cols, vals)]
    items.sort(key=lambda t: -abs(t[1]))
    return items


def compare_models(df, test_size=0.25, seed=42):
    """
    동일 홀드아웃에서 XGBoost vs 로지스틱회귀 vs 랜덤포레스트 AUROC 비교.
    차별성(설명가능 + 비선형 상호작용 포착)을 정량적으로 보여주기 위함.
    """
    from sklearn.model_selection import train_test_split
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.metrics import roc_auc_score

    X, y = feature_matrix(df)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=test_size,
                                          random_state=seed, stratify=y)
    out = {}

    spw = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
    xgb = _make_model(scale_pos_weight=spw).fit(Xtr, ytr)
    out["XGBoost"] = float(roc_auc_score(yte, xgb.predict_proba(Xte)[:, 1]))

    lr = make_pipeline(StandardScaler(),
                       LogisticRegression(max_iter=1000, class_weight="balanced"))
    lr.fit(Xtr, ytr)
    out["로지스틱 회귀"] = float(roc_auc_score(yte, lr.predict_proba(Xte)[:, 1]))

    rf = RandomForestClassifier(n_estimators=300, max_depth=8,
                                class_weight="balanced", random_state=seed, n_jobs=4)
    rf.fit(Xtr, ytr)
    out["랜덤포레스트"] = float(roc_auc_score(yte, rf.predict_proba(Xte)[:, 1]))
    return out


if __name__ == "__main__":
    from data_generator import generate
    d = generate()
    res = train_and_score(d)
    m = res["metrics"]
    print(f"사건율: {m['prevalence']:.1%}  (train {m['n_train']} / test {m['n_test']})")
    print(f"AUROC = {m['auroc']:.3f}   AUPRC = {m['auprc']:.3f}")
    print("Track 분포:", res["df"]["track"].value_counts().to_dict())
    sp_pack = compute_shap(res["model"], res["X"])
    print("\n[SHAP 전역 중요도 top5]")
    for lbl, g in global_importance(sp_pack)[:5]:
        print(f"  {lbl:24} {g:8.3f}")
    print("\n[환자 P0000 SHAP top5]")
    for lbl, s, v in patient_shap(sp_pack, res["X"], 0)[:5]:
        print(f"  {lbl:24} shap={s:+.3f}  value={v}")
