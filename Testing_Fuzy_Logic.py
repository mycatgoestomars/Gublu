from fuzzy_logic import fuzzy_emotional_assessment

# Example input to test the fuzzy logic
emotion_scores = {
    "sadness": 0.0004,
    "joy": 0.0002,
    "anger": 0.0003,
    "fear": 0.9985,
    "surprise": 0.0004,
    "neutral": 0.0
}

result = fuzzy_emotional_assessment(emotion_scores)

print("Fuzzy result:")
print(result)