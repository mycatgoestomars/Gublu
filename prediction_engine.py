# Generates forward-looking predictions based on user check-in history and streak break records
# Predicts behaviour risk, streak break risk, and trigger combinations
# Feeds combined predictions into the decision engine and chatbot

from collections import Counter
from memory_manager import load_memory


# Helper to find most common item
def most_common(items):
    # Returns the most frequent item in a list and how many times it appeared
    # Returns None and 0 if the list is empty
    filtered = [item for item in items if item]
    if not filtered:
        return None, 0
    counter = Counter(filtered)
    return counter.most_common(1)[0]


# Predicts behaviour risk
def predict_behaviour_risk():
    # Checks if a negative behaviour has repeated 3 or more times in the last 7 check-ins
    # Warns the user they may repeat it again soon
    memory = load_memory()
    checkins = memory.get("daily_checkins", [])

    if len(checkins) < 5:
        return "Not enough data to predict behaviour yet."

    recent_checkins = checkins[-7:]

    behaviours = [c["behaviour"] for c in recent_checkins]
    top_behaviour, behaviour_count = most_common(behaviours)

    # Only warns if a clearly negative behaviour dominates recent history
    if top_behaviour in ["procrastinated", "overspent", "avoided tasks"] and behaviour_count >= 3:
        return f"You may repeat '{top_behaviour}' soon."

    return "No strong negative behaviour predicted."


# Predicts streak break risk
def predict_streak_risk():
    # Looks at past streak break records to find a trigger that has repeatedly caused breaks
    # Returns a warning if a trigger appears 2 or more times
    memory = load_memory()
    streak_breaks = memory.get("streak_breaks", [])

    if len(streak_breaks) < 2:
        return "Not enough streak history to predict breaks."

    # Collects all triggers from all past break events
    all_break_triggers = []
    for break_event in streak_breaks:
        all_break_triggers.extend(break_event.get("triggers", []))

    top_trigger, trigger_count = most_common(all_break_triggers)

    if top_trigger and trigger_count >= 2:
        return f"Be careful: '{top_trigger}' has led to streak breaks before."

    return "No strong streak break risk detected."


# Predicts trigger and time combination
def predict_trigger_combo():
    # Looks for a recurring trigger and time combination across all check-ins
    # Returns a warning if the same trigger appears at the same time of day 3 or more times
    memory = load_memory()
    checkins = memory.get("daily_checkins", [])

    if len(checkins) < 5:
        return None

    # Builds trigger and time pairs from every single check-in
    trigger_time_combos = []
    for entry in checkins:
        for trigger in entry.get("triggers", []):
            combo = (trigger, entry.get("time_of_day"))
            trigger_time_combos.append(combo)

    top_combo, combo_count = most_common(trigger_time_combos)

    if top_combo and combo_count >= 3:
        trigger, time_slot = top_combo
        return f"Pattern detected: '{trigger}' during {time_slot} often leads to difficulty."

    return None


# Gets all predictions
def get_predictions():
    # Runs all prediction functions and returns the results as a list
    # Only includes non-None results
    behaviour_prediction = predict_behaviour_risk()
    streak_prediction = predict_streak_risk()
    combo_prediction = predict_trigger_combo()

    prediction_list = []

    if behaviour_prediction:
        prediction_list.append(behaviour_prediction)

    if streak_prediction:
        prediction_list.append(streak_prediction)

    if combo_prediction:
        prediction_list.append(combo_prediction)

    return prediction_list


# Testing the predictor engine
if __name__ == "__main__":

    predictions = get_predictions()

    print("\n===== PREDICTIONS =====")
    for prediction in predictions:
        print("-", prediction)