from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os

# Loading our environment keys from the .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass 

# Importing main chatbot decisions maker
from Gublu import process

# Importing memory and saving functions
from chat_memory import add_message, clear_history
from memory_manager import (
    save_journal_entry, get_journal_emotion_summary, get_latest_checkin,
    get_weekly_journal_summary, generate_journal_summary
)

# Checking if GPT is turned on 
from GPT_Response_Generation import USE_GPT
print(f"GPT enabled: {USE_GPT}")

app = Flask(__name__)
CORS(app)  # allow frontend access

# This checks if a user profile already exists, so it can take the next actions accordingly
@app.route("/user", methods=["GET"])
def get_user():
    from memory_manager import load_memory

    memory = load_memory()
    username = memory.get("username")

    # If no username is stored, the user has not completed onboarding
    if not username:
        return jsonify({"exists": False})

    return jsonify({
        "exists": True,
        "username": username,
        "chosen_problem": memory.get("chosen_problem"),
        "my_why": memory.get("my_why")
    })


# Saves user's name, problem, and "My Why" to the memory file
@app.route("/user/setup", methods=["POST"])
def setup_user():
    from memory_manager import load_memory, save_memory

    data = request.json or {}
    memory = load_memory()

    memory["username"] = data.get("username", "User")
    memory["chosen_problem"] = data.get("problem", "procrastination")
    memory["my_why"] = data.get("my_why", "")

    save_memory(memory)

    return jsonify({"message": "User created", "username": memory["username"]})


# This lets the user change their "My Why" statement directly from the dashboard
@app.route("/user/my-why", methods=["PUT"])
def update_my_why():
    from memory_manager import load_memory, save_memory

    data = request.json or {}
    memory = load_memory()

    memory["my_why"] = data.get("my_why", memory.get("my_why", ""))
    save_memory(memory)

    return jsonify({"message": "My Why updated", "my_why": memory["my_why"]})


# Checks if the user has already done their daily check in today
@app.route("/checkin/status", methods=["GET"])
def checkin_status():
    from memory_manager import load_memory

    memory = load_memory()
    checkins = memory.get("daily_checkins", [])
    today = datetime.now().date().isoformat()

    # Check if any saved entry has today's date
    checked_in = any(c.get("date") == today for c in checkins)

    return jsonify({"checked_in_today": checked_in, "date": today})


# Makes sure if OpenAI GPT integration is turned on
@app.route("/gpt-status", methods=["GET"])
def gpt_status():
    return jsonify({
        "gpt_enabled": USE_GPT,
        "message": "GPT is active and will be used for chat responses." if USE_GPT
                   else "GPT is not configured. Using the rule-based fallback instead."
    })


# Generates a fixed opening message for the chat screen based on today's check in data
@app.route("/chat/starter", methods=["GET"])
def chat_starter():
    today_checkin = get_latest_checkin()

    if today_checkin:
        mood    = today_checkin.get("mood", "")
        energy  = today_checkin.get("energy", "")
        triggers = [t for t in today_checkin.get("triggers", []) if t != "nothing"]

        # Building a personalised opening sentence using what they said in the check in
        parts = []
        if mood:
            parts.append(f"feeling {mood}")
        if energy:
            parts.append(f"{energy} energy")

        trigger_text = ""
        if triggers:
            trigger_text = f" with {' and '.join(triggers)} as a factor"

        if parts:
            summary = " and ".join(parts)
            starter = (
                f"You checked in as {summary} today{trigger_text}. "
                f"If you'd like, you can tell me more about how your day went — "
                f"what helped, what made it harder, or anything on your mind."
            )
        else:
            starter = (
                "You've already checked in today. "
                "Feel free to tell me how the rest of your day went, "
                "or anything that's been on your mind."
            )
    else:
        starter = (
            "You can tell me more about your day, what affected you, "
            "or anything connected to your check-in. "
            "I'm here to help you reflect without judgement."
        )

    return jsonify({"starter": starter})


# Gets the emotional trend data from past chat/journal entries, also used to display emotional tone in the dashboard
@app.route("/journal-summary", methods=["GET"])
def journal_summary():
    try:
        emotion_summary = get_journal_emotion_summary()
        return jsonify(emotion_summary)
    except Exception:
        return jsonify({
            "available": False,
            "message": "As you keep journalling, I'll be able to show emotional trends over time."
        })


# Connects the front and back end of the chat aspect. Also makes sure it replies according to the emotion detected and other context.
# Saves the detected emotion scores, risk level, and a short emotion summary of the message to memory
@app.route("/chat", methods=["POST"])
def chat():
    from memory_manager import load_memory, save_memory
    from Gublu import detect_risk
    data = request.json or {}
    user_message = data.get("message", "")

    # Loads and gives context to the chatbot using the most recent check in information
    memory = load_memory()
    checkins = memory.get("daily_checkins", [])
    today = datetime.now().date().isoformat()
    today_checkin = None
    for entry in reversed(checkins):
        if entry.get("date") == today:
            today_checkin = entry
            break

    # Checking the risk level before processing everything else
    risk_level = detect_risk(user_message)

    # Run the message through processing pipeline
    emotions, distress, label, reply = process(user_message, checkin_context=today_checkin)

    # Storing the conversation  in the chat memory 
    add_message(user_message, reply, emotions=emotions, distress=distress,
                label=label, risk_level=risk_level)

    # Saving the full record to the journal
    save_journal_entry(
        user_message=user_message,
        bot_reply=reply,
        emotions=emotions,
        distress_score=distress,
        distress_label=label,
        risk_level=risk_level,
        checkin_context=today_checkin
    )

    # high distress messages separately for the streaks page
    if label == "high distress":
        memory = load_memory()
        memory["high_distress_messages"].append({
            "date": datetime.now().isoformat(),
            "user_message": user_message,
            "bot_reply": reply,
            "distress_score": distress,
            "emotions": emotions
        })
        save_memory(memory)

    return jsonify({
        "reply": reply,
        "distress": distress,
        "label": label
    })


# This receives the daily check in data from the frontend
@app.route("/checkin", methods=["POST"])
def checkin():
    from streak_system import update_streak
    from memory_manager import load_memory, save_memory

    data = request.json or {}
    memory = load_memory()

    # Getting the problem they chose during the onboarding setup
    problem = memory.get("chosen_problem", "procrastination")

    entry = {
        "date": data.get("date"),
        "problem": problem,
        "mood": data.get("mood"),
        "energy": data.get("energy"),
        "triggers": data.get("triggers", []),
        "environment": data.get("environment"),
        "behaviour": data.get("behaviour"),
        "time_of_day": data.get("time_of_day"),
        "streak_broken": False,
        "break_details": {}
    }

    # Saving the data to daily_checkins
    memory["daily_checkins"] = memory.get("daily_checkins", [])
    memory["daily_checkins"].append(entry)
    save_memory(memory)

    # Updating streak
    streak = update_streak(entry)

    return jsonify({
        "message": "Check-in saved",
        "streak": streak.get("current_days", 0)
    })

# Returns all the info needed to build the main dashboard
@app.route("/dashboard", methods=["GET"])
def dashboard():
    from streak_system import get_streak
    from decision_engine import build_decision_message
    from prediction_engine import get_predictions
    from memory_manager import load_memory

    memory = load_memory()
    streak = get_streak()

    return jsonify({
        "streak": streak.get("current_days", 0),
        "decision": build_decision_message(),
        "predictions": get_predictions(),
        "username": memory.get("username", "User"),
        "my_why": memory.get("my_why", ""),
        "chosen_problem": memory.get("chosen_problem", "procrastination")
    })

# Getting the last 10 check ins from the memory file
@app.route("/history", methods=["GET"])
def history():
    from memory_manager import load_memory

    memory = load_memory()
    checkins = memory.get("daily_checkins", [])

    # Returning the 10 most recent check ins 
    return jsonify(checkins[-10:] if checkins else [])

# Resets the current streak counter to zero without deleting the past data
@app.route("/streak/reset", methods=["POST"])
def streak_reset():
    from memory_manager import load_memory, save_memory

    memory = load_memory()
    today = datetime.now().date().isoformat()
    prev_streak = memory.get("streak", {}).get("current_days", 0)

    # Recording the break
    if prev_streak > 0:
        last_checkin = (memory.get("daily_checkins") or [{}])[-1]
        memory.setdefault("streak_breaks", []).append({
            "date": today,
            "problem": memory.get("chosen_problem", ""),
            "previous_streak_length": prev_streak,
            "mood": last_checkin.get("mood", ""),
            "energy": last_checkin.get("energy", ""),
            "triggers": last_checkin.get("triggers", []),
            "environment": last_checkin.get("environment", ""),
            "behaviour": last_checkin.get("behaviour", ""),
            "time_of_day": last_checkin.get("time_of_day", ""),
            "break_details": {"manual_reset": True},
        })

    # Sets the streak counter back to zero
    memory["streak"] = {
        "current_days": 0,
        "start_date": today,
        "last_check_in": today,
        "status": "broken",
    }
    save_memory(memory)

    return jsonify({"message": "Streak reset to 0.", "previous_streak": prev_streak})

# Analyses the users triggers
@app.route("/triggers/analysis", methods=["GET"])
def trigger_analysis():
    from memory_manager import load_memory
    from collections import Counter

    memory = load_memory()
    checkins = memory.get("daily_checkins", [])
    breaks = memory.get("streak_breaks", [])
    high_msgs = memory.get("high_distress_messages", [])
    problem = memory.get("chosen_problem", "procrastination")

    # Trigger frequency
    all_triggers = []
    for c in checkins:
        all_triggers.extend([t for t in c.get("triggers", []) if t != "nothing"])
    trigger_counts = dict(Counter(all_triggers).most_common(6))
    total_triggers = sum(trigger_counts.values()) or 1
    trigger_pcts = {k: round(v / total_triggers * 100) for k, v in trigger_counts.items()}

    # Time of day distribution
    times = [c.get("time_of_day") for c in checkins if c.get("time_of_day")]
    time_counts = Counter(times)
    total_times = len(times) or 1
    time_pcts = {k: round(v / total_times * 100) for k, v in time_counts.items()}

    # Mood distribution
    moods = [c.get("mood") for c in checkins if c.get("mood")]
    mood_counts = dict(Counter(moods).most_common())

    # Energy distribution
    energies = [c.get("energy") for c in checkins if c.get("energy")]
    energy_counts = dict(Counter(energies).most_common())

    # Environment distribution
    envs = [c.get("environment") for c in checkins if c.get("environment")]
    env_counts = Counter(envs)
    total_envs = len(envs) or 1
    env_pcts = {k: round(v / total_envs * 100) for k, v in env_counts.most_common(4)}

    # Behaviour breakdown
    behaviours = [c.get("behaviour") for c in checkins if c.get("behaviour")]
    behaviour_counts = dict(Counter(behaviours).most_common())

    # Streak break analysis
    break_triggers = []
    break_times = []
    break_envs = []
    break_moods = []
    for b in breaks:
        break_triggers.extend([t for t in b.get("triggers", []) if t != "nothing"])
        if b.get("time_of_day"):
            break_times.append(b["time_of_day"])
        if b.get("environment"):
            break_envs.append(b["environment"])
        if b.get("mood"):
            break_moods.append(b["mood"])

    break_trigger_top = Counter(break_triggers).most_common(1)
    break_time_top = Counter(break_times).most_common(1)
    break_env_top = Counter(break_envs).most_common(1)
    break_mood_top = Counter(break_moods).most_common(1)

    # Generate insight message
    insight = ""
    if len(breaks) >= 2 and break_trigger_top:
        t = break_trigger_top[0][0]
        insight = f"I've noticed you're more likely to break your streak when {t} is a factor. Let's find a way to make it easier on those days."
    elif len(breaks) >= 1 and break_mood_top:
        m = break_mood_top[0][0]
        insight = f"Your streak breaks tend to happen when you're feeling {m}. Recognising this pattern is the first step."
    elif trigger_counts:
        top_trigger = list(trigger_counts.keys())[0]
        insight = f"I've noticed '{top_trigger}' comes up frequently as a trigger. Let's find a way to manage it better."
    elif len(checkins) > 0:
        insight = "Keep logging your check-ins — I'll start noticing patterns soon and help you understand your triggers."
    else:
        insight = "Start your daily check-ins so I can help you understand what affects your habits."

    return jsonify({
        "trigger_pcts": trigger_pcts,
        "time_pcts": time_pcts,
        "mood_counts": mood_counts,
        "energy_counts": energy_counts,
        "env_pcts": env_pcts,
        "behaviour_counts": behaviour_counts,
        "streak_breaks_count": len(breaks),
        "total_checkins": len(checkins),
        "high_distress_count": len(high_msgs),
        "break_top_trigger": break_trigger_top[0][0] if break_trigger_top else None,
        "break_top_time": break_time_top[0][0] if break_time_top else None,
        "break_top_env": break_env_top[0][0] if break_env_top else None,
        "break_top_mood": break_mood_top[0][0] if break_mood_top else None,
        "insight": insight,
        "problem": problem,
    })


# Gathers all the data needed to draw the Streaks page, including the calendar map.
@app.route("/streaks/data", methods=["GET"])
def streaks_data():
    from memory_manager import load_memory
    from streak_system import SUCCESS_RULES
    from collections import Counter

    memory = load_memory()
    checkins = memory.get("daily_checkins", [])
    breaks = memory.get("streak_breaks", [])
    streak = memory.get("streak", {})
    problem = memory.get("chosen_problem", "procrastination")
    high_msgs = memory.get("high_distress_messages", [])

    success_list = SUCCESS_RULES.get(problem, [])

    # Builds the calendar map.
    # Give every date the designated status (user info saved in memory)
    calendar = {}
    for c in checkins:
        date = c.get("date", "")
        if not date:
            continue
        beh = c.get("behaviour", "")
        if beh in success_list:
            status = "completed"
        elif beh:
            status = "partial"
        else:
            status = "missed"
        calendar[date] = {
            "status": status,
            "mood": c.get("mood"),
            "energy": c.get("energy"),
            "triggers": c.get("triggers", []),
            "environment": c.get("environment"),
            "behaviour": beh,
            "time_of_day": c.get("time_of_day"),
            "problem": c.get("problem", problem),
        }

    # Gives the day detail for conversation summary
    # Groups messages by date so user can click on a day to view them
    conv_by_date = {}
    for msg in high_msgs:
        d = msg.get("date", "")[:10]
        if d not in conv_by_date:
            conv_by_date[d] = []
        conv_by_date[d].append({
            "user": msg.get("user_message", ""),
            "bot": msg.get("bot_reply", ""),
            "distress": msg.get("distress_score", 0),
        })

    # Stats
    total_success = sum(1 for c in checkins if c.get("behaviour") in success_list)
    total_checkins = len(checkins)
    completion_rate = round((total_success / total_checkins * 100)) if total_checkins > 0 else 0

    # Calculating the longest streak they've ever had
    longest = 0
    current_run = 0
    for c in checkins:
        if c.get("behaviour") in success_list:
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 0

    # Insight generation
    if total_checkins >= 7:
        # Finding the best day of week for them
        from datetime import datetime as dt
        day_success = {}
        day_total = {}
        for c in checkins:
            try:
                wd = dt.strptime(c.get("date", ""), "%Y-%m-%d").strftime("%A")
            except:
                continue
            day_total[wd] = day_total.get(wd, 0) + 1
            if c.get("behaviour") in success_list:
                day_success[wd] = day_success.get(wd, 0) + 1

        best_day = max(day_success, key=lambda d: day_success[d] / max(day_total.get(d, 1), 1)) if day_success else None
        worst_day = min(day_success, key=lambda d: day_success.get(d, 0) / max(day_total.get(d, 1), 1)) if day_success else None

        # Finding their best time of day
        time_success = {}
        time_total = {}
        for c in checkins:
            t = c.get("time_of_day", "")
            if not t:
                continue
            time_total[t] = time_total.get(t, 0) + 1
            if c.get("behaviour") in success_list:
                time_success[t] = time_success.get(t, 0) + 1

        best_time = max(time_success, key=lambda t: time_success[t] / max(time_total.get(t, 1), 1)) if time_success else None

        parts = []
        if best_day and best_time:
            parts.append(f"You're most consistent on {best_day} {best_time}s.")
        elif best_day:
            parts.append(f"You're most consistent on {best_day}s.")

        if worst_day and worst_day != best_day:
            parts.append(f"Consider setting a gentle reminder for {worst_day}s, as that tends to be your slip point.")

        if completion_rate >= 75:
            parts.append("Keep it up!")
        elif completion_rate >= 50:
            parts.append("You're building momentum. Small consistent steps matter most.")
        else:
            parts.append("Every check-in counts. Focus on one good day at a time.")

        insight = " ".join(parts) if parts else "Keep logging to unlock deeper insights."
    else:
        insight = "Complete more daily check-ins to unlock personalised streak insights."

    # Streak message
    current_days = streak.get("current_days", 0)
    if current_days >= 21:
        streak_title = "Incredible Discipline"
        streak_msg = f"You've maintained {current_days} days of consistency. This level of commitment is reshaping your habits at a deep level."
    elif current_days >= 14:
        streak_title = "Steady Rhythm"
        streak_msg = f"You're building a strong foundation. Every small act reinforces your mental clarity. You're almost halfway to a new record."
    elif current_days >= 7:
        streak_title = "Building Momentum"
        streak_msg = f"A full week of consistency! Your brain is starting to wire this as a habit. Keep the rhythm going."
    elif current_days >= 3:
        streak_title = "Getting Started"
        streak_msg = f"Three days in. The hardest part is behind you. Each day forward strengthens your resolve."
    elif current_days >= 1:
        streak_title = "Fresh Start"
        streak_msg = "You showed up today. That's the most important step. Let's keep this going."
    else:
        streak_title = "Ready to Begin"
        streak_msg = "Every journey starts with a single step. Log today's check-in to begin your streak."

    return jsonify({
        "calendar": calendar,
        "conversations": conv_by_date,
        "streak_days": current_days,
        "streak_title": streak_title,
        "streak_msg": streak_msg,
        "longest_streak": longest,
        "total_success": total_success,
        "total_checkins": total_checkins,
        "completion_rate": completion_rate,
        "insight": insight,
        "problem": problem,
    })


# Predicts how likely the user is to break their streak
@app.route("/predictions", methods=["GET"])
def predictions():
    from ml_streak_predictor import predict_streak_break_risk, get_feature_importance, model_status
    from memory_manager import load_memory
    from collections import Counter

    memory = load_memory()
    checkins = memory.get("daily_checkins", [])
    streak = memory.get("streak", {})
    problem = memory.get("chosen_problem", "procrastination")

    # Running the machine learning prediction
    prediction = predict_streak_break_risk()

    # Building the consistency chart data
    from streak_system import SUCCESS_RULES
    recent = checkins[-14:] if len(checkins) >= 14 else checkins
    consistency = []
    for c in recent:
        beh = c.get("behaviour", "")
        success = beh in SUCCESS_RULES.get(c.get("problem", problem), [])
        consistency.append({
            "date": c.get("date", ""),
            "success": success,
            "projected": False
        })

    # Guessing the next 7 days based on their recent success rate
    if len(recent) >= 3:
        recent_success = sum(1 for c in consistency if c["success"]) / max(len(consistency), 1)
    else:
        recent_success = 0.5

    from datetime import timedelta
    import random
    last_date = datetime.now()
    for i in range(1, 8):
        proj_date = (last_date + timedelta(days=i)).strftime("%Y-%m-%d")
        proj_success = random.random() < recent_success
        consistency.append({
            "date": proj_date,
            "success": proj_success,
            "projected": True
        })

    # Calculating if their trend is changing
    if len(checkins) >= 7:
        last7 = checkins[-7:]
        prev7 = checkins[-14:-7] if len(checkins) >= 14 else checkins[:7]
        last7_rate = sum(1 for c in last7 if c.get("behaviour") in SUCCESS_RULES.get(c.get("problem", problem), [])) / max(len(last7), 1)
        prev7_rate = sum(1 for c in prev7 if c.get("behaviour") in SUCCESS_RULES.get(c.get("problem", problem), [])) / max(len(prev7), 1)
        if last7_rate > prev7_rate + 0.1:
            trend = "trending_up"
        elif last7_rate < prev7_rate - 0.1:
            trend = "trending_down"
        else:
            trend = "stable"
    else:
        trend = "not_enough_data"

    # Creating actionable suggestions based on what the ML model found
    suggestions = []
    if prediction.get("available"):
        factors = prediction.get("top_factors", [])
        if "mood" in factors or "energy level" in factors:
            suggestions.append({
                "icon": "energy",
                "title": "Manage Your Energy",
                "desc": "Low energy days correlate with streak breaks. Try lighter tasks on those days."
            })
        if "time of day" in factors or "night" in factors:
            suggestions.append({
                "icon": "time",
                "title": "Shift Your Schedule",
                "desc": "Late-night sessions are riskier. Move your habit window earlier."
            })
        if "stress" in factors or "tiredness" in factors:
            suggestions.append({
                "icon": "calm",
                "title": "Build a Buffer Routine",
                "desc": "Add a short wind-down before your habit on stressful days."
            })
        if "loneliness" in factors or "alone" in factors:
            suggestions.append({
                "icon": "connect",
                "title": "Stay Connected",
                "desc": "Isolation increases risk. Try a quick check-in with someone first."
            })
        if "boredom" in factors:
            suggestions.append({
                "icon": "engage",
                "title": "Break the Boredom Loop",
                "desc": "Boredom is a key trigger. Have a go-to alternative activity ready."
            })
        if not suggestions:
            suggestions.append({
                "icon": "maintain",
                "title": "Maintain Your Routine",
                "desc": "Your patterns are positive. Keep your current approach going."
            })
    else:
        suggestions.append({
            "icon": "log",
            "title": "Keep Logging",
            "desc": "More check-in data will unlock personalised predictions."
        })

    # Only showing the top 2 suggestions
    suggestions = suggestions[:2]

    return jsonify({
        "prediction": prediction,
        "consistency": consistency,
        "trend": trend,
        "streak_days": streak.get("current_days", 0),
        "total_checkins": len(checkins),
        "goal_days": 21,
        "problem": problem,
        "suggestions": suggestions,
    })


@app.route("/predictions/train", methods=["POST"])
def train_model():
    # Trains the ML model manually when requested
    from ml_streak_predictor import train_streak_model
    result = train_streak_model()
    return jsonify(result)


@app.route("/predictions/status", methods=["GET"])
def ml_status():
    # Checks the status of the trained ML model
    from ml_streak_predictor import model_status
    return jsonify(model_status())


@app.route("/predictions/simulate", methods=["POST"])
def simulate_data():
    # Generates fake data for testing and trains the ML model on it
    from simulate_user_data import simulate
    from ml_streak_predictor import train_streak_model

    data = request.json or {}
    days = data.get("days", 60)
    problem = data.get("problem", "procrastination")

    simulate(days=days, problem=problem, reset=True)
    train_result = train_streak_model()

    return jsonify({
        "message": f"Simulated {days} days and trained model.",
        "training": train_result
    })


# Resets the app back to a blank slate and trains a new model to show the app onboarding flow from scratch
@app.route("/reset", methods=["POST"])
def reset():
    from memory_manager import default_memory, save_memory
    import shutil

    # Resetting the memory back to its empty default state
    save_memory(default_memory())

    # Clearing the chat history for this session
    clear_history()

    # Deleting the saved ML model file
    if os.path.exists("ml_models"):
        shutil.rmtree("ml_models", ignore_errors=True)

    return jsonify({"message": "All data reset. Fresh start."})


# Returns the 3 simulation profiles to display
@app.route("/simulations/profiles", methods=["GET"])
def sim_profiles():
    profiles = [
        {
            "id": "resilient",
            "name": "Nadia - The Resilient Builder",
            "problem": "procrastination",
            "days": 45,
            "desc": "Strong streak consistency (~80% completion). Occasional slip on tired evenings but recovers quickly. Mostly positive moods.",
            "avatar_color": "#3d7a5a",
        },
        {
            "id": "struggling",
            "name": "Marcus - The Struggling Fighter",
            "problem": "isolation",
            "days": 60,
            "desc": "Frequent streak breaks (~40% completion). Often lonely, low energy, late-night check-ins. High distress journal entries.",
            "avatar_color": "#c45d3e",
        },
        {
            "id": "recovering",
            "name": "Lala - The Recovering Balancer",
            "problem": "overspending",
            "days": 35,
            "desc": "Mixed results (~60% completion). Started badly but improving. Stress triggers spending. Recent uptick in success.",
            "avatar_color": "#b89a4a",
        },
    ]
    return jsonify(profiles)


# Loads a specific simulated user profile
@app.route("/simulations/load", methods=["POST"])
def sim_load():
    import random
    import shutil
    from memory_manager import default_memory, save_memory
    from streak_system import SUCCESS_RULES

    data = request.json or {}
    profile_id = data.get("profile", "resilient")

    # Starting with a clean slate
    memory = default_memory()
    clear_history()
    if os.path.exists("ml_models"):
        shutil.rmtree("ml_models", ignore_errors=True)

    # Setting up the Profile Configs
    PROFILES = {
        "resilient": {
            "username": "Nadia",
            "problem": "procrastination",
            "my_why": "I want to prove to myself I can finish what I start.",
            "days": 45,
            "fail_base": 0.15,
            "mood_weights": [0.40, 0.30, 0.15, 0.10, 0.05],
            "energy_weights": [0.30, 0.40, 0.20, 0.10],
            "journal_msgs": [
                ("I stayed focused today, felt good.", 0.2),
                ("Had a hard time after lunch but pushed through.", 0.45),
                ("Really proud of myself for finishing early.", 0.15),
                ("Tired but I did it. Small win.", 0.35),
                ("I'm starting to believe I can change this.", 0.2),
                ("My focus was off today. Disappointed in myself.", 0.65),
                ("I keep checking my phone. It's like I can't stop.", 0.75),
            ],
        },
        "struggling": {
            "username": "Marcus",
            "problem": "isolation",
            "my_why": "I don't want to feel so alone anymore.",
            "days": 60,
            "fail_base": 0.55,
            "mood_weights": [0.05, 0.15, 0.30, 0.25, 0.25],
            "energy_weights": [0.05, 0.20, 0.40, 0.35],
            "journal_msgs": [
                ("I didn't talk to anyone today. Again.", 0.8),
                ("I feel invisible. Nobody checks on me.", 0.9),
                ("Tried to text someone but couldn't bring myself to do it.", 0.7),
                ("I was around people but still felt alone.", 0.75),
                ("Today was really dark. I just stayed in bed.", 0.85),
                ("Had a short call with mum. It helped a little.", 0.4),
                ("I'm so tired of feeling like this every day.", 0.9),
                ("Went to the shop. That's something I guess.", 0.5),
                ("I hate weekends. Everyone is busy except me.", 0.8),
            ],
        },
        "recovering": {
            "username": "Lala",
            "problem": "overspending",
            "my_why": "I want financial freedom and to stop stress-buying.",
            "days": 35,
            "fail_base": 0.40,
            "mood_weights": [0.20, 0.30, 0.25, 0.15, 0.10],
            "energy_weights": [0.15, 0.35, 0.30, 0.20],
            "journal_msgs": [
                ("Almost bought something I didn't need. Caught myself.", 0.5),
                ("Stressed about bills. Opened a shopping app without thinking.", 0.7),
                ("Good day. Stuck to my budget!", 0.2),
                ("I spent too much again. Feel guilty.", 0.8),
                ("Trying the 24-hour rule before buying. It's working.", 0.3),
                ("My friend invited me shopping. I said no. Proud of that.", 0.25),
                ("Bad day at work. Ended up spending to feel better.", 0.75),
            ],
        },
    }

    profile = PROFILES.get(profile_id, PROFILES["resilient"])

    MOODS = ["good", "okay", "low", "frustrated", "anxious"]
    ENERGIES = ["high", "normal", "low", "very low"]
    TRIGGERS_POOL = ["stress", "boredom", "argument", "loneliness", "tiredness"]
    ENVS = ["alone", "with friends", "with family", "busy (work/school)", "mostly online"]
    TIMES = ["morning", "afternoon", "evening", "night"]

    BEHAVIOURS = {
        "procrastination": ["focused well", "slightly distracted", "procrastinated", "avoided tasks"],
        "overspending": ["no spending", "planned spending", "impulse purchase", "overspent"],
        "isolation": ["connected well", "some interaction", "very little interaction", "avoided people"],
    }

    problem = profile["problem"]
    success_list = SUCCESS_RULES.get(problem, [])
    behaviours = BEHAVIOURS[problem]
    success_behaviours = [b for b in behaviours if b in success_list]
    fail_behaviours = [b for b in behaviours if b not in success_list]

    memory["username"] = profile["username"]
    memory["chosen_problem"] = problem
    memory["my_why"] = profile["my_why"]

    from datetime import timedelta
    start = datetime.now() - timedelta(days=profile["days"])

    checkins = []
    streak = 0
    longest = 0
    breaks = []

    # Using a fixed seed so the same profile always generates exactly the same check-ins, streak history, and journal entries for consistent testing
    PROFILE_SEEDS = {
        "resilient":  42,    # Nadia — stable, improving user
        "struggling": 17,    # Marcus — high distress, frequent breaks
        "recovering": 99,    # Lala — early difficulty, then recovery
    }
    rng = random.Random(PROFILE_SEEDS.get(profile_id, 42))

    for i in range(profile["days"]):
        day = start + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")

        mood = rng.choices(MOODS, weights=profile["mood_weights"])[0]
        energy = rng.choices(ENERGIES, weights=profile["energy_weights"])[0]
        time_of_day = rng.choice(TIMES)
        env = rng.choice(ENVS)

        # The number of triggers they log goes up if they are in a bad mood
        n_triggers = 1 if mood in ["good", "okay"] else rng.randint(1, 3)
        triggers = rng.sample(TRIGGERS_POOL, min(n_triggers, len(TRIGGERS_POOL)))

        # Adjusting how likely they are to fail based on mood, energy and time of day
        fail_prob = profile["fail_base"]
        if mood in ["frustrated", "anxious"]:
            fail_prob += 0.2
        if energy in ["low", "very low"]:
            fail_prob += 0.1
        if time_of_day == "night":
            fail_prob += 0.1
        if mood == "good":
            fail_prob -= 0.15
        # The 'recovering' profile gets better over time (in the second half of the days)
        if profile_id == "recovering" and i > profile["days"] * 0.6:
            fail_prob -= 0.2
        fail_prob = max(0.05, min(fail_prob, 0.85))

        if rng.random() < fail_prob:
            behaviour = rng.choice(fail_behaviours)
        else:
            behaviour = rng.choice(success_behaviours)

        is_success = behaviour in success_list

        entry = {
            "date": date_str,
            "problem": problem,
            "mood": mood,
            "energy": energy,
            "triggers": triggers,
            "environment": env,
            "behaviour": behaviour,
            "time_of_day": time_of_day,
            "streak_broken": False,
            "break_details": {}
        }
        checkins.append(entry)

        if is_success:
            streak += 1
            longest = max(longest, streak)
        else:
            if streak > 0:
                breaks.append({
                    "date": date_str,
                    "problem": problem,
                    "previous_streak_length": streak,
                    "mood": mood,
                    "energy": energy,
                    "triggers": triggers,
                    "environment": env,
                    "behaviour": behaviour,
                    "time_of_day": time_of_day,
                    "break_details": {}
                })
            streak = 0

    # Setting a fixed mood and behaviour for today so the dashboard always shows the same greeting after loading the simulation.
    TODAY_DEFAULTS = {
        "resilient":  {"mood": "good",  "energy": "normal",   "behaviour": success_behaviours[0]},
        "struggling": {"mood": "low",   "energy": "low",      "behaviour": fail_behaviours[0]   if fail_behaviours else success_behaviours[0]},
        "recovering": {"mood": "okay",  "energy": "normal",   "behaviour": success_behaviours[0]},
    }
    today_defaults = TODAY_DEFAULTS.get(profile_id, TODAY_DEFAULTS["resilient"])

    today_str = datetime.now().strftime("%Y-%m-%d")
    today_entry = {
        "date": today_str,
        "problem": problem,
        "mood": today_defaults["mood"],
        "energy": today_defaults["energy"],
        "triggers": ["stress"],
        "environment": "alone",
        "behaviour": today_defaults["behaviour"],
        "time_of_day": "morning",
        "streak_broken": False,
        "break_details": {}
    }
    # We only add today if the loop above hasn't already generated it
    if not any(c["date"] == today_str for c in checkins):
        checkins.append(today_entry)
        if today_defaults["behaviour"] in success_list:
            streak += 1
            longest = max(longest, streak)

    memory["daily_checkins"] = checkins
    memory["streak_breaks"] = breaks
    memory["streak"] = {
        "current_days": streak,
        "start_date": checkins[-1]["date"] if checkins else None,
        "last_check_in": today_str,
        "status": "active" if streak > 0 else "broken"
    }

    # Generating realistic journal entries for this profile
    # Each simulated profile has a list of realistic journal messages with pre-assigned distress scores. We spread these across the whole date range so the ML model has something to train on.
    journal_msgs = profile["journal_msgs"]
    simulated_chat_log = []
    high_distress = []

    for i, (journal_text, journal_distress_score) in enumerate(journal_msgs):
        # Spreading the journal entries evenly across the simulated dates
        day_offset = int((i / max(len(journal_msgs), 1)) * profile["days"])
        day_offset = min(day_offset, profile["days"] - 1)
        journal_date = start + timedelta(days=day_offset)
        journal_timestamp = journal_date.isoformat()

        # Generating fake emotion scores that match their distress level
        # A higher distress score means more sadness/fear and less joy
        simulated_emotions = {
            "sadness": round(min(journal_distress_score * 1.1, 1.0), 3),
            "fear":    round(journal_distress_score * 0.5, 3),
            "anger":   round(min(journal_distress_score * 0.3, 0.5), 3),
            "joy":     round(max(1.0 - journal_distress_score, 0.05), 3),
        }

        # Assigning a distress label based on the score
        if journal_distress_score >= 0.65:
            simulated_distress_label = "high distress"
        elif journal_distress_score >= 0.4:
            simulated_distress_label = "moderate distress"
        else:
            simulated_distress_label = "low distress"

        # Automatically creating a summary for the entry
        journal_summary_text = generate_journal_summary(
            journal_text, simulated_emotions,
            journal_distress_score, simulated_distress_label
        )

        # Building the full journal entry object just like a real one
        simulated_journal_entry = {
            "timestamp": journal_timestamp,
            "user_message": journal_text,
            "bot_reply": "I hear you. That sounds really tough. Just take things one step at a time.",
            "summary": journal_summary_text,
            "emotions": simulated_emotions,
            "distress_score": round(journal_distress_score, 4),
            "distress_label": simulated_distress_label,
            "risk_level": "high" if journal_distress_score >= 0.8 else "low",
            "checkin_context": None
        }
        simulated_chat_log.append(simulated_journal_entry)

        # Also tracking the high-distress messages separately for the Streaks page
        if journal_distress_score >= 0.65:
            high_distress.append({
                "date": journal_timestamp,
                "user_message": journal_text,
                "bot_reply": "I hear you. That sounds really tough. Just take things one step at a time.",
                "distress_score": journal_distress_score,
                "emotions": simulated_emotions
            })

    memory["chat_log"] = simulated_chat_log
    memory["high_distress_messages"] = high_distress

    save_memory(memory)

    # Finally, training the ML model on all this new simulated data
    try:
        from ml_streak_predictor import train_streak_model
        train_result = train_streak_model()
    except:
        train_result = {"trained": False}

    return jsonify({
        "message": f"Loaded profile: {profile['username']}",
        "username": profile["username"],
        "problem": problem,
        "days": profile["days"],
        "checkins": len(checkins),
        "breaks": len(breaks),
        "current_streak": streak,
        "longest_streak": longest,
        "high_distress_msgs": len(high_distress),
        "ml_training": train_result,
    })


# Start the Flask development server on port 5000.
# The Next.js frontend connects to http://127.0.0.1:5000
if __name__ == "__main__":
    app.run(port=5000, debug=True, use_reloader=False, threaded=True)