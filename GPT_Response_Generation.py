# Handles generating chatbot responses
# Tries to use the OpenAI GPT API first, falls back to a local rule-based response if unavailable

import os
import random

from prediction_engine import get_predictions
from pattern_engine import get_all_patterns
from decision_engine import build_decision_message
from insight_selector import select_best_insight
from chat_memory import get_history_text
from memory_manager import get_journal_emotion_summary


# Sets up OpenAI integration

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception as import_error:
    OPENAI_AVAILABLE = False
    print("OpenAI import failed:", import_error)


api_key = os.getenv("OPENAI_API_KEY")
USE_GPT = OPENAI_AVAILABLE and bool(api_key)

# Debug output to confirm GPT setup without printing the actual API key.
print("OPENAI_AVAILABLE:", OPENAI_AVAILABLE)
print("API KEY FOUND:", bool(api_key))
print("USE_GPT:", USE_GPT)

if USE_GPT:
    gpt_client = OpenAI(api_key=api_key)
else:
    gpt_client = None


# Set this to False if you don't want replies to show [GPT] on the frontend.
SHOW_GPT_MARKER = False


# Filters out robotic phrases

_BLOCKED_PHRASES = [
    "not enough daily check-in data",
    "not enough streak",
    "not enough data",
    "no strong",
    "no strong decision insight",
    "no strong negative behaviour",
    "no strong streak break risk",
    "not enough streak break history",
    "not enough streak history",
    "not enough journal data",
]


def filter_insight(text):
    # Removes internal 'no data' style messages before they reach the user
    if not text:
        return None

    lowered_text = text.lower()

    for blocked_phrase in _BLOCKED_PHRASES:
        if blocked_phrase in lowered_text:
            return None

    return text


def clean_insights(items):
    # Filters a list of insight strings and keeps only the useful ones
    if not items:
        return []

    return [item for item in items if filter_insight(item)]


# Formats check in context

def format_checkin_context(checkin):
    # Turns the latest check in dictionary into a natural sentence so GPT can understand it
    if not checkin or not isinstance(checkin, dict):
        return ""

    context_parts = []

    mood = checkin.get("mood")
    energy = checkin.get("energy")
    triggers = checkin.get("triggers", [])
    environment = checkin.get("environment")
    behaviour = checkin.get("behaviour")
    time_of_day = checkin.get("time_of_day")

    if mood:
        context_parts.append(f"feeling {mood}")

    if energy:
        context_parts.append(f"{energy} energy")

    if triggers and triggers != ["nothing"]:
        context_parts.append(f"triggered by {', '.join(triggers)}")

    if environment:
        context_parts.append(f"environment: {environment}")

    if behaviour:
        context_parts.append(f"behaviour: {behaviour}")

    if time_of_day:
        context_parts.append(f"time: {time_of_day}")

    if not context_parts:
        return ""

    return "Today you checked in as: " + ", ".join(context_parts) + "."


# Creates journal trend context

def format_journal_trend_context():
    # Creates a short journal trend note for GPT
    summary = get_journal_emotion_summary()

    if not summary.get("available"):
        return ""

    trend = summary.get("trend", "stable")
    emotion = summary.get("dominant_emotion", "")
    distress = summary.get("average_distress", 0.0)

    if trend == "increasing" and distress > 0.5:
        return (
            f"The user's recent journal entries suggest rising emotional "
            f"distress, with {emotion} as the dominant tone. "
            f"Use this gently only if relevant."
        )

    if trend == "decreasing":
        return (
            f"The user's recent journal entries suggest improving emotional "
            f"tone, with {emotion} as the dominant emotion."
        )

    if emotion in ("sadness", "fear") and distress > 0.45:
        return (
            f"The user's recent journal entries suggest some emotional "
            f"heaviness, with {emotion} as the dominant tone."
        )

    return ""


# Makes rule-based insights sound more natural

def humanize(text):
    # Makes the rule-based insight text sound a bit more natural and less robotic
    if not text:
        return ""

    replacements = {
        "The strongest pattern I noticed is:": "I've noticed that",
        "The most important prediction is:": "It might help to keep in mind that",
        "One useful pattern is:": "Something that seems to come up for you is",
        "The most important streak-break pattern is:": "Something worth being aware of is that",
        "When": "It seems like when",
        "is often linked to": "can lead to",
    }

    for original, replacement in replacements.items():
        text = text.replace(original, replacement)

    return text.strip()


# Chooses a distress-aware base opener

def get_base(label):
    # Chooses a short, empathetic opening sentence based on the user's distress level
    if label == "high distress":
        return random.choice([
            "That sounds really heavy.",
            "I'm really sorry you're dealing with that.",
            "That seems like a lot to handle.",
        ])

    if label == "moderate distress":
        return random.choice([
            "That sounds a bit difficult.",
            "Seems like something's weighing on you.",
            "That doesn't sound easy.",
        ])

    return random.choice([
        "Sounds like things are okay right now.",
        "Glad things seem steady.",
        "That's good to hear.",
    ])


# Generates a fallback response

def fallback_response(label, user_text, patterns, predictions, checkin_context=None):
    # Generates a basic response without using GPT
    opening = get_base(label)

    conversation_history = get_history_text()
    checkin_sentence = format_checkin_context(checkin_context)

    clean_patterns = clean_insights(patterns)
    clean_predictions = clean_insights(predictions)

    best_insight = select_best_insight(user_text, clean_patterns, clean_predictions)
    best_insight = filter_insight(best_insight)
    best_insight = humanize(best_insight) if best_insight else None

    decision_message = filter_insight(build_decision_message())
    decision_message = humanize(decision_message) if decision_message else None

    if conversation_history:
        opening += " From what you've been saying, it seems connected."

    if checkin_sentence:
        opening += " " + checkin_sentence

    journal_note = ""
    journal_summary = get_journal_emotion_summary()

    if journal_summary.get("available") and journal_summary.get("trend") == "increasing":
        journal_note = (
            " You've seemed under a bit more pressure lately, "
            "so it may help to keep today’s goal small."
        )

    if decision_message:
        return f"{opening}{journal_note} {decision_message} Maybe take things one step at a time."

    if best_insight:
        return f"{opening}{journal_note} {best_insight} Try not to be too hard on yourself."

    return (
        f"{opening} As you keep tracking your habits, I'll be able to give "
        f"more personalised advice over time."
    )


# Generates a GPT response
def generate_gpt(user_text, emotions, distress, label, patterns, predictions, checkin_context=None):
    # Generates a response using the GPT API
    if not gpt_client:
        print("GPT skipped: gpt_client is None")
        return None

    clean_patterns = clean_insights(patterns)
    clean_predictions = clean_insights(predictions)

    decision_message = filter_insight(build_decision_message()) or ""
    decision_message = humanize(decision_message)

    conversation_history = get_history_text()
    checkin_sentence = format_checkin_context(checkin_context)
    journal_trend_note = format_journal_trend_context()

    system_prompt = """
You are Gublu, a calm and supportive companion inside a habit-tracking and journaling app.

Your scope is strictly limited to:
- wellbeing
- habits
- journaling
- daily check-ins
- emotions
- triggers
- streaks
- personal reflection

If the user asks about unrelated topics such as maths, coding, news, trivia, homework, general knowledge, or anything outside the app's purpose, politely redirect them back to habits, mood, journaling, or their day.

Do not answer unrelated factual questions.
Do not give long explanations.
Do not make medical diagnoses.
Do not claim to be a therapist or doctor.
Do not give clinical advice.

Style rules:
- Reply in 2–3 short sentences only.
- Be warm, natural, and conversational.
- Sound like a thoughtful, non-judgemental friend.
- Give one small, realistic suggestion if useful.
- Focus on the user's current message first.
- Only mention streaks, habit patterns, journal trends, or repeated triggers when they are clearly relevant to the user's current message.
- Do not mention patterns, streaks, or journal trends in every response.
- If a pattern was mentioned recently, avoid repeating it unless the user asks about it or it is very important.
- Use pattern insights to gently help the user understand what may be affecting their mood or behaviour, not to lecture them.
- Vary your wording so responses do not feel repetitive.
- If habit data is limited, do not say "not enough data"; gently say that more tracking will help you personalise advice over time.
"""

    user_prompt = f"""
Recent conversation:
{conversation_history if conversation_history else "No prior conversation this session."}

Today's check-in context:
{checkin_sentence if checkin_sentence else "No check-in data available today."}

Recent journal trend:
{journal_trend_note if journal_trend_note else "No strong journal trend available."}

User message:
{user_text}

Detected emotions:
{emotions}

Distress signal:
{round(distress, 3)} ({label})

Relevant habit insight:
{decision_message if decision_message else "No strong habit insight available yet."}

Clean pattern list:
{clean_patterns}

Clean prediction list:
{clean_predictions}

Now respond to the user in 2–3 short sentences.
"""

    try:
        print("Trying GPT request...")

        response = gpt_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_tokens=160,
            timeout=15,  # 15-second hard timeout — prevents blocking other requests
        )

        print("GPT SUCCESS")

        gpt_text = response.choices[0].message.content.strip()

        if SHOW_GPT_MARKER:
            return "[GPT] " + gpt_text

        return gpt_text

    except Exception as error:
        print("GPT ERROR:", error)
        return None


# Main response function
def generate_response(user_text, emotions, distress, label, checkin_context=None):
    # Gets the chatbots reply
    pattern_data = get_all_patterns()
    recent_patterns = pattern_data.get("daily_patterns", [])
    recent_predictions = get_predictions()

    if USE_GPT:
        gpt_reply = generate_gpt(
            user_text=user_text,
            emotions=emotions,
            distress=distress,
            label=label,
            patterns=recent_patterns,
            predictions=recent_predictions,
            checkin_context=checkin_context,
        )

        if gpt_reply:
            return gpt_reply

    print("Using fallback response")
    return fallback_response(
        label=label,
        user_text=user_text,
        patterns=recent_patterns,
        predictions=recent_predictions,
        checkin_context=checkin_context,
    )