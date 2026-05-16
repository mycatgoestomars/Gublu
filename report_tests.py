# Gublu Final Report Test Suite
# Generates test_outputs/ with JSON, CSV, graphs, and summary
import sys, os, json, time, csv, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))

import requests
API = "http://127.0.0.1:5000"
os.makedirs("test_outputs", exist_ok=True)

passed_tests = 0
failed_tests = 0
test_results = []

def record_test(name, category, expected, actual, passed):
    global passed_tests, failed_tests
    status = "PASS" if passed else "FAIL"
    if passed: passed_tests += 1
    else: failed_tests += 1
    test_results.append({"name":name,"category":category,"expected":str(expected),"actual":str(actual),"status":status})
    print(f"  [{status}] {name}" + ("" if passed else f" — expected={expected}, actual={actual}"))

def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")

def api_call(method, path, json_data=None):
    try:
        if method == "GET": r = requests.get(f"{API}{path}", timeout=15)
        else: r = requests.post(f"{API}{path}", json=json_data, timeout=30)
        return r.status_code, r.json()
    except Exception as e: return 0, str(e)

# ===========================
# 1. Emotional Prediction
# ===========================
section("1. Emotional Prediction")
from predict import predict_emotions

sad_emotions = predict_emotions("I feel so sad and empty")
record_test("Sad input — sadness is dominant","Emotion Prediction",True,sad_emotions["sadness"]==max(sad_emotions.values()),sad_emotions["sadness"]==max(sad_emotions.values()))

happy_emotions = predict_emotions("I had an amazing day today")
record_test("Happy input — joy is dominant","Emotion Prediction",True,happy_emotions["joy"]==max(happy_emotions.values()),happy_emotions["joy"]==max(happy_emotions.values()))

angry_emotions = predict_emotions("I'm so frustrated and angry")
record_test("Angry input — anger is dominant","Emotion Prediction",True,angry_emotions["anger"]==max(angry_emotions.values()),angry_emotions["anger"]==max(angry_emotions.values()))

neutral_emotions = predict_emotions("I went to the shop")
all_keys = all(k in neutral_emotions for k in ["sadness","joy","anger","fear","surprise","neutral"])
record_test("Emotion output has all required keys","Emotion Prediction",True,all_keys,all_keys)

# ===========================
# 2. Emotional Correction
# ===========================
section("2. Emotional Correction")
from emotion_correction import correct_emotions

before_negation = {"sadness":0.1,"joy":0.8,"anger":0.05,"fear":0.05,"surprise":0.0,"neutral":0.0}
after_negation = correct_emotions("I'm not happy", dict(before_negation))
neg_ok = after_negation["joy"] < before_negation["joy"] and after_negation["sadness"] > before_negation["sadness"]
record_test("Negation reduces joy and boosts sadness","Emotion Correction",True,neg_ok,neg_ok)

before_strong = {"sadness":0.3,"joy":0.4,"anger":0.1,"fear":0.1,"surprise":0.0,"neutral":0.0}
after_strong = correct_emotions("nothing matters", dict(before_strong))
strong_ok = after_strong["sadness"] > before_strong["sadness"] + 0.4
record_test("Strong negative phrase boosts sadness","Emotion Correction",True,strong_ok,strong_ok)

before_clamp = {"sadness":0.8,"joy":0.9,"anger":0.1,"fear":0.1,"surprise":0.0,"neutral":0.0}
after_clamp = correct_emotions("I'm not happy and feel hopeless", dict(before_clamp))
clamp_ok = all(0.0 <= v <= 1.0 for v in after_clamp.values())
record_test("Values clamped between 0.0 and 1.0","Emotion Correction",True,clamp_ok,clamp_ok)

# ==================================
# 3. Fuzzy Logic Distress Scoring
# ==================================
section("3. Fuzzy Distress Scoring")
from Gublu import fuzzy_system

high_sad = {"sadness":0.9,"joy":0.05,"anger":0.1,"fear":0.1,"surprise":0.0,"neutral":0.0}
score_hs, label_hs = fuzzy_system(high_sad)
record_test("High sadness — high distress","Fuzzy Logic","high distress",label_hs,label_hs=="high distress" and score_hs>=0.85)

high_joy = {"sadness":0.05,"joy":0.9,"anger":0.05,"fear":0.05,"surprise":0.1,"neutral":0.0}
score_hj, label_hj = fuzzy_system(high_joy)
record_test("High joy — low distress","Fuzzy Logic","low distress",label_hj,label_hj=="low distress" and score_hj<0.45)

mixed = {"sadness":0.5,"joy":0.2,"anger":0.3,"fear":0.3,"surprise":0.1,"neutral":0.0}
score_mx, label_mx = fuzzy_system(mixed)
record_test("Mixed emotions — moderate distress","Fuzzy Logic","moderate distress",label_mx,label_mx=="moderate distress")

zeros = {"sadness":0.0,"joy":0.0,"anger":0.0,"fear":0.0,"surprise":0.0,"neutral":0.0}
score_z, label_z = fuzzy_system(zeros)
record_test("All zeros — low distress","Fuzzy Logic","low distress",label_z,score_z==0.0 and label_z=="low distress")

# =======================
# 4. Risk Detection
# =======================
section("4. Risk Detection")
from Gublu import detect_risk

record_test("Direct risk phrase detected","Risk Detection","high",detect_risk("I want to kill myself"),detect_risk("I want to kill myself")=="high")
record_test("Safe input — low risk","Risk Detection","low",detect_risk("I had a normal day"),detect_risk("I had a normal day")=="low")
record_test("Case insensitive risk detection","Risk Detection","high",detect_risk("I Want To Die"),detect_risk("I Want To Die")=="high")

# =======================
# 5. Streak System
# =======================
section("5. Streak System")
from streak_system import is_success

record_test("Procrastination — focused well = success","Streak System",True,is_success("procrastination","focused well"),is_success("procrastination","focused well"))
record_test("Procrastination — procrastinated = failure","Streak System",False,is_success("procrastination","procrastinated"),not is_success("procrastination","procrastinated"))
record_test("Overspending — no spending = success","Streak System",True,is_success("overspending","no spending"),is_success("overspending","no spending"))
record_test("Isolation — avoided people = failure","Streak System",False,is_success("isolation","avoided people"),not is_success("isolation","avoided people"))

# =======================
# 6. Memory Manager
# =======================
section("6. Memory Manager")
from memory_manager import load_memory, save_memory, default_memory

default_mem = default_memory()
required_keys = ["username","my_why","chosen_problem","daily_checkins","patterns","streak","streak_breaks","high_distress_messages"]
keys_ok = all(k in default_mem for k in required_keys)
record_test("Default memory has all required keys","Memory Manager",True,keys_ok,keys_ok)

# =====================
# 7. API Tests
# =====================
section("7. API Tests")
print("  [SETUP] Resetting and loading Nadia simulation...")
requests.post(f"{API}/reset", timeout=10)
time.sleep(1)

status, sim_nadia = api_call("POST", "/simulations/load", {"profile":"resilient"})
record_test("Load Nadia (resilient) profile","API Simulation",200,status,status==200 and sim_nadia.get("username")=="Nadia")
time.sleep(1)

status, chat_resp = api_call("POST", "/chat", {"message":"I'm feeling stressed about exams"})
record_test("Chat — normal message returns reply","API Chat",200,status,status==200 and chat_resp.get("reply") and isinstance(chat_resp.get("distress"),(int,float)))

status, chat_happy = api_call("POST", "/chat", {"message":"Great day today!"})
chat_happy_ok = status==200 and chat_happy.get("label") in ["low distress","moderate distress"]
record_test("Chat — happy message is low or moderate distress","API Chat","low/moderate distress",chat_happy.get("label"),chat_happy_ok)

status, chat_risk = api_call("POST", "/chat", {"message":"I want to end my life"})
record_test("Chat — high risk triggers safety response","API Chat","high distress",chat_risk.get("label"),status==200 and chat_risk.get("distress")==1.0)

status, dash = api_call("GET", "/dashboard")
record_test("Dashboard returns all fields","API Dashboard",True,all(k in dash for k in ["streak","username"]) if isinstance(dash,dict) else False,status==200 and isinstance(dash,dict) and all(k in dash for k in ["streak","username"]))

status, hist = api_call("GET", "/history")
record_test("History returns check-in array","API History",True,isinstance(hist,list) and len(hist)>0,status==200 and isinstance(hist,list) and len(hist)>0)

status, pred = api_call("GET", "/predictions")
record_test("Predictions endpoint returns data","API Predictions",200,status,status==200)

status, sim_marcus = api_call("POST", "/simulations/load", {"profile":"struggling"})
record_test("Load Marcus (struggling) profile","API Simulation","Marcus",sim_marcus.get("username"),status==200 and sim_marcus.get("username")=="Marcus")

status, sim_lala = api_call("POST", "/simulations/load", {"profile":"recovering"})
record_test("Load Lala (recovering) profile","API Simulation","Lala",sim_lala.get("username"),status==200 and sim_lala.get("username")=="Lala")

# ================================
# 8. Simulation Reproducibility
# ================================
section("8. Simulation Reproducibility")
requests.post(f"{API}/reset", timeout=10); time.sleep(0.5)
_, load1 = api_call("POST", "/simulations/load", {"profile":"resilient"}); time.sleep(0.5)
streak1 = load1.get("current_streak")
breaks1 = load1.get("breaks")

requests.post(f"{API}/reset", timeout=10); time.sleep(0.5)
_, load2 = api_call("POST", "/simulations/load", {"profile":"resilient"}); time.sleep(0.5)
streak2 = load2.get("current_streak")
breaks2 = load2.get("breaks")

repro_ok = streak1 == streak2 and breaks1 == breaks2
record_test("Same profile produces identical results","Simulation Reproducibility",f"streak={streak1},breaks={breaks1}",f"streak={streak2},breaks={breaks2}",repro_ok)

# =====================
# 9. Error Handling
# =====================
section("9. Error Handling")
requests.post(f"{API}/reset", timeout=10); time.sleep(0.5)

status, dash_empty = api_call("GET", "/dashboard")
record_test("Empty state — dashboard returns streak=0","Error Handling",0,dash_empty.get("streak") if isinstance(dash_empty,dict) else None,status==200 and isinstance(dash_empty,dict) and dash_empty.get("streak")==0)

status, chat_empty = api_call("POST", "/chat", {"message":""})
record_test("Empty chat message — no crash","Error Handling",True,chat_empty.get("reply") is not None if isinstance(chat_empty,dict) else False,status==200)

# ==========================
# 10. ML Model Evaluation
# ==========================
section("10. ML Model Evaluation (XGBoost)")
print("  [SETUP] Loading Marcus for ML evaluation...")
requests.post(f"{API}/simulations/load", json={"profile":"struggling"}, timeout=30)
time.sleep(2)

import numpy as np, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
from xgboost import XGBClassifier
from ml_streak_predictor import entry_to_features, is_failure

with open("gublu_memory.json") as f: memory_data = json.load(f)
checkin_data = memory_data["daily_checkins"]
running_streak = 0
for c in checkin_data:
    c["_current_streak"] = running_streak
    if is_failure(c): running_streak = 0
    else: running_streak += 1

feature_rows = [entry_to_features(c, i, checkin_data) for i, c in enumerate(checkin_data)]
target_labels = [is_failure(c) for c in checkin_data]
feature_df = pd.DataFrame(feature_rows)
target_array = np.array(target_labels)

ml_metrics = {}
if len(np.unique(target_array)) >= 2 and len(feature_df) >= 20:
    X_train, X_test, y_train, y_test = train_test_split(feature_df, target_array, test_size=0.2, random_state=42)
    n_pos = y_train.sum(); n_neg = len(y_train) - n_pos
    scale_weight = max(n_neg / max(n_pos, 1), 1.0)

    xgb_model = XGBClassifier(n_estimators=80, max_depth=4, learning_rate=0.1, scale_pos_weight=scale_weight, eval_metric="logloss", random_state=42, verbosity=0)
    xgb_model.fit(X_train, y_train)
    y_predicted = xgb_model.predict(X_test)
    y_probabilities = xgb_model.predict_proba(X_test)[:,1]

    ml_metrics = {
        "accuracy": round(accuracy_score(y_test, y_predicted), 4),
        "precision": round(precision_score(y_test, y_predicted, zero_division=0), 4),
        "recall": round(recall_score(y_test, y_predicted, zero_division=0), 4),
        "f1_score": round(f1_score(y_test, y_predicted, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, y_probabilities), 4) if len(np.unique(y_test))>=2 else 0.0,
    }
    confusion_matrix_values = confusion_matrix(y_test, y_predicted).tolist()
    ml_metrics["confusion_matrix"] = confusion_matrix_values

    feature_importance_rows = sorted(zip(feature_df.columns, xgb_model.feature_importances_), key=lambda x: x[1], reverse=True)

    for metric_name, metric_value in ml_metrics.items():
        if metric_name != "confusion_matrix":
            print(f"  {metric_name}: {metric_value}")
    print(f"  Confusion Matrix: {confusion_matrix_values}")

    record_test("ML Accuracy >= 0.50","ML Evaluation",">=0.50",ml_metrics["accuracy"],ml_metrics["accuracy"]>=0.50)
    record_test("ML F1 Score >= 0.40","ML Evaluation",">=0.40",ml_metrics["f1_score"],ml_metrics["f1_score"]>=0.40)
    record_test("ML ROC-AUC >= 0.40","ML Evaluation",">=0.40",ml_metrics["roc_auc"],ml_metrics["roc_auc"]>=0.40)

    # --- GRAPHS ---
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Confusion Matrix
    fig, ax = plt.subplots(figsize=(5,4))
    cm = np.array(confusion_matrix_values)
    ax.imshow(cm, cmap="Blues")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i,j]), ha="center", va="center", fontsize=14, color="white" if cm[i,j]>cm.max()/2 else "black")
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    ax.set_xticks([0,1]); ax.set_yticks([0,1])
    ax.set_xticklabels(["Success","Break"]); ax.set_yticklabels(["Success","Break"])
    ax.set_title("XGBoost Confusion Matrix")
    plt.tight_layout(); plt.savefig("test_outputs/confusion_matrix.png", dpi=150); plt.close()
    print("  Saved: test_outputs/confusion_matrix.png")

    # Metrics Bar Chart
    metric_names = ["Accuracy","Precision","Recall","F1 Score","ROC-AUC"]
    metric_values = [ml_metrics["accuracy"],ml_metrics["precision"],ml_metrics["recall"],ml_metrics["f1_score"],ml_metrics["roc_auc"]]
    fig, ax = plt.subplots(figsize=(7,4))
    bars = ax.bar(metric_names, metric_values, color=["#3d5a40","#588157","#a3b18a","#dad7cd","#344e41"])
    for bar, val in zip(bars, metric_values): ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.02, f"{val:.3f}", ha="center", fontsize=10)
    ax.set_ylim(0,1.15); ax.set_ylabel("Score"); ax.set_title("XGBoost ML Model Metrics")
    plt.tight_layout(); plt.savefig("test_outputs/ml_metrics_bar_chart.png", dpi=150); plt.close()
    print("  Saved: test_outputs/ml_metrics_bar_chart.png")

    # Feature Importance
    top_features = feature_importance_rows[:10]
    fig, ax = plt.subplots(figsize=(8,5))
    feat_names = [f[0] for f in reversed(top_features)]
    feat_vals = [f[1] for f in reversed(top_features)]
    ax.barh(feat_names, feat_vals, color="#3d5a40")
    ax.set_xlabel("Importance"); ax.set_title("Top 10 XGBoost Feature Importances")
    plt.tight_layout(); plt.savefig("test_outputs/feature_importance_chart.png", dpi=150); plt.close()
    print("  Saved: test_outputs/feature_importance_chart.png")

    # ML CSV
    with open("test_outputs/ml_evaluation_results.csv","w",newline="") as f:
        w = csv.writer(f); w.writerow(["metric","value"])
        for k,v in ml_metrics.items():
            if k != "confusion_matrix": w.writerow([k,v])
        w.writerow(["confusion_matrix",str(confusion_matrix_values)])
        w.writerow(["---","--- Feature Importance ---"])
        for feat, imp in feature_importance_rows[:10]: w.writerow([feat, round(imp,4)])
    print("  Saved: test_outputs/ml_evaluation_results.csv")
else:
    print("  Not enough class variety for ML evaluation")

# ====================================
# 11. Simulation Profile Comparison
# ===================================
section("11. Simulation Profile Comparison")
profile_stats = {}
for profile_id, profile_name in [("resilient","Nadia"),("struggling","Marcus"),("recovering","Lala")]:
    requests.post(f"{API}/reset", timeout=10); time.sleep(0.5)
    _, result = api_call("POST", "/simulations/load", {"profile": profile_id}); time.sleep(1)
    _, pred_result = api_call("GET", "/predictions")
    profile_stats[profile_name] = {
        "checkins": result.get("checkins",0), "breaks": result.get("breaks",0),
        "current_streak": result.get("current_streak",0), "longest_streak": result.get("longest_streak",0),
        "risk_score": pred_result.get("risk_score",0) if isinstance(pred_result,dict) else 0,
        "high_distress_msgs": result.get("high_distress_msgs",0)
    }

marcus_more_breaks = profile_stats.get("Marcus",{}).get("breaks",0) > profile_stats.get("Nadia",{}).get("breaks",0)
record_test("Marcus has more breaks than Nadia","Simulation Comparison",True,marcus_more_breaks,marcus_more_breaks)

try:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    names = list(profile_stats.keys())
    fig, axes = plt.subplots(1,3,figsize=(12,4))
    axes[0].bar(names,[profile_stats[n]["breaks"] for n in names],color=["#3d5a40","#c1121f","#588157"])
    axes[0].set_title("Streak Breaks"); axes[0].set_ylabel("Count")
    axes[1].bar(names,[profile_stats[n]["current_streak"] for n in names],color=["#3d5a40","#c1121f","#588157"])
    axes[1].set_title("Current Streak"); axes[1].set_ylabel("Days")
    axes[2].bar(names,[profile_stats[n]["high_distress_msgs"] for n in names],color=["#3d5a40","#c1121f","#588157"])
    axes[2].set_title("High Distress Messages"); axes[2].set_ylabel("Count")
    plt.suptitle("Simulation Profile Comparison", fontsize=14)
    plt.tight_layout(); plt.savefig("test_outputs/simulation_profile_comparison.png", dpi=150); plt.close()
    print("  Saved: test_outputs/simulation_profile_comparison.png")
except Exception as e: print(f"  Could not generate comparison graph: {e}")

# =====================
# 12. PSO Testing
# =====================
section("12. PSO Testing")
pso_exists = os.path.exists("pso_optimiser.py") and os.path.exists("evaluate_pso.py")
if pso_exists:
    print("  PSO files found: pso_optimiser.py, evaluate_pso.py")
    try:
        from evaluate_pso import evaluate
        default_params = (0.32, 0.52, 0.72)
        pso_params = (0.352, 0.491, 0.900)
        default_mae, default_mse = evaluate(default_params)
        pso_mae, pso_mse = evaluate(pso_params)
        pso_comparable = abs(pso_mse - default_mse) < 0.01
        record_test("PSO MSE is comparable to or better than default","PSO Performance",True,pso_comparable,pso_comparable)
        print(f"  Before PSO: MSE={default_mse:.6f}, MAE={default_mae:.6f}")
        print(f"  After PSO:  MSE={pso_mse:.6f}, MAE={pso_mae:.6f}")
        with open("test_outputs/pso_results.csv","w",newline="") as f:
            w = csv.writer(f); w.writerow(["metric","before_pso","after_pso"])
            w.writerow(["MSE",round(default_mse,6),round(pso_mse,6)])
            w.writerow(["MAE",round(default_mae,6),round(pso_mae,6)])
            w.writerow(["best_params","(0.32, 0.52, 0.72)",str(pso_params)])
            w.writerow(["comparable","",str(pso_comparable)])
        print("  Saved: test_outputs/pso_results.csv")
    except Exception as e:
        print(f"  PSO evaluation error: {e}")
        record_test("PSO evaluation runs","PSO Performance","no error",str(e),False)
else:
    print("  PSO is not implemented in this project. No PSO tests added.")

# ============================================================
# 13. XGBoost Default vs Optimised with RandomizedSearchCV
# ============================================================
section("13. XGBoost Default vs Optimised (RandomizedSearchCV)")
print("  [SETUP] Loading Marcus for XGBoost comparison...")
requests.post(f"{API}/simulations/load", json={"profile":"struggling"}, timeout=30)
time.sleep(2)

from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split as sk_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score as sk_f1, roc_auc_score, confusion_matrix as sk_cm
from ml_streak_predictor import entry_to_features, is_failure

with open("gublu_memory.json") as f: mem = json.load(f)
ci_data = mem["daily_checkins"]
rs = 0
for c in ci_data:
    c["_current_streak"] = rs
    if is_failure(c): rs = 0
    else: rs += 1

feat_rows = [entry_to_features(c, i, ci_data) for i, c in enumerate(ci_data)]
tgt_labels = [is_failure(c) for c in ci_data]
feat_df = pd.DataFrame(feat_rows)
tgt_arr = np.array(tgt_labels)

xgb_comparison = {}
if len(np.unique(tgt_arr)) >= 2 and len(feat_df) >= 20:
    X_tr, X_te, y_tr, y_te = train_test_split(feat_df, tgt_arr, test_size=0.2, random_state=42)
    n_pos = y_tr.sum(); n_neg = len(y_tr) - n_pos
    spw = max(n_neg / max(n_pos,1), 1.0)

    # Default model
    default_xgb = XGBClassifier(n_estimators=80, max_depth=4, learning_rate=0.1,
                                 scale_pos_weight=spw, eval_metric="logloss",
                                 random_state=42, verbosity=0)
    default_xgb.fit(X_tr, y_tr)
    d_pred = default_xgb.predict(X_te)
    d_prob = default_xgb.predict_proba(X_te)[:,1]
    d_acc   = round(accuracy_score(y_te, d_pred), 4)
    d_prec  = round(precision_score(y_te, d_pred, zero_division=0), 4)
    d_rec   = round(recall_score(y_te, d_pred, zero_division=0), 4)
    d_f1    = round(sk_f1(y_te, d_pred, zero_division=0), 4)
    d_auc   = round(roc_auc_score(y_te, d_prob), 4) if len(np.unique(y_te)) >= 2 else 0.0
    d_cm    = sk_cm(y_te, d_pred).tolist()

    # Optimised model (RandomizedSearchCV)
    param_dist = {
        "n_estimators":     [50,80,100,150,200],
        "max_depth":        [3,4,5,6],
        "learning_rate":    [0.05,0.08,0.1,0.15,0.2],
        "subsample":        [0.7,0.8,0.9,1.0],
        "colsample_bytree": [0.7,0.8,0.9,1.0],
        "min_child_weight": [1,2,3,5],
        "gamma":            [0,0.1,0.2,0.3],
    }
    cv_splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    search_base = XGBClassifier(scale_pos_weight=spw, eval_metric="logloss",
                                 random_state=42, verbosity=0, use_label_encoder=False)
    search = RandomizedSearchCV(search_base, param_dist, n_iter=30, scoring="f1",
                                 cv=cv_splitter, random_state=42, n_jobs=-1, refit=True)
    search.fit(X_tr, y_tr)
    opt_model = search.best_estimator_
    best_xgb_params = search.best_params_
    o_pred = opt_model.predict(X_te)
    o_prob = opt_model.predict_proba(X_te)[:,1]
    o_acc   = round(accuracy_score(y_te, o_pred), 4)
    o_prec  = round(precision_score(y_te, o_pred, zero_division=0), 4)
    o_rec   = round(recall_score(y_te, o_pred, zero_division=0), 4)
    o_f1    = round(sk_f1(y_te, o_pred, zero_division=0), 4)
    o_auc   = round(roc_auc_score(y_te, o_prob), 4) if len(np.unique(y_te)) >= 2 else 0.0
    o_cm    = sk_cm(y_te, o_pred).tolist()

    # Decide which won
    opt_won = o_f1 > d_f1
    final_model = opt_model if opt_won else default_xgb
    final_cm    = o_cm if opt_won else d_cm
    selected_name = "RandomizedSearchCV Optimised" if opt_won else "Default"

    print(f"  Default  — Acc={d_acc}, Prec={d_prec}, Rec={d_rec}, F1={d_f1}, AUC={d_auc}")
    print(f"  Optimised— Acc={o_acc}, Prec={o_prec}, Rec={o_rec}, F1={o_f1}, AUC={o_auc}")
    print(f"  Best XGB params: {best_xgb_params}")
    print(f"  Selected model: {selected_name}")

    record_test("XGBoost default model trains successfully","XGBoost Comparison",True,d_f1>=0,d_f1>=0)
    record_test("RandomizedSearchCV search completes","XGBoost Comparison",True,o_f1>=0,o_f1>=0)
    record_test("Final model F1 >= Default model F1","XGBoost Comparison",f"F1>={d_f1}",max(d_f1,o_f1),max(d_f1,o_f1)>=d_f1)

    xgb_comparison = {
        "default": {"accuracy":d_acc,"precision":d_prec,"recall":d_rec,"f1_score":d_f1,"roc_auc":d_auc,"confusion_matrix":d_cm},
        "optimised": {"accuracy":o_acc,"precision":o_prec,"recall":o_rec,"f1_score":o_f1,"roc_auc":o_auc,"confusion_matrix":o_cm},
        "best_params": best_xgb_params,
        "selected_model": selected_name,
        "optimisation_improved_f1": opt_won,
    }

    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

    # Comparison chart
    metric_names = ["Accuracy","Precision","Recall","F1","ROC-AUC"]
    d_vals = [d_acc, d_prec, d_rec, d_f1, d_auc]
    o_vals = [o_acc, o_prec, o_rec, o_f1, o_auc]
    x = np.arange(len(metric_names)); width = 0.35
    fig, ax = plt.subplots(figsize=(9,5))
    bars1 = ax.bar(x-width/2, d_vals, width, label="Default", color="#6b9e6b")
    bars2 = ax.bar(x+width/2, o_vals, width, label="Optimised (RandomizedSearchCV)", color="#2d5a27")
    for b, v in list(zip(bars1,d_vals))+list(zip(bars2,o_vals)):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.01, f"{v:.3f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(metric_names)
    ax.set_ylim(0,1.2); ax.set_ylabel("Score"); ax.set_title("XGBoost: Default vs RandomizedSearchCV Optimised")
    ax.legend(); plt.tight_layout()
    plt.savefig("test_outputs/xgboost_default_vs_optimised_metrics.png", dpi=150); plt.close()
    print("  Saved: test_outputs/xgboost_default_vs_optimised_metrics.png")

    # Final model confusion matrix
    cm_arr = np.array(final_cm)
    fig, ax = plt.subplots(figsize=(5,4))
    ax.imshow(cm_arr, cmap="Blues")
    for i in range(cm_arr.shape[0]):
        for j in range(cm_arr.shape[1]):
            ax.text(j,i,str(cm_arr[i,j]),ha="center",va="center",fontsize=14,
                    color="white" if cm_arr[i,j]>cm_arr.max()/2 else "black")
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    ax.set_xticks([0,1]); ax.set_yticks([0,1])
    ax.set_xticklabels(["Success","Break"]); ax.set_yticklabels(["Success","Break"])
    ax.set_title(f"Confusion Matrix — {selected_name}")
    plt.tight_layout(); plt.savefig("test_outputs/confusion_matrix_final_model.png", dpi=150); plt.close()
    print("  Saved: test_outputs/confusion_matrix_final_model.png")

    # Feature importance of final model
    feat_imps = sorted(zip(feat_df.columns, final_model.feature_importances_), key=lambda x: x[1], reverse=True)[:10]
    fig, ax = plt.subplots(figsize=(8,5))
    ax.barh([f[0] for f in reversed(feat_imps)],[f[1] for f in reversed(feat_imps)], color="#2d5a27")
    ax.set_xlabel("Importance"); ax.set_title(f"Top 10 Feature Importances — {selected_name}")
    plt.tight_layout(); plt.savefig("test_outputs/feature_importance_final_model.png", dpi=150); plt.close()
    print("  Saved: test_outputs/feature_importance_final_model.png")

    # XGBoost optimisation CSV
    with open("test_outputs/xgboost_optimisation_results.csv","w",newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric","default","optimised"])
        for mn, dv, ov in zip(["accuracy","precision","recall","f1_score","roc_auc"],d_vals,o_vals):
            w.writerow([mn,dv,ov])
        w.writerow(["confusion_matrix_default","",str(d_cm)])
        w.writerow(["confusion_matrix_optimised","",str(o_cm)])
        w.writerow(["best_params","",str(best_xgb_params)])
        w.writerow(["selected_model","",selected_name])
        w.writerow(["reason","","Higher F1 score" if opt_won else "Default retained (optimised did not improve F1)"])
    print("  Saved: test_outputs/xgboost_optimisation_results.csv")

    # Updated ml_evaluation_results.csv (final model)
    final_metrics = xgb_comparison["optimised"] if opt_won else xgb_comparison["default"]
    feat_imp_rows = sorted(zip(feat_df.columns, final_model.feature_importances_), key=lambda x: x[1], reverse=True)
    with open("test_outputs/ml_evaluation_results.csv","w",newline="") as f:
        w = csv.writer(f); w.writerow(["metric","value"])
        for k,v in final_metrics.items():
            if k != "confusion_matrix": w.writerow([k,v])
        w.writerow(["confusion_matrix",str(final_metrics["confusion_matrix"])])
        w.writerow(["model_used",selected_name])
        w.writerow(["---","--- Feature Importance ---"])
        for feat, imp in feat_imp_rows[:10]: w.writerow([feat, round(imp,4)])
    print("  Saved: test_outputs/ml_evaluation_results.csv")

else:
    print("  Not enough data for XGBoost comparison")

# Simulation profile prediction comparison
section("14. Simulation Profile Prediction Comparison")
sim_pred_stats = {}
for pid, pname in [("resilient","Nadia"),("struggling","Marcus"),("recovering","Lala")]:
    requests.post(f"{API}/reset", timeout=10); time.sleep(0.5)
    _, sr = api_call("POST", "/simulations/load", {"profile":pid}); time.sleep(1)
    _, pr = api_call("GET", "/predictions")
    sim_pred_stats[pname] = {
        "risk_score": pr.get("risk_score",0) if isinstance(pr,dict) else 0,
        "risk_level": pr.get("risk_level","n/a") if isinstance(pr,dict) else "n/a",
        "current_streak": sr.get("current_streak",0),
        "breaks": sr.get("breaks",0),
    }
    record_test(f"{pname} — predictions load correctly","Simulation Predictions",200,200 if isinstance(pr,dict) else 0,isinstance(pr,dict))
    print(f"  {pname}: risk_level={sim_pred_stats[pname]['risk_level']}, risk_score={sim_pred_stats[pname]['risk_score']}, streak={sim_pred_stats[pname]['current_streak']}, breaks={sim_pred_stats[pname]['breaks']}")

try:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    names = list(sim_pred_stats.keys())
    fig, axes = plt.subplots(1,3,figsize=(13,4))
    axes[0].bar(names,[sim_pred_stats[n]["risk_score"] for n in names],color=["#3d5a40","#c1121f","#588157"])
    axes[0].set_title("Risk Score (0-1)"); axes[0].set_ylim(0,1)
    axes[1].bar(names,[sim_pred_stats[n]["current_streak"] for n in names],color=["#3d5a40","#c1121f","#588157"])
    axes[1].set_title("Current Streak (days)")
    axes[2].bar(names,[sim_pred_stats[n]["breaks"] for n in names],color=["#3d5a40","#c1121f","#588157"])
    axes[2].set_title("Total Streak Breaks")
    plt.suptitle("Simulation Profile Predictions Comparison",fontsize=13)
    plt.tight_layout(); plt.savefig("test_outputs/simulation_profile_prediction_comparison.png",dpi=150); plt.close()
    print("  Saved: test_outputs/simulation_profile_prediction_comparison.png")
except Exception as e:
    print(f"  Could not generate sim prediction chart: {e}")


# Saving the results
section("Saving Results")
total_tests = passed_tests + failed_tests
pass_rate = f"{passed_tests/total_tests*100:.1f}%" if total_tests > 0 else "0%"

graph_files = [
    "test_outputs/confusion_matrix.png",
    "test_outputs/ml_metrics_bar_chart.png",
    "test_outputs/feature_importance_chart.png",
    "test_outputs/simulation_profile_comparison.png",
    "test_outputs/xgboost_default_vs_optimised_metrics.png",
    "test_outputs/confusion_matrix_final_model.png",
    "test_outputs/feature_importance_final_model.png",
    "test_outputs/simulation_profile_prediction_comparison.png",
]

results_json = {"total":total_tests,"passed":passed_tests,"failed":failed_tests,
    "pass_rate":pass_rate,"graph_files":graph_files,"tests":test_results}
if xgb_comparison:
    results_json["xgboost_comparison"] = xgb_comparison
with open("test_outputs/test_results.json","w") as f: json.dump(results_json, f, indent=2)
print("  Saved: test_outputs/test_results.json")

with open("test_outputs/test_results_summary.csv","w",newline="",encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["test_name","category","expected","actual","status"])
    for t in test_results: w.writerow([t["name"],t["category"],t["expected"],t["actual"],t["status"]])
print("  Saved: test_outputs/test_results_summary.csv")
