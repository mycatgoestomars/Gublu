# Picks the single most important insight to show the user
# Pulls insights from daily patterns, streak break patterns, future predictions, and multi-signal reasoning
# Scores each insight based on the words it contains and its source
# Shows the highest-scoring insight on the dashboard and in the chat

from memory_manager import load_memory
from pattern_engine import get_all_patterns
from prediction_engine import get_predictions
from reasoning_engine import get_multi_signal_insights


# Priority word lists
HIGH_PRIORITY_WORDS = [
    "streak break",
    "break",
    "risk",
    "procrastinated",
    "avoided tasks",
    "overspent",
    "impulse purchase",
    "completely isolated",
    "minimal interaction"
]

# Words that suggest we should be a bit careful giving a smaller score boost
MEDIUM_PRIORITY_WORDS = [
    "stress",
    "tiredness",
    "low",
    "argument",
    "loneliness",
    "night",
    "evening",
    "boredom"
]


# Insight scoring
def score_insight(insight):
    # Scores an insight text based on how urgent or useful it is
    # Subtracts points for generic 'not enough data' messages so they get ignored if possible
    lowered = insight.lower()
    score = 0

    for word in HIGH_PRIORITY_WORDS:
        if word in lowered:
            score += 3

    for word in MEDIUM_PRIORITY_WORDS:
        if word in lowered:
            score += 1

    # Penalises generic "not enough data" messages so they show up less
    if "not enough data" in lowered:
        score -= 5

    # Penalises weak "no strong pattern" messages
    if "no strong" in lowered:
        score -= 3

    return score


# Collects all available insights
def get_all_available_insights():
    # Gathers insights from all four engines and puts them into one list
    # Each insight gets a type, the text, and a source weight based on how reliable the system is
    all_patterns = get_all_patterns()
    predictions = get_predictions()
    reasoning_insights = get_multi_signal_insights()

    all_insights = []

    for item in all_patterns.get("daily_patterns", []):
        all_insights.append({
            "type": "daily_pattern",
            "text": item,
            "source_weight": 1
        })

    for item in all_patterns.get("streak_break_patterns", []):
        all_insights.append({
            "type": "streak_break_pattern",
            "text": item,
            "source_weight": 3
        })

    for item in predictions:
        all_insights.append({
            "type": "prediction",
            "text": item,
            "source_weight": 3
        })

    for item in reasoning_insights:
        all_insights.append({
            "type": "multi_signal_reasoning",
            "text": item,
            "source_weight": 4
        })

    return all_insights


# Chooses the best insight
def choose_best_insight():
    # Scores all available insights and returns the one with the highest score
    # Returns None if nothing scores above 0
    all_insights = get_all_available_insights()

    if not all_insights:
        return None

    best_insight = None
    best_score = -999

    for insight in all_insights:
        # Combines the keyword score with the source's natural weight
        keyword_score = score_insight(insight["text"])
        total_score = keyword_score + insight["source_weight"]

        insight["score"] = total_score

        if total_score > best_score:
            best_score = total_score
            best_insight = insight

    # Only returns it if it actually scored positively
    if best_insight and best_insight["score"] > 0:
        return best_insight

    return None


# Builds decision message
def build_decision_message():
    # Selects the best insight and turns it into a natural-sounding sentence
    # The starting phrase changes depending on where the insight came from
    best_insight = choose_best_insight()

    if not best_insight:
        return "No strong decision insight is available yet."

    insight_type = best_insight["type"]
    insight_text = best_insight["text"]

    # Picks a natural prefix based on the insight's source
    if insight_type == "multi_signal_reasoning":
        prefix = "The strongest pattern I noticed is:"
    elif insight_type == "prediction":
        prefix = "The most important prediction is:"
    elif insight_type == "streak_break_pattern":
        prefix = "The most important streak-break pattern is:"
    else:
        prefix = "One useful pattern is:"

    return f"{prefix} {insight_text}"


# Test
if __name__ == "__main__":
    print("\n===== SMART DECISION =====")
    print(build_decision_message())