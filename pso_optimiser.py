# PSO Optimiser dataset version
import numpy as np
import pandas as pd
import pyswarms as ps
from predict import predict_emotions


# Label to distress
label_to_distress = {
    "joy": 0.2,
    "surprise": 0.35,
    "anger": 0.55,
    "sadness": 0.8,
    "fear": 0.95
}

label_map = ["sadness", "joy", "anger", "fear", "surprise"]


# Load data
df = pd.read_csv("Dataset Split/train_emotion.csv")


# Build training data
training_data = []

for _, row in df.head(50).iterrows():
    text = row["text"]
    label = row["label"]

    if isinstance(label, int):
        label = label_map[label]

    emotion_scores = predict_emotions(text)
    target = label_to_distress[label]

    training_data.append((emotion_scores, target))


# Fuzzy system parameterised
def triangular(x, a, b, c):
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    if a < x < b:
        return (x - a) / (b - a + 1e-9)
    if b < x < c:
        return (c - x) / (c - b + 1e-9)
    return 0.0


def fuzzy_distress(scores, low, mid, high):

    def fuzzify(v):
        return {
            "low": triangular(v, 0, 0, low),
            "medium": triangular(v, 0, mid, 1),
            "high": triangular(v, high, 1, 1)
        }

    f = {e: fuzzify(v) for e, v in scores.items()}

    fear = f["fear"]
    sadness = f["sadness"]
    anger = f["anger"]
    joy = f["joy"]

    d = {
        "low": joy["high"],
        "medium": max(anger["high"], min(fear["medium"], sadness["medium"])),
        "high": max(fear["high"], sadness["high"])
    }

    mapping = {"low": 0.2, "medium": 0.5, "high": 0.9}

    num = sum(d[k] * mapping[k] for k in mapping)
    den = sum(d[k] for k in mapping)

    return 0 if den == 0 else num / den


# Fitness function
def fitness(particles):
    errors = []

    for p in particles:
        low, mid, high = p

        if not (0.1 < low < mid < high < 0.95):
            errors.append(1000)
            continue

        mse = []

        for scores, target in training_data:
            pred = fuzzy_distress(scores, low, mid, high)
            mse.append((pred - target) ** 2)

        errors.append(np.mean(mse))

    return np.array(errors)


# PSO Testing 
if __name__ == "__main__":

    options = {"c1": 1.5, "c2": 1.5, "w": 0.7}

    bounds = (
        np.array([0.2, 0.3, 0.5]),
        np.array([0.5, 0.7, 0.9])
    )

    optimizer = ps.single.GlobalBestPSO(
        n_particles=30,
        dimensions=3,
        options=options,
        bounds=bounds
    )

    best_cost, best_pos = optimizer.optimize(fitness, iters=100)

    print("\nBest Cost:", best_cost)
    print("LOW_END =", best_pos[0])
    print("MEDIUM_PEAK =", best_pos[1])
    print("HIGH_START =", best_pos[2])