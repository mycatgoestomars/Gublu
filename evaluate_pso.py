# Evaluates the PSO fuzzy logic performance
# Compares performance before and after PSO using MSE and MAE and displays a graph

from predict import predict_emotions
import numpy as np
import matplotlib.pyplot as plt


# Test dataset
dataset = [
    ("I feel calm and relaxed", 0.2),
    ("I am a bit stressed today", 0.55),
    ("I feel very anxious and overwhelmed", 0.85),
    ("Everything is falling apart, I can't cope", 0.95),
    ("I feel slightly worried", 0.6),
    ("I am panicking and can't breathe", 0.8),
    ("I feel okay overall", 0.25),
]


# Parameterised fuzzy system
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


def fuzzify(value, low_end, medium_peak, high_start):
    return {
        "low": triangular(value, 0.0, 0.0, low_end),
        "medium": triangular(value, 0.0, medium_peak, 1.0),
        "high": triangular(value, high_start, 1.0, 1.0)
    }


def compute_distress(emotions, params):
    low_end, medium_peak, high_start = params
    sadness = fuzzify(emotions["sadness"], low_end, medium_peak, high_start)
    fear = fuzzify(emotions["fear"], low_end, medium_peak, high_start)
    anger = fuzzify(emotions["anger"], low_end, medium_peak, high_start)
    joy = fuzzify(emotions["joy"], low_end, medium_peak, high_start)

    # Fuzzy rules
    low = joy["high"]
    medium = max(anger["high"], min(fear["medium"], sadness["medium"]))
    high = max(fear["high"], sadness["high"])

    # Defuzzification
    numerator = low * 0.2 + medium * 0.5 + high * 0.9
    denominator = low + medium + high
    return 0.0 if denominator == 0 else numerator / denominator


# Evaluation function
def evaluate(params):
    errors = []
    for text, target in dataset:
        emotions = predict_emotions(text)
        pred = compute_distress(emotions, params)
        errors.append((pred - target) ** 2)
    mse = np.mean(errors)
    mae = np.mean([abs(np.sqrt(e)) for e in errors])

    return mae, mse


# Main execution
if __name__ == "__main__":

    print("Running PSO Evaluation...\n")

    # Before PSO default values
    default_params = (0.32, 0.52, 0.72)

    # After PSO optimised values
    pso_params = (0.352, 0.491, 0.900)

    # Evaluates both
    d_mae, d_mse = evaluate(default_params)
    p_mae, p_mse = evaluate(pso_params)

    # Prints results
    print("===== RESULTS =====\n")
    print("Before PSO:")
    print("MSE:", round(d_mse, 6))
    print("MAE:", round(d_mae, 6))
    print()
    print("After PSO:")
    print("MSE:", round(p_mse, 6))
    print("MAE:", round(p_mae, 6))
    print()

    # Comparison
    print("===== COMPARISON =====\n")
    if p_mse < d_mse:
        print("PSO improved performance")
    else:
        print("PSO did not improve performance")

    # Graph for report
    labels = ["Before PSO", "After PSO"]
    mse_values = [d_mse, p_mse]
    plt.figure()
    plt.bar(labels, mse_values)
    plt.xlabel("System")
    plt.ylabel("Mean Squared Error (MSE)")
    plt.title("PSO Performance Comparison")
    plt.show()