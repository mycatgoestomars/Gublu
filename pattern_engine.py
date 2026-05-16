# Analyses the user's check-in history to find repeating patterns in triggers, times, and behaviours
# Detects daily patterns and streak break patterns for the decision engine and chatbot to use

from collections import Counter
from memory_manager import load_memory, save_memory


# Helper to find most common item

def most_common(items):
    # Takes a list and returns the most frequent item along with how many times it appeared
    # Removes any empty or None values
    filtered = [item for item in items if item]
    if not filtered:
        return None, 0

    counter = Counter(filtered)
    return counter.most_common(1)[0]


# Daily pattern detection

def detect_daily_patterns():
    # Looks at the last 7 check-ins and finds repeated patterns
    # Saves these insights to memory so other engines can use them
    memory = load_memory()
    checkins = memory.get("daily_checkins", [])

    # Needs at least 3 check-ins before spotting a pattern
    if len(checkins) < 3:
        return ["Not enough daily check-in data yet to detect patterns."]

    insights = []

    # Looks at the 7 most recent check-ins
    recent_checkins = checkins[-7:]

    # Trigger pattern
    all_triggers = []
    for entry in recent_checkins:
        all_triggers.extend(entry.get("triggers", []))

    top_trigger, trigger_count = most_common(all_triggers)
    if top_trigger and top_trigger != "nothing" and trigger_count >= 2:
        insights.append(f"You often report '{top_trigger}' as a trigger.")

    # Time of day pattern
    times = [entry.get("time_of_day") for entry in recent_checkins]
    common_time, time_count = most_common(times)
    if common_time and time_count >= 2:
        insights.append(f"Your difficult moments often happen during the {common_time}.")

    # Environment pattern
    environments = [entry.get("environment") for entry in recent_checkins]
    common_env, env_count = most_common(environments)
    if common_env and env_count >= 2:
        insights.append(f"Your environment is often '{common_env}' during check-ins.")

    # Behaviour pattern
    behaviours = [entry.get("behaviour") for entry in recent_checkins]
    common_behaviour, behaviour_count = most_common(behaviours)
    if common_behaviour and behaviour_count >= 2:
        insights.append(f"Your recent behaviour often appears as '{common_behaviour}'.")

    if not insights:
        insights.append("No strong repeated pattern detected yet.")

    # Saves the detected patterns to memory for other engines to use
    memory["patterns"] = insights
    save_memory(memory)

    return insights


# Streak break pattern detection
def detect_streak_break_patterns():
    # Looks at all recorded streak breaks and finds patterns in what triggered the failures
    # Helps the chatbot warn the user about high-risk situations
    memory = load_memory()
    streak_breaks = memory.get("streak_breaks", [])

    # Needs at least 2 breaks before comparing them makes any sense
    if len(streak_breaks) < 2:
        return ["Not enough streak break history yet to compare break patterns."]

    insights = []

    # Trigger pattern across breaks
    all_triggers = []
    for entry in streak_breaks:
        all_triggers.extend(entry.get("triggers", []))

    top_trigger, trigger_count = most_common(all_triggers)
    if top_trigger and top_trigger != "nothing" and trigger_count >= 2:
        insights.append(f"Streak breaks are often linked to '{top_trigger}'.")

    # Time of day pattern across breaks
    times = [entry.get("time_of_day") for entry in streak_breaks]
    common_time, time_count = most_common(times)
    if common_time and time_count >= 2:
        insights.append(f"Streak breaks often happen during the {common_time}.")

    # Environment pattern across breaks
    environments = [entry.get("environment") for entry in streak_breaks]
    common_env, env_count = most_common(environments)
    if common_env and env_count >= 2:
        insights.append(f"Streak breaks often happen when your environment is '{common_env}'.")

    # Behaviour pattern across breaks
    behaviours = [entry.get("behaviour") for entry in streak_breaks]
    common_behaviour, behaviour_count = most_common(behaviours)
    if common_behaviour and behaviour_count >= 2:
        insights.append(f"A recurring break behaviour is '{common_behaviour}'.")

    if not insights:
        insights.append("No repeated streak break pattern detected yet.")

    return insights


# Gets all patterns main entry
def get_all_patterns():
    # Runs both detection functions and returns their results together
    daily = detect_daily_patterns()
    break_patterns = detect_streak_break_patterns()

    return {
        "daily_patterns": daily,
        "streak_break_patterns": break_patterns
    }


# Test

if __name__ == "__main__":
    results = get_all_patterns()

    print("\n===== DAILY PATTERNS =====")
    for item in results["daily_patterns"]:
        print("-", item)

    print("\n===== STREAK BREAK PATTERNS =====")
    for item in results["streak_break_patterns"]:
        print("-", item)