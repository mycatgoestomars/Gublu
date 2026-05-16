# Selects the most relevant insight based on user input, patterns, and predictions
import re


# Keyword extraction
def extract_keywords(text):
    text = text.lower()

    keywords = [
        "stress", "boredom", "argument", "loneliness",
        "tired", "exam", "work", "money",
        "alone", "friends", "family",
        "night", "morning", "afternoon",
        "procrastinate", "spend", "isolate"
    ]

    found = [k for k in keywords if k in text]
    return found


# Scoring function
def score_insight(insight, keywords):
    score = 0

    insight_lower = insight.lower()

    for word in keywords:
        if word in insight_lower:
            score += 1

    return score


# Selects best insight
def select_best_insight(user_text, patterns, predictions):

    keywords = extract_keywords(user_text)

    all_insights = patterns + predictions

    if not all_insights:
        return None

    best = None
    best_score = 0

    for insight in all_insights:
        score = score_insight(insight, keywords)

        if score > best_score:
            best_score = score
            best = insight

    # Falls back to the first prediction or pattern in the list if nothing matches
    if best is None:
        if predictions:
            return predictions[0]
        if patterns:
            return patterns[0]

    return best