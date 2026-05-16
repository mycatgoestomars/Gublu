# Handles loading and saving all user data to a single JSON file
# Auto-repairs the file if any keys are missing so the app never crashes

import json
import os
from datetime import datetime, timedelta


# The file where all user data is stored
MEMORY_FILE = "gublu_memory.json"


# Default memory structure
def default_memory():
    # Returns the empty memory structure for a brand new user
    return {
        "username": None,
        "my_why": None,
        "chosen_problem": None,
        "survey_answers": {},
        "daily_checkins": [],
        "patterns": [],
        "streak": {
            "current_days": 0,
            "start_date": None,
            "last_check_in": None,
            "status": "inactive"
        },
        "streak_breaks": [],
        "high_distress_messages": [],
        "chat_log": []
    }


# Load memory with auto repair
def load_memory():
    # Loads the user's saved memory from the JSON file
    # Fills in missing keys automatically so the app won't crash
    # Resets back to defaults if the file is broken
    saved_memory = default_memory()

    # Creates it with default empty values if the file doesn't exist yet
    if not os.path.exists(MEMORY_FILE):
        save_memory(saved_memory)
        return saved_memory

    try:
        with open(MEMORY_FILE, "r") as f:
            stored_data = json.load(f)

        # Merges stored data into default structure to catch new keys
        for key in saved_memory:
            if key in stored_data:
                saved_memory[key] = stored_data[key]

        # Makes sure the streak field is a dictionary
        if not isinstance(saved_memory["streak"], dict):
            saved_memory["streak"] = default_memory()["streak"]

        # Fills in any streak sub keys that might be missing
        for key in default_memory()["streak"]:
            if key not in saved_memory["streak"]:
                saved_memory["streak"][key] = default_memory()["streak"][key]

        # Makes sure optional lists always exist so loops don't break
        if "streak_breaks" not in saved_memory:
            saved_memory["streak_breaks"] = []

        if "high_distress_messages" not in saved_memory:
            saved_memory["high_distress_messages"] = []

        # Makes sure the chat log exists for the sentiment history
        if "chat_log" not in saved_memory:
            saved_memory["chat_log"] = []

        if "username" not in saved_memory:
            saved_memory["username"] = None

        if "my_why" not in saved_memory:
            saved_memory["my_why"] = None

        save_memory(saved_memory)
        return saved_memory

    except Exception:
        # Returns a clean default if loading fails for any reason
        save_memory(saved_memory)
        return saved_memory


# Save memory

def save_memory(memory):
    # Saves the current memory dictionary into the JSON file
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


# Journal summary generator

def generate_journal_summary(user_message, emotions, distress_score, distress_label):
    # Creates a short, simple emotional summary of a chat message using fixed rules
    if not emotions:
        return "Journal entry recorded."

    # Finds the strongest emotion
    dominant_emotion = max(emotions, key=lambda k: emotions[k])
    dominant_score = round(emotions[dominant_emotion], 2)

    # Builds a natural, simple summary sentence that is consistent
    distress_word = distress_label.replace(" distress", "").capitalize()

    return f"{distress_word} distress entry. Dominant emotion: {dominant_emotion} ({dominant_score})."


# Save journal entry

def save_journal_entry(user_message, bot_reply, emotions, distress_score,
                       distress_label, risk_level="low", checkin_context=None,
                       summary=None):
    # Saves a single analysed chat message to the permanent chat log
    # Auto-generates a summary using generate_journal_summary() if not provided
    memory = load_memory()

    # Auto generates a summary if one was not passed in
    if summary is None:
        summary = generate_journal_summary(
            user_message, emotions, distress_score, distress_label
        )

    journal_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_message": user_message,
        "bot_reply": bot_reply,
        "summary": summary,
        "emotions": emotions,
        "distress_score": round(distress_score, 4),
        "distress_label": distress_label,
        "risk_level": risk_level,
        "checkin_context": checkin_context
    }

    memory["chat_log"].append(journal_entry)
    save_memory(memory)


# Get recent journal entries

def get_recent_journal_entries(n=10):
    # Returns the N most recent chat or journal entries from the log
    memory = load_memory()
    chat_log = memory.get("chat_log", [])
    return chat_log[-n:] if chat_log else []


# Daily journal summary

def get_daily_journal_summary():
    # Groups all journal entries by date and calculates daily averages
    memory = load_memory()
    chat_log = memory.get("chat_log", [])

    if not chat_log:
        return []

    # Groups entries by date
    entries_by_date = {}
    for journal_entry in chat_log:
        # Grabs just the date part of the timestamp
        entry_date = journal_entry.get("timestamp", "")[:10]
        if not entry_date:
            continue
        if entry_date not in entries_by_date:
            entries_by_date[entry_date] = []
        entries_by_date[entry_date].append(journal_entry)

    # Calculates the daily averages for each date
    daily_summaries = []
    for date_str in sorted(entries_by_date.keys()):
        day_entries = entries_by_date[date_str]
        entry_count = len(day_entries)

        # Averages the distress across all entries for this day
        distress_values = [e.get("distress_score", 0.0) for e in day_entries]
        average_distress = round(sum(distress_values) / max(entry_count, 1), 4)

        # Averages each emotion across all entries for this day
        emotion_keys = ["sadness", "fear", "anger", "joy"]
        emotion_averages = {}
        for emotion_key in emotion_keys:
            scores = [e.get("emotions", {}).get(emotion_key, 0.0) for e in day_entries]
            emotion_averages[f"avg_{emotion_key}"] = round(
                sum(scores) / max(len(scores), 1), 4
            )

        # The dominant emotion is whichever average is highest
        dominant_emotion = max(
            emotion_keys,
            key=lambda k: emotion_averages.get(f"avg_{k}", 0)
        )

        daily_summaries.append({
            "date": date_str,
            "entry_count": entry_count,
            "average_distress": average_distress,
            "dominant_emotion": dominant_emotion,
            **emotion_averages
        })

    return daily_summaries


# Weekly journal summary

def get_weekly_journal_summary(target_date=None):
    # Calculates weekly aggregated journal sentiment features for a specific date
    # Groups journal entries by week and returns sentiment averages for the 7 day window
    memory = load_memory()
    chat_log = memory.get("chat_log", [])

    if not chat_log:
        return None

    # Defaults to today if no specific date is asked for
    if target_date is None:
        end_date = datetime.now().date()
    else:
        try:
            end_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            end_date = datetime.now().date()

    # The week window is the 7 days ending on the target date
    start_date = end_date - timedelta(days=7)

    # Finds all the journal entries that fall within this week
    for journal_entry in chat_log:
        entry_date_str = journal_entry.get("timestamp", "")[:10]
        if not entry_date_str:
            continue
        try:
            entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if start_date < entry_date <= end_date:
            week_entries.append(journal_entry)

    journal_entry_count_week = len(week_entries)

    # Returns zeros if they didn't journal this week so the ML model doesn't crash
    if journal_entry_count_week == 0:
        return {
            "weekly_journal_distress_avg": 0.0,
            "weekly_sadness_avg": 0.0,
            "weekly_fear_avg": 0.0,
            "weekly_anger_avg": 0.0,
            "weekly_distress_trend": 0.0,
            "journal_entry_count_week": 0
        }

    # Calculates weekly averages for distress and each individual emotion
    distress_values = [e.get("distress_score", 0.0) for e in week_entries]
    weekly_journal_distress_avg = round(
        sum(distress_values) / journal_entry_count_week, 4
    )

    weekly_sadness_avg = round(
        sum(e.get("emotions", {}).get("sadness", 0.0) for e in week_entries)
        / journal_entry_count_week, 4
    )
    weekly_fear_avg = round(
        sum(e.get("emotions", {}).get("fear", 0.0) for e in week_entries)
        / journal_entry_count_week, 4
    )
    weekly_anger_avg = round(
        sum(e.get("emotions", {}).get("anger", 0.0) for e in week_entries)
        / journal_entry_count_week, 4
    )

    # Calculates the distress trend across the week
    # Compares the average distress in the first half of the week against the second half
    half = journal_entry_count_week // 2
    if half > 0:
        first_half_distress = sum(distress_values[:half]) / half
        second_half_distress = sum(distress_values[half:]) / max(
            journal_entry_count_week - half, 1
        )
        weekly_distress_trend = round(second_half_distress - first_half_distress, 4)
    else:
        weekly_distress_trend = 0.0

    return {
        "weekly_journal_distress_avg": weekly_journal_distress_avg,
        "weekly_sadness_avg": weekly_sadness_avg,
        "weekly_fear_avg": weekly_fear_avg,
        "weekly_anger_avg": weekly_anger_avg,
        "weekly_distress_trend": weekly_distress_trend,
        "journal_entry_count_week": journal_entry_count_week
    }


# Journal emotion summary
def get_journal_emotion_summary():
    # Calculates simple emotional trends from the recent journal entries
    recent_entries = get_recent_journal_entries(10)

    # Needs at least 3 entries to say anything meaningful
    if len(recent_entries) < 3:
        return {
            "available": False,
            "message": "As you keep journaling, I'll be able to show emotional trends over time.",
            "entry_count": len(recent_entries)
        }

    # Calculates the average distress across these entries
    distress_scores = [e.get("distress_score", 0.0) for e in recent_entries]
    average_distress = round(sum(distress_scores) / len(distress_scores), 3)

    # Finds the most common strongest emotion across the entries
    emotion_counts = {}
    for journal_entry in recent_entries:
        emotions = journal_entry.get("emotions", {})
        if emotions:
            # The dominant emotion is whichever one scored the highest in this specific message
            peak_emotion = max(emotions, key=lambda k: emotions[k])
            emotion_counts[peak_emotion] = emotion_counts.get(peak_emotion, 0) + 1

    dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"

    # Detects the trend by comparing the first half of the recent entries with the second half
    half = len(distress_scores) // 2
    first_half_avg = sum(distress_scores[:half]) / max(half, 1)
    second_half_avg = sum(distress_scores[half:]) / max(len(distress_scores) - half, 1)

    if second_half_avg > first_half_avg + 0.08:
        trend = "increasing"
    elif second_half_avg < first_half_avg - 0.08:
        trend = "decreasing"
    else:
        trend = "stable"

    # Includes the weekly summary data if we have it
    weekly_summary = get_weekly_journal_summary()

    # Builds a natural, simple message to show on the dashboard card
    if trend == "increasing" and average_distress > 0.55:
        message = "Your journal tone has been heavier recently. It's okay to take things slowly."
    elif trend == "decreasing":
        message = "Your journal entries suggest things are feeling a bit lighter lately. Keep going."
    elif dominant_emotion in ("sadness", "fear") and average_distress > 0.5:
        message = "Recent entries suggest you've had some difficult moments. Be kind to yourself."
    elif dominant_emotion == "joy" or average_distress < 0.35:
        message = "Your recent journal entries have a positive emotional tone. Well done."
    else:
        message = "Your emotional tone has been fairly balanced across recent journal entries."

    summary_response = {
        "available": True,
        "average_distress": average_distress,
        "dominant_emotion": dominant_emotion,
        "trend": trend,
        "message": message,
        "entry_count": len(recent_entries)
    }

    # Merges the weekly ML features into the response if they exist
    if weekly_summary:
        summary_response.update(weekly_summary)

    return summary_response


# Get latest check in
def get_latest_checkin():
    # Returns today's check in entry from memory
    memory = load_memory()
    checkins = memory.get("daily_checkins", [])
    today = datetime.now().date().isoformat()

    for checkin_entry in reversed(checkins):
        if checkin_entry.get("date") == today:
            return checkin_entry

    return None