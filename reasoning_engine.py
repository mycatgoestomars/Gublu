# Finds meaningful combinations of factors that repeatedly appear before negative behaviours
# Looks at combinations of trigger, energy, environment, and time to produce stronger warnings
# These insights are ranked highly by the decision engine

from collections import Counter
from memory_manager import load_memory

# The behaviours that count as a failure for each problem type
# Only looks at days with these behaviours when building combinations
NEGATIVE_BEHAVIOURS = [
    "procrastinated",
    "avoided tasks",
    "impulse purchase",
    "overspent",
    "minimal interaction",
    "completely isolated"
]


# Builds combinations from entry
# Takes a single check in entry and builds a list of groupings
# Creates combinations of trigger, signal, time, and behaviour
def build_combo(entry):
    triggers = entry.get("triggers", [])
    energy = entry.get("energy")
    time_slot = entry.get("time_of_day")
    environment = entry.get("environment")
    behaviour = entry.get("behaviour")

    combos = []

    for trigger in triggers:
        if trigger != "nothing":
            combos.append((trigger, energy, time_slot, behaviour)) # Combines the trigger with the energy context
            combos.append((trigger, environment, time_slot, behaviour)) # Combines the trigger with the environment context

    return combos


# Multi signal insight detection
# Analyses all check ins to find recurring combinations of factors that lead to negative behaviours
# Only considers entries where the behaviour was negative
def get_multi_signal_insights():

    memory = load_memory()
    checkins = memory.get("daily_checkins", [])

    if len(checkins) < 4:
        return ["Not enough data yet for multi-signal reasoning."]

    all_combos = []

    # Only builds combinations for days where the behaviour was negative
    for entry in checkins:
        behaviour = entry.get("behaviour")
        if behaviour in NEGATIVE_BEHAVIOURS:
            all_combos.extend(build_combo(entry))

    if not all_combos:
        return ["No strong negative behaviour combinations detected yet."]

    # Counts how often each combination appeared
    combo_counter = Counter(all_combos)
    insights = []

    # Only reports combinations that have appeared at least twice
    for combo, count in combo_counter.most_common(3):
        if count >= 2:
            trigger, second_signal, time_slot, behaviour = combo

            insights.append(
                f"When '{trigger}' combines with '{second_signal}' during the {time_slot}, "
                f"it is often linked to '{behaviour}'."
            )

    if not insights:
        insights.append("No repeated multi-signal pattern detected yet.")

    return insights


# Gets the strongest single insight
# Returns only the top most repeated multi signal insight or None if nothing was found
def get_strongest_reasoning_insight():
    insights = get_multi_signal_insights()

    if not insights:
        return None

    return insights[0]


# Testing the model
if __name__ == "__main__":
    print("\n===== MULTI-SIGNAL INSIGHTS =====")
    for insight in get_multi_signal_insights():
        print("-", insight)