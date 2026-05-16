# Takes emotion scores, converts them into fuzzy levels, applies rules, and produces a final assessment
# Models emotional uncertainty better than hard binary rules


# Triangular membership function

def triangular(x, a, b, c):
    # Computes the membership degree of x in a triangular fuzzy set

    # Outside the triangle
    if x <= a or x >= c:
        return 0.0

    # At the peak
    if x == b:
        return 1.0

    # Rising edge
    if a < x < b:
        return (x - a) / (b - a)

    # Falling edge
    if b < x < c:
        return (c - x) / (c - b)

    return 0.0


# Fuzzifies a single emotion score

def fuzzify_emotion(value):
    # Converts a raw emotion score into fuzzy memberships
    memberships = {
        "low": triangular(value, 0.0, 0.0, 0.5),
        "medium": triangular(value, 0.0, 0.5, 1.0),
        "high": triangular(value, 0.5, 1.0, 1.0)
    }

    return memberships


# Fuzzifies all emotions
def fuzzify_all_emotions(emotion_scores):
    # Applies fuzzification to each emotion score
    fuzzy_scores = {}
    for emotion, value in emotion_scores.items():
        fuzzy_scores[emotion] = fuzzify_emotion(value)
    return fuzzy_scores


# Applies fuzzy rules
def apply_fuzzy_rules(fuzzy_scores):
    # Applies fuzzy inference rules to determine emotional distress

    fear = fuzzy_scores["fear"]
    sadness = fuzzy_scores["sadness"]
    anger = fuzzy_scores["anger"]
    joy = fuzzy_scores["joy"]

    # Rule strengths
    rule_1 = fear["high"]
    rule_2 = sadness["high"]
    rule_3 = anger["high"]
    rule_4 = joy["high"]
    rule_5 = min(fear["medium"], sadness["medium"])

    distress = {
        "low": max(rule_4, 0.0),
        "medium": max(rule_3, rule_5),
        "high": max(rule_1, rule_2)
    }

    return distress


# Defuzzification
def defuzzify_distress(distress_memberships):
    # Converts fuzzy distress memberships into a single crisp number

    low_value = 0.2
    medium_value = 0.5
    high_value = 0.9

    numerator = (
        distress_memberships["low"] * low_value +
        distress_memberships["medium"] * medium_value +
        distress_memberships["high"] * high_value
    )

    denominator = (
        distress_memberships["low"] +
        distress_memberships["medium"] +
        distress_memberships["high"]
    )

    if denominator == 0:
        return 0.0

    return numerator / denominator


# Final fuzzy decision
def fuzzy_emotional_assessment(emotion_scores):
    # Runs the full fuzzy pipeline to return memberships, scores, and labels

    fuzzy_scores = fuzzify_all_emotions(emotion_scores)
    distress_memberships = apply_fuzzy_rules(fuzzy_scores)
    distress_score = defuzzify_distress(distress_memberships)

    if distress_score < 0.35:
        label = "low distress"
    elif distress_score < 0.7:
        label = "moderate distress"
    else:
        label = "high distress"

    return {
        "fuzzy_scores": fuzzy_scores,
        "distress_memberships": distress_memberships,
        "distress_score": distress_score,
        "label": label
    }