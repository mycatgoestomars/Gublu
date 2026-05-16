# Generates a smart warning before chat starts based on patterns and predictions
from pattern_engine import get_all_patterns
from prediction_engine import get_predictions


# Clean text helper
def clean_text(text):
    if not text:
        return None

    # Removes generic phrasing to sound more natural
    replacements = [
        "You often report ",
        "Your difficult moments often happen ",
        "Pattern detected: ",
        "Be careful: "
    ]

    for r in replacements:
        text = text.replace(r, "")

    return text


# Selects the best warning
def build_warning():

    patterns = get_all_patterns()
    predictions = get_predictions()

    daily_patterns = patterns.get("daily_patterns", [])
    break_patterns = patterns.get("streak_break_patterns", [])


   # 1. Predictions for future risk
    # 2. Streak break patterns for danger
    # 3. Daily patterns for general insight
    if predictions:
        chosen = predictions[0]
    elif break_patterns:
        chosen = break_patterns[0]
    elif daily_patterns:
        chosen = daily_patterns[0]
    else:
        return None

    return clean_text(chosen)


# Main function
def get_proactive_message():

    warning = build_warning()

    if not warning:
        return None

    message = (
        "⚠️ Heads up:\n"
        f"{warning}\n"
        "Try to stay aware of this today.\n"
    )

    return message


# Testing
if __name__ == "__main__":

    msg = get_proactive_message()

    if msg:
        print("\n" + msg)
    else:
        print("No warning available.")