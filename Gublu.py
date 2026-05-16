# Central file that ties all of Gublu systems together
# Predicts emotion scores, fixes errors, checks for high risk language, calculates distress, and generates chatbot response

from predict import predict_emotions
from GPT_Response_Generation import generate_response
from risk_model import ml_risk_check
from emotion_correction import correct_emotions
from setup_system import run_initial_setup
from daily_checkin import run_daily_checkin
from streak_system import update_streak
from pattern_engine import get_all_patterns
from prediction_engine import get_predictions
from proactive_engine import get_proactive_message
from reasoning_engine import get_multi_signal_insights
from decision_engine import build_decision_message
from chat_memory import add_message, clear_history


# Risk detection
def detect_risk(text):
    # Checks whether a user's message contains dangerous language
    lowered = text.lower()

    # Phrases that are unambiguously high-risk and flagged immediately
    direct_risk_phrases = [
        "kill myself",
        "end my life",
        "suicide",
        "i want to die",
        "dont want to live",
        "don't want to live",
        "tired of living"
    ]

    for phrase in direct_risk_phrases:
        if phrase in lowered:
            return "high"

    # Phrases that may indicate passive or indirect risk and are passed to the ML model
    passive_risk_phrases = [
        "harm myself",
        "hurt myself",
        "hit myself",
        "run over",
        "get run over",
        "crash into",
        "disappear",
        "not exist"
    ]

    if any(phrase in lowered for phrase in passive_risk_phrases):
        return ml_risk_check(lowered)

    return "low"


# Fuzzy logic helpers
# Thresholds define the fuzzy logic boundaries for mapping distress signals
LOW_END = 0.4
MEDIUM_PEAK = 0.6
HIGH_START = 0.8


def triangular(x, a, b, c):
    # Calculates the value for the triangular fuzzy set
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    if a < x < b:
        return (x - a) / (b - a + 1e-9)
    if b < x < c:
        return (c - x) / (c - b + 1e-9)
    return 0.0


def fuzzify(value):
    # Converts a single emotion score into fuzzy values across three distress levels
    return {
        "low":    triangular(value, 0.0, 0.0,        LOW_END),
        "medium": triangular(value, 0.0, MEDIUM_PEAK, 1.0),
        "high":   triangular(value, HIGH_START, 1.0,  1.0)
    }


# Fuzzy distress scoring
def fuzzy_system(emotions):
    # Converts all the emotion scores into one final distress score and a text label
    # Fast-tracks extreme sadness or fear
    if emotions["sadness"] > 0.85:
        return 0.9, "high distress"

    if emotions["fear"] > 0.9:
        return 0.85, "high distress"

    # Fuzzifies the four emotion inputs
    sadness_fuzzy = fuzzify(emotions["sadness"])
    fear_fuzzy    = fuzzify(emotions["fear"])
    anger_fuzzy   = fuzzify(emotions["anger"])
    joy_fuzzy     = fuzzify(emotions["joy"])

    # Output membership for each distress level
    distress_low    = joy_fuzzy["high"]   # High joy means low distress
    distress_medium = max(anger_fuzzy["medium"], fear_fuzzy["medium"], sadness_fuzzy["medium"])
    distress_high   = max(sadness_fuzzy["high"], fear_fuzzy["high"] * 0.6)

    # Defuzzifies using the weighted centroid method
    numerator   = distress_low * 0.2 + distress_medium * 0.5 + distress_high * 0.9
    denominator = distress_low + distress_medium + distress_high

    score = 0.0 if denominator == 0 else numerator / denominator

    label = (
        "low distress"      if score < 0.45 else
        "moderate distress" if score < 0.8  else
        "high distress"
    )

    return score, label


# Main chat process
def process(text, checkin_context=None):
    # Main part that handles a user's message and generates the reply
    # Raw emotion prediction
    emotions = predict_emotions(text)

    # Applies correction to fix negation and boost sadness for negative phrases
    emotions = correct_emotions(text, emotions)

    # Risk check which overrides the distress score if dangerous
    risk_level = detect_risk(text)

    # Calculates the fuzzy distress score
    distress, label = fuzzy_system(emotions)

    # Overrides the score and forces a safety response if high risk
    if risk_level == "high":
        distress = 1.0
        label = "high distress"

        chat_reply = (
            "I'm really sorry you're feeling this way. "
            "You don't have to go through this alone. "
            "Please reach out to someone you trust or a professional."
        )
    else:
        # Generates a contextual chatbot response
        chat_reply = generate_response(text, emotions, distress, label, checkin_context=checkin_context)

    return emotions, distress, label, chat_reply


# Display helpers for CLI only
def show_proactive_warning():
    # Prints a proactive warning based on current patterns and predictions
    warning = get_proactive_message()
    if warning:
        print(warning)
        print("-" * 50)


def show_patterns():
    # Prints the detected daily and streak break patterns
    patterns = get_all_patterns()

    print("\n Insights:")
    for item in patterns.get("daily_patterns", []):
        print("-", item)

    for item in patterns.get("streak_break_patterns", []):
        print("-", item)

    print("\n" + "=" * 50 + "\n")


def show_predictions():
    # Prints the current forward looking predictions
    predictions = get_predictions()

    print("Predictions:")
    for item in predictions:
        print("-", item)

    print("\n" + "=" * 50 + "\n")


def show_reasoning():
    # Prints multi signal reasoning insights
    reasoning = get_multi_signal_insights()

    print("Multi Signal Reasoning:")
    for item in reasoning:
        print("-", item)

    print("\n" + "=" * 50 + "\n")


def show_decision():
    # Prints the smart decision engine's top insight
    print("Smart Decision:")
    print("-", build_decision_message())
    print("\n" + "=" * 50 + "\n")


# Main app in CLI mode
if __name__ == "__main__":

    print("Gublu Chatbot — Final System Version")
    print("Type 'exit' to quit")
    print("Type 'reset' to clear conversation memory\n")

    # Runs first-time setup
    run_initial_setup()

    # Daily check in
    entry = run_daily_checkin(broken=False)

    # Updates and displays streak
    streak = update_streak(entry)
    print(f"\n Current Streak: {streak['current_days']} days\n")

    # Shows proactive warning
    show_proactive_warning()

    # Shows detected patterns
    show_patterns()

    # Shows predictions
    show_predictions()

    # Shows multi-signal reasoning
    show_reasoning()

    # Shows the smart decision insight
    show_decision()

    # Chat loop
    while True:
        user_input = input("You: ")

        if user_input.lower() == "exit":
            break

        if user_input.lower() == "reset":
            clear_history()
            print("Conversation memory cleared.")
            continue

        emotions, distress, label, reply = process(user_input)

        # Saves the message pair to the conversation memory
        add_message(user_input, reply)

        print("\nEmotion Scores:", emotions)
        print("Distress:", round(distress, 3), "-", label)
        print("\nGublu:", reply)
        print("-" * 60)