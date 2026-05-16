# Trains and uses an XGBoost machine learning model to predict if the user is likely to break their streak
# Turns each check in into a row of numbers and labels it as a success or failure
# Trains the XGBoost model on all past check ins and guesses a risk score for the newest check in
# Needs at least 20 check ins to train properly
# Safely deletes and retrains old saved models with the wrong data shape

import os
import json
import joblib
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.metrics import f1_score

from memory_manager import load_memory
from streak_system import SUCCESS_RULES


# File paths
MODEL_DIR  = "ml_models"
MODEL_PATH = os.path.join(MODEL_DIR, "streak_break_model.pkl")

# Helps detect old models with different features so we can safely delete them
# Any saved model with an older version gets deleted and retrained automatically
CURRENT_MODEL_VERSION = 3


# Feature column options
# Defines the allowed values for each category
# Uses them to convert text words into numbers for the ML model
TRIGGER_OPTIONS = ["stress", "boredom", "argument", "loneliness", "tiredness"]
MOOD_OPTIONS    = ["good", "okay", "low", "frustrated", "anxious"]
ENERGY_OPTIONS  = ["high", "normal", "low", "very low"]
TIME_OPTIONS    = ["morning", "afternoon", "evening", "night"]
ENV_OPTIONS     = ["alone", "with friends", "with family", "busy",
                   "online", "busy (work/school)", "mostly online"]
PROBLEM_OPTIONS = ["procrastination", "overspending", "isolation"]

# The weekly journal sentiment feature names
# Uses these exact names as columns in the data table
JOURNAL_FEATURE_NAMES = [
    "weekly_journal_distress_avg",
    "weekly_sadness_avg",
    "weekly_fear_avg",
    "weekly_anger_avg",
    "weekly_distress_trend",
    "journal_entry_count_week",
]


# Label for failure day
def is_failure(entry):
    # Returns 1 if the check-in was a streak break day or 0 if it was a success
    # Uses this to label the training data for the ML model
    problem = entry.get("problem", "procrastination")
    behaviour = entry.get("behaviour", "")
    success_list = SUCCESS_RULES.get(problem, [])
    return 0 if behaviour in success_list else 1


# Weekly journal features for ML
def get_journal_features_for_date(target_date, chat_log):
    # Calculates the weekly journal sentiment averages for a specific date
    # Looks at all the journal entries from the 7 days before the check-in
    # Uses weekly averages instead of single-message scores so the model sees a stable emotional trend
    from datetime import datetime, timedelta

    # Default empty values in case they didn't write any journal entries this week
    default_features = {
        "weekly_journal_distress_avg": 0.0,
        "weekly_sadness_avg": 0.0,
        "weekly_fear_avg": 0.0,
        "weekly_anger_avg": 0.0,
        "weekly_distress_trend": 0.0,
        "journal_entry_count_week": 0,
    }

    if not chat_log:
        return default_features

    try:
        end_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return default_features

    # Looks at journal entries from the 7 days before this check in
    start_date = end_date - timedelta(days=7)

    week_entries = []
    for journal_entry in chat_log:
        entry_date_str = journal_entry.get("timestamp", "")[:10]
        if not entry_date_str:
            continue
        try:
            entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        # Only includes entries from the week before the target date
        if start_date < entry_date <= end_date:
            week_entries.append(journal_entry)

    journal_entry_count_week = len(week_entries)

    if journal_entry_count_week == 0:
        return default_features

    # Calculates the weekly averages for distress and each core emotion
    distress_values = [e.get("distress_score", 0.0) for e in week_entries]
    weekly_journal_distress_avg = round(
        sum(distress_values) / journal_entry_count_week, 4
    )
    weekly_sadness_avg = round(
        sum(e.get("emotions", {}).get("sadness", 0.0) for e in week_entries)
        / journal_entry_count_week, 4
    )
    weekly_fear_avg = round(
        sum(e.get("emotions", {}).get("fear", 0.0) for e in week_entries)
        / journal_entry_count_week, 4
    )
    weekly_anger_avg = round(
        sum(e.get("emotions", {}).get("anger", 0.0) for e in week_entries)
        / journal_entry_count_week, 4
    )

    # Distress trend is the average of second half minus average of first half
    # Positive means getting worse, negative means getting better
    half = journal_entry_count_week // 2
    if half > 0:
        first_half_avg = sum(distress_values[:half]) / half
        second_half_avg = sum(distress_values[half:]) / max(
            journal_entry_count_week - half, 1
        )
        weekly_distress_trend = round(second_half_avg - first_half_avg, 4)
    else:
        weekly_distress_trend = 0.0

    return {
        "weekly_journal_distress_avg": weekly_journal_distress_avg,
        "weekly_sadness_avg": weekly_sadness_avg,
        "weekly_fear_avg": weekly_fear_avg,
        "weekly_anger_avg": weekly_anger_avg,
        "weekly_distress_trend": weekly_distress_trend,
        "journal_entry_count_week": journal_entry_count_week,
    }


# Feature builder
def entry_to_features(entry, idx=0, all_checkins=None, chat_log=None):
    # Converts a single check-in entry into a dictionary of numbers for the XGBoost model
    # Returns a dictionary where every single value is a number
    feature_row = {}

    # Converts the text categories into simple number codes
    feature_row["mood"]       = MOOD_OPTIONS.index(entry.get("mood", "okay"))       if entry.get("mood")       in MOOD_OPTIONS       else 1
    feature_row["energy"]     = ENERGY_OPTIONS.index(entry.get("energy", "normal")) if entry.get("energy")     in ENERGY_OPTIONS     else 1
    feature_row["time_of_day"]= TIME_OPTIONS.index(entry.get("time_of_day", "afternoon")) if entry.get("time_of_day") in TIME_OPTIONS else 1
    feature_row["problem"]    = PROBLEM_OPTIONS.index(entry.get("problem", "procrastination")) if entry.get("problem") in PROBLEM_OPTIONS else 0

    # One hot encodes the environment
    environment = (entry.get("environment") or "").lower()
    for env_option in ENV_OPTIONS:
        feature_row[f"env_{env_option}"] = 1 if env_option in environment else 0

    # Multi hot encodes the triggers because there can be more than one active at a time
    active_triggers = [t.lower() for t in entry.get("triggers", [])]
    for trigger_option in TRIGGER_OPTIONS:
        feature_row[f"trigger_{trigger_option}"] = 1 if trigger_option in active_triggers else 0

    # The length of the streak at the exact time of this check-in
    feature_row["current_streak"] = entry.get("_current_streak", 0)

    # Counts how many failures happened in the last 3 and 7 check-ins
    # Gives the model some recent history context
    if all_checkins and idx > 0:
        last_3 = all_checkins[max(0, idx - 3):idx]
        last_7 = all_checkins[max(0, idx - 7):idx]
        feature_row["failures_last_3"] = sum(1 for c in last_3 if is_failure(c))
        feature_row["failures_last_7"] = sum(1 for c in last_7 if is_failure(c))
    else:
        feature_row["failures_last_3"] = 0
        feature_row["failures_last_7"] = 0

    # Weekly journal sentiment features
    # Captures the user's emotional tone in the 7 days leading up to this check-in
    # Uses weekly numbers instead of single message sentiment to avoid jumping to conclusions
    checkin_date = entry.get("date", "")
    journal_features = get_journal_features_for_date(checkin_date, chat_log or [])
    feature_row.update(journal_features)

    return feature_row


# Model compatibility check
def is_model_compatible():
    # Checks if the saved model file matches our current features
    # Deletes and retrains the saved model if it has an old version number or is missing columns
    # Returns True if it is fine, False if it needs to retrain
    if not os.path.exists(MODEL_PATH):
        return False

    try:
        saved_pipeline = joblib.load(MODEL_PATH)
    except Exception:
        return False

    # Checks the version tag first
    saved_version = saved_pipeline.get("model_version", 1)
    if saved_version != CURRENT_MODEL_VERSION:
        return False

    # Verifies that the journal feature columns actually exist in the saved model
    saved_columns = saved_pipeline.get("columns", [])
    for journal_col in JOURNAL_FEATURE_NAMES:
        if journal_col not in saved_columns:
            return False

    return True


# Train the model
def train_streak_model():
    # Trains the XGBoost classifier on all of the user's past check ins
    # Needs at least 20 check ins and at least one failure and success to learn anything
    # Deletes old models with wrong features and trains a fresh one
    # Saves the trained model to disk
    memory = load_memory()
    checkins = memory.get("daily_checkins", [])
    chat_log = memory.get("chat_log", [])

    # Checks if we have enough data to train
    if len(checkins) < 20:
        return {
            "trained": False,
            "message": f"Need at least 20 check-ins to train. Currently have {len(checkins)}."
        }

    # Deletes any old or broken models before training
    if os.path.exists(MODEL_PATH) and not is_model_compatible():
        os.remove(MODEL_PATH)

    # Injects the running streak length at each point in time
    running_streak = 0
    for checkin in checkins:
        checkin["_current_streak"] = running_streak
        if is_failure(checkin):
            running_streak = 0
        else:
            running_streak += 1

    # Builds the feature rows and the target labels for each check in
    # Passes the chat log so the weekly journal features can be calculated
    feature_rows = []
    labels = []
    for i, checkin in enumerate(checkins):
        feature_rows.append(
            entry_to_features(checkin, i, checkins, chat_log=chat_log)
        )
        labels.append(is_failure(checkin))

    feature_df = pd.DataFrame(feature_rows)
    label_array = np.array(labels)

    # Returns False if all the days have the same outcome
    unique_classes = np.unique(label_array)
    if len(unique_classes) < 2:
        return {
            "trained": False,
            "message": "Not enough variety in data — all days are the same outcome. Keep logging diverse check-ins."
        }

    # Balances the training data by tweaking the class weights
    n_failures = label_array.sum()
    n_successes = len(label_array) - n_failures
    class_balance_weight = max(n_successes / max(n_failures, 1), 1.0)

    # Step 1: Training the default XGBoost model
    default_model = XGBClassifier(
        n_estimators=80,
        max_depth=4,
        learning_rate=0.1,
        scale_pos_weight=class_balance_weight,
        eval_metric="logloss",
        random_state=42,
        verbosity=0
    )
    default_model.fit(feature_df, label_array)

    # Step 2: Trying to improve it with RandomizedSearchCV
    # Only runs the optimisation search when there are enough samples and variety
    optimisation_used = False
    best_params = None
    chosen_model = default_model

    if len(feature_df) >= 30 and len(np.unique(label_array)) >= 2:
        chosen_model, optimisation_used, best_params = _run_randomised_search(
            feature_df, label_array, class_balance_weight, default_model
        )

    # Saves the chosen best model and its column list to the disk
    os.makedirs(MODEL_DIR, exist_ok=True)
    saved_pipeline = {
        "model":              chosen_model,
        "columns":            list(feature_df.columns),
        "n_samples":          len(feature_df),
        "n_positive":         int(n_failures),
        "n_negative":         int(n_successes),
        "model_version":      CURRENT_MODEL_VERSION,
        "optimisation_used":  optimisation_used,
        "best_params":        best_params,
    }
    joblib.dump(saved_pipeline, MODEL_PATH)

    opt_note = " (RandomizedSearchCV optimised)" if optimisation_used else " (default parameters)"
    return {
        "trained": True,
        "message": f"Model trained on {len(feature_df)} check-ins ({int(n_failures)} failures, {int(n_successes)} successes){opt_note}.",
        "model_type": "xgboost",
        "optimisation_used": optimisation_used,
        "best_params": best_params,
    }


# RandomisedSearchCV optimisation
def _run_randomised_search(feature_df, label_array, class_balance_weight, default_model):
    # Runs RandomizedSearchCV to find better XGBoost settings
    # Holds out 20% of the data to test the default model against the optimised model
    # Holds out 20% of the data to compare the default vs optimised model fairly
    X_train, X_val, y_train, y_val = train_test_split(
        feature_df, label_array, test_size=0.2, random_state=42, stratify=label_array
        if len(np.unique(label_array)) >= 2 and min(np.bincount(label_array)) >= 2
        else None
    )

    # Tests the F1 score of the default model on the validation split
    default_val_pred = default_model.predict(X_val)
    default_f1 = f1_score(y_val, default_val_pred, zero_division=0)

    # The settings grid we want RandomizedSearchCV to try out
    param_distributions = {
        "n_estimators":      [50, 80, 100, 150, 200],
        "max_depth":         [3, 4, 5, 6],
        "learning_rate":     [0.05, 0.08, 0.1, 0.15, 0.2],
        "subsample":         [0.7, 0.8, 0.9, 1.0],
        "colsample_bytree":  [0.7, 0.8, 0.9, 1.0],
        "min_child_weight":  [1, 2, 3, 5],
        "gamma":             [0, 0.1, 0.2, 0.3],
    }

    # Uses stratified k fold so every slice of data gets both successes and failures
    cross_val_splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    search_base = XGBClassifier(
        scale_pos_weight=class_balance_weight,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
        use_label_encoder=False,
    )

    try:
        search = RandomizedSearchCV(
            estimator=search_base,
            param_distributions=param_distributions,
            n_iter=30,
            scoring="f1",
            cv=cross_val_splitter,
            random_state=42,
            n_jobs=-1,
            refit=True,
        )
        search.fit(X_train, y_train)
        optimised_model = search.best_estimator_
        best_params = search.best_params_

        # Compares the new model on the exact same held out validation set
        optimised_val_pred = optimised_model.predict(X_val)
        optimised_f1 = f1_score(y_val, optimised_val_pred, zero_division=0)

        # Only switches to the optimised model if it is strictly better
        if optimised_f1 > default_f1:
            # Re-fits the winner on the full dataset before saving it
            optimised_model.fit(feature_df, label_array)
            return optimised_model, True, best_params
        else:
            # Returns the default model
            return default_model, False, best_params

    except Exception:
        # Silently falls back to the default if the search fails
        return default_model, False, None


# Predicts streak break risk

def predict_streak_break_risk(current_entry=None):
    # Loads the trained ML model and predicts how likely the user is to break their streak
    # Tries to train one if there is no model saved yet
    # Retrains automatically if the saved model is too old or incompatible
    # Checks if the model needs retraining due to a version mismatch
    if not os.path.exists(MODEL_PATH) or not is_model_compatible():
        train_result = train_streak_model()
        if not train_result.get("trained"):
            return {
                "available": False,
                "model_type": "xgboost",
                "risk_level": "not enough data",
                "message": train_result.get("message", "Need at least 20 check-ins to train ML model.")
            }

    # Loads the saved model from the disk
    try:
        saved_pipeline = joblib.load(MODEL_PATH)
    except Exception:
        return {
            "available": False,
            "model_type": "xgboost",
            "risk_level": "model error",
            "message": "Could not load the prediction model."
        }

    model   = saved_pipeline["model"]
    columns = saved_pipeline["columns"]

    # Uses the most recent check-in if a specific one is not passed
    memory = load_memory()
    checkins = memory.get("daily_checkins", [])
    chat_log = memory.get("chat_log", [])

    if current_entry is None and checkins:
        current_entry = checkins[-1]
    elif current_entry is None:
        return {
            "available": False,
            "model_type": "xgboost",
            "risk_level": "no data",
            "message": "No check-in data to predict from."
        }

    # Attaches the current streak length to the entry so the model knows it
    streak_data = memory.get("streak", {})
    current_entry["_current_streak"] = streak_data.get("current_days", 0)

    # Builds the feature vector for this check in including the journal features
    features = entry_to_features(
        current_entry, len(checkins) - 1, checkins, chat_log=chat_log
    )
    prediction_df = pd.DataFrame([features])

    # Makes sure our columns line up with what the model was trained on
    for col in columns:
        if col not in prediction_df.columns:
            prediction_df[col] = 0
    prediction_df = prediction_df[columns]

    # Gets the probability that this specific day is a failure
    prob_array = model.predict_proba(prediction_df)[0]
    risk_score = float(prob_array[1]) if len(prob_array) > 1 else 0.0

    # Converts the probability score into a simple human readable risk level
    if risk_score >= 0.65:
        risk_level = "high"
    elif risk_score >= 0.35:
        risk_level = "medium"
    else:
        risk_level = "low"

    # Gets the top features that drove this prediction result
    top_factors = get_feature_importance(model, columns, top_n=5)

    return {
        "available":  True,
        "model_type": "xgboost",
        "risk_score": round(risk_score, 3),
        "risk_level": risk_level,
        "top_factors": top_factors
    }


# Feature importance
def get_feature_importance(model=None, columns=None, top_n=5):
    # Returns the top N most important features from the trained model with human readable names
    # Loads them from the saved file if model or columns are not provided
    # Returns a list of feature name strings
    if model is None or columns is None:
        if not os.path.exists(MODEL_PATH):
            return []
        saved_pipeline = joblib.load(MODEL_PATH)
        model   = saved_pipeline["model"]
        columns = saved_pipeline["columns"]

    importances = model.feature_importances_

    # Sorts the features by how important they were
    sorted_pairs = sorted(zip(columns, importances), key=lambda pair: pair[1], reverse=True)

    # Maps internal ML column names to plain English user facing descriptions
    readable_names = {
        # Core check-in fields
        "mood":             "Your mood that day",
        "energy":           "Your energy level",
        "time_of_day":      "Time of day",
        "problem":          "Your focus area",
        "current_streak":   "Streak Length",
        "failures_last_3":  "Struggles in last 3 days",
        "failures_last_7":  "Struggles in last 7 days",
        # Trigger features
        "trigger_stress":       "Feeling stressed",
        "trigger_boredom":      "Feeling bored",
        "trigger_argument":     "After an argument",
        "trigger_loneliness":   "Feeling lonely",
        "trigger_tiredness":    "Feeling tired",
        # Environment features
        "env_alone":               "Being alone",
        "env_with friends":        "Being with friends",
        "env_with family":         "Being with family",
        "env_busy":                "Busy environment",
        "env_online":              "Spending time online",
        "env_busy (work/school)":  "Work or school pressure",
        "env_mostly online":       "Mostly online",
        # Weekly journal sentiment features
        "weekly_journal_distress_avg":  "Journal distress (this week)",
        "weekly_sadness_avg":           "Sadness in journal entries",
        "weekly_fear_avg":              "Anxiety in journal entries",
        "weekly_anger_avg":             "Frustration in journal entries",
        "weekly_distress_trend":        "Worsening emotional trend",
        "journal_entry_count_week":     "Journal activity this week",
    }

    top_features = []
    for col, importance in sorted_pairs[:top_n]:
        # Only includes factors that had above 2% importance
        if importance > 0.02:
            readable = readable_names.get(col)
            # Falls back to a cleaned up version of the column name if we forgot to add it to the map
            if not readable:
                readable = col.replace("_", " ").replace("env ", "Environment: ").title()
            top_features.append(readable)

    return top_features


# Model status
def model_status():
    # Returns a summary of how the model is doing
    if not os.path.exists(MODEL_PATH):
        memory = load_memory()
        checkin_count = len(memory.get("daily_checkins", []))
        return {
            "trained":             False,
            "model_type":          "xgboost",
            "checkins_available":  checkin_count,
            "checkins_needed":     20,
            "message":             f"Need {max(20 - checkin_count, 0)} more check-ins to train."
        }

    saved_pipeline = joblib.load(MODEL_PATH)
    return {
        "trained":             True,
        "model_type":          "xgboost",
        "model_version":       saved_pipeline.get("model_version", 1),
        "n_samples":           saved_pipeline.get("n_samples",  0),
        "n_positive":          saved_pipeline.get("n_positive", 0),
        "n_negative":          saved_pipeline.get("n_negative", 0),
        "optimisation_used":   saved_pipeline.get("optimisation_used", False),
        "best_params":         saved_pipeline.get("best_params", None),
    }


# Testing
if __name__ == "__main__":
    print("=== Model Status ===")
    print(json.dumps(model_status(), indent=2))

    print("\n=== Training ===")
    print(json.dumps(train_streak_model(), indent=2))

    print("\n=== Prediction ===")
    print(json.dumps(predict_streak_break_risk(), indent=2))
