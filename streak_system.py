
# User's Streak System
# This file is based on the user's streak system
# It deals with the rules and conditions of a successful streak count or a streak breakage
# If a streak is broken, the corresponding data of the user's behaviour is saved in memory, which helps the prediction model understand the user's patterns

from memory_manager import load_memory, save_memory  
from datetime import datetime  

# Setting the rules for a successful streak
SUCCESS_RULES = {

    "procrastination": [
        "focused well",
        "slightly distracted"
    ],

    "overspending": [
        "no spending",
        "planned spending"
    ],

    "isolation": [
        "connected well",
        "some interaction"
    ]
}

# This function check and retrieves the useer's current streak information from the memory
# For the case of a new user, it will create a new streak data structure
def get_or_create_streak(memory):    
    if "streak" not in memory or not isinstance(memory["streak"], dict):

        # Creating a fresh streak (broken streak or new user)
        memory["streak"] = {
            "current_days": 0,
            "start_date": None,
            "last_check_in": None,
            "status": "inactive"
        }
    return memory["streak"]

# This function checks if the user has had a successful streak or not, based on the stored data of the users input.
# For example:
# is_success("procrastination", "focused well") returns True.
# is_success("procrastination", "procrastinated") returns False.
def is_success(problem, behaviour):
    success_behaviours = SUCCESS_RULES.get(problem, [])
    return behaviour in success_behaviours

# The following function updates the user's streak data based on the check-in data (their area of focus, corresponding behaviour log success, if the user has checked in today,etc.)
def update_streak(entry):
    memory = load_memory()
    streak = get_or_create_streak(memory)
    problem = entry["problem"]
    behaviour = entry["behaviour"]
    today = entry["date"]
    today_was_success = is_success(problem, behaviour)
    if streak["start_date"] is None: # Checking if this is the first streak update or not
        streak["start_date"] = today
        streak["current_days"] = 1 if today_was_success else 0
        streak["last_check_in"] = today
        streak["status"] = "active" if today_was_success else "broken" # Sets the streak status on the basis of success or failiure

    else:
        if streak["last_check_in"] == today: # Checking if the streak has already been updated for the current day
            print("Already checked in today.")
            return streak 

        # Continuing the streak if the users data points to success
        if today_was_success:
            streak["current_days"] += 1 # Increasing the current streak
            streak["status"] = "active" # Confirming that the streak is not broken

        else:
            log_streak_break(memory, entry, streak["current_days"]) # Checking and storing streak breakage
            streak["current_days"] = 0 # Resetting the streak
            streak["start_date"] = today # Starting a new streak period from today
            streak["status"] = "broken" # Telling that the streak is broken
        streak["last_check_in"] = today
    save_memory(memory)
    return streak

# The function helps to log and store streak breakages along with the corresponding data inputted by the user leading to the streak break
def log_streak_break(memory, entry, previous_streak):
    if "streak_breaks" not in memory:
        memory["streak_breaks"] = []

    # Storing the details of the broken streak in a dictionary
    break_entry = {
        "date": entry["date"],
        "problem": entry["problem"],
        "previous_streak_length": previous_streak,
        "mood": entry["mood"],
        "energy": entry["energy"],
        "triggers": entry["triggers"],
        "environment": entry["environment"],
        "behaviour": entry["behaviour"],
        "time_of_day": entry["time_of_day"],
        "break_details": entry.get("break_details", {})
    }
    memory["streak_breaks"].append(break_entry)


# This function gets the streak information (essential for the UI)
def get_streak():
    memory = load_memory()
    streak = get_or_create_streak(memory)
    return streak


# Function for getting the streak summary
def get_streak_summary():
    streak = get_streak()
    return {
        "current_days": streak["current_days"],
        "status": streak["status"],
        "start_date": streak["start_date"],
        "last_check_in": streak["last_check_in"]
    }

# Testing all the functions in the file
if __name__ == "__main__":
    from daily_checkin import run_daily_checkin
    print("Running test check-in...\n")
    entry = run_daily_checkin()
    streak = update_streak(entry)
    print("\nStreak Updated:")
    print(streak)