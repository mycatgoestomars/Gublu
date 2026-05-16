# Applies custom rules on top of raw emotion scores to make sure common expressions are caught accurately
# Helps fix ML model confusion with negations, strong negative phrases, and negative words


# Word and phrase lists

# Phrases with negation which mean we should flip joy to sadness
NEGATION_PATTERNS = [
    "not happy",
    "not feeling good",
    "dont feel good",
    "don't feel good",
    "not okay",
    "not fine",
    "not great",
    "not doing well"
]

# Single negative words that give a big boost to the sadness score
NEGATIVE_WORDS = [
    "hopeless",
    "worthless",
    "empty",
    "tired",
    "exhausted",
    "lost",
    "failure",
    "pointless",
    "useless",
    "numb",
    "drained",
    "overwhelmed"
]

# Strong multi word negative phrases that add an even larger sadness boost
STRONG_NEGATIVE_PHRASES = [
    "feel empty",
    "feels pointless",
    "everything is pointless",
    "nothing matters",
    "i feel lost"
]

# Positive words that give a slight boost to joy if there is no negation
POSITIVE_WORDS = [
    "happy",
    "good",
    "great",
    "excited",
    "proud",
    "calm"
]


# Correction function
def correct_emotions(text, emotions):
    # Applies custom rule based corrections to the raw emotion scores
    # Clamps all scores to be between 0.0 and 1.0 at the end
    lowered_text = text.lower()

    # Checks for negation patterns
    for pattern in NEGATION_PATTERNS:
        if pattern in lowered_text:
            emotions["sadness"] += 0.4
            emotions["joy"] *= 0.3   # Significantly reduces joy

    # Checks for strong hopelessness phrases
    for phrase in STRONG_NEGATIVE_PHRASES:
        if phrase in lowered_text:
            emotions["sadness"] += 0.5

    # Checks for single negative words
    for word in NEGATIVE_WORDS:
        if word in lowered_text:
            emotions["sadness"] += 0.35

    # Checks for positive words and only boosts joy if the user didn't use the word "not"
    for word in POSITIVE_WORDS:
        if word in lowered_text and "not " not in lowered_text:
            emotions["joy"] += 0.1

    # Clamps all final values to make sure they stay within the valid range
    for key in emotions:
        emotions[key] = max(0.0, min(1.0, emotions[key]))

    return emotions