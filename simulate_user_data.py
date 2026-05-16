# Gublu User Data Simulator
# This file creates fake user check-in data for testing and demo, saving time on entering data manually
# It simulates 3 different types of user profiles to show all aspects of the functionlity by simulating days worth of data

import json
import random
import argparse
from datetime import datetime, timedelta

# Setting all the information that will be used in the simulation
MEMORY_FILE = "gublu_memory.json"
MOODS = ["good", "okay", "low", "frustrated", "anxious"]
ENERGIES = ["high", "normal", "low", "very low"]
TRIGGERS = ["stress", "boredom", "argument", "loneliness", "tiredness", "nothing"]
ENVIRONMENTS = ["alone", "with friends", "with family", "busy (work/school)", "mostly online", "online"]
TIME_OPTIONS = ["morning", "afternoon", "evening", "night"]
BEHAVIOURS = {
    "procrastination": ["focused well", "slightly distracted", "procrastinated", "avoided tasks"],
    "overspending": ["no spending", "planned spending", "impulse purchase", "overspent"],
    "isolation": ["connected well", "some interaction", "very little interaction", "avoided people"],
}
SUCCESS_BEHAVIOURS = {
    "procrastination": ["focused well", "slightly distracted"],
    "overspending": ["no spending", "planned spending"],
    "isolation": ["connected well", "some interaction"],
}

# This function is used to set data for a given time period for each areas of focus (procrastination, isolation, overspending)
# It generates daily survey and other needed data for the different simulation profiles
# The simulated users will be representing different types of users to show different cases
def generate_checkins(days=60, problem="procrastination"):
    checkins = []
    start_date = datetime.now() - timedelta(days=days)

    for i in range(days):
        date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")  # Simulating dates for check ins
        is_weekend = (start_date + timedelta(days=i)).weekday() >= 5  # Checking if date is a weekend for
        rand = random.random()  # Generating a random number for deciding the mood on that day

        # Choosing the mood
        if rand < 0.35:
            mood = "good"
        elif rand < 0.60:
            mood = "okay"
        elif rand < 0.78:
            mood = "low"
        elif rand < 0.90:
            mood = "frustrated"
        else:
            mood = "anxious"

        # The energy is being decided on the basis of the current mood for more realistic check in data
        if mood in ["good", "okay"]:
            energy = random.choice(["high", "normal", "normal"]) 
        elif mood == "low":
            energy = random.choice(["normal", "low", "low"])  
        else:
            energy = random.choice(["low", "very low"])  

        time_of_day = random.choice(TIME_OPTIONS)  # Choosing a time when the behaviour occured

        # Weekend environments are chosen differently than weekday environments for more realism (unnecessary, might remove later) ***********************ATTENTION!!!!!!!!!!!!!!!!***********************************************************************************
        if is_weekend:
            environment = random.choice(["alone", "with friends", "with family", "online"]) 
        else:
            environment = random.choice(["busy (work/school)", "alone", "mostly online", "online"]) 

        trigger_pool = []  # Creating an empty trigger list that will be filled based on mood, energy and environment

        # Setting the stress and argument triggers according to the user's mood
        if mood in ["frustrated", "anxious"]:
            trigger_pool.extend(["stress", "stress", "argument"])

        # Tiredness according to the current energy 
        if energy in ["low", "very low"]:
            trigger_pool.extend(["tiredness", "tiredness"])

        # Loneliness and boredom according to the environment
        if environment in ["alone"]:
            trigger_pool.extend(["loneliness", "loneliness"])
        if mood in ["low", "okay"] and environment in ["online", "mostly online"]:
            trigger_pool.extend(["boredom", "boredom"])

        # If there is no trigger then choose nothing
        if not trigger_pool:
            triggers = ["nothing"]

        else:
            n_triggers = random.randint(1, min(3, len(trigger_pool)))  # Choosing how many triggers to select
            triggers = list(set(random.sample(trigger_pool, n_triggers)))  # Selecting triggers and removing any duplicates

        fail_prob = 0.25  # Setting the minimum chance of a failed habit day

        # Increasing the chance of failure according to the mood, energy, time of day, triggers and the environment of the user
        if mood in ["frustrated", "anxious"]:
            fail_prob += 0.25

        if energy in ["low", "very low"]:
            fail_prob += 0.15

        if time_of_day == "night":
            fail_prob += 0.15

        if "stress" in triggers:
            fail_prob += 0.1

        if "loneliness" in triggers and problem == "isolation":
            fail_prob += 0.2

        if "boredom" in triggers and problem in ["procrastination", "overspending"]:
            fail_prob += 0.15

        if environment in ["alone"] and problem == "isolation":
            fail_prob += 0.1

        if environment in ["online", "mostly online"] and problem in ["procrastination", "overspending"]:
            fail_prob += 0.1

        # Decreasing the chance of failure according to the information
        if mood == "good":
            fail_prob -= 0.15

        if energy == "high":
            fail_prob -= 0.1

        if time_of_day == "morning":
            fail_prob -= 0.1

        fail_prob = max(0.05, min(fail_prob, 0.85))  # Setting chance of failure between 5% and 85%

        # Getting all information for chance of success
        behaviours = BEHAVIOURS[problem]  
        success = SUCCESS_BEHAVIOURS[problem] 
        failure = [b for b in behaviours if b not in success]

        # Randomising streak breakage for the current day according to the faliure probability generated
        # Also chooses the reason at random
        if random.random() < fail_prob:
            behaviour = random.choice(failure) 
        else:
            behaviour = random.choice(success)

        # Updating all the checkin data in the list
        checkins.append({
            "date": date,
            "problem": problem,
            "mood": mood,
            "energy": energy,
            "triggers": triggers,
            "environment": environment,
            "behaviour": behaviour,
            "time_of_day": time_of_day,
            "streak_broken": False,
            "break_details": {}
        })

    return checkins

# This function gets the memory stored in the gublu_memory.json file. It also generates a blank memory if it doesn't exist already.
def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:  # Reading the memory file
            return json.load(f)
            
    # Returning blank memory if it doesn't exist
    except:
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
            "high_distress_messages": []
        }


# This function will save the new memory data
def save_memory(memory):

    with open(MEMORY_FILE, "w") as f:  # Write mode this time
        json.dump(memory, f, indent=2) 

# This function is to run the simulation. It also has a reset feature to start from default or as a new user
def simulate(days=60, problem="procrastination", reset=False):
    memory = load_memory()

    # Removing stored memory if the data is resetted
    if reset:
        memory["daily_checkins"] = [] 
        memory["streak_breaks"] = []  
        memory["streak"] = {
            "current_days": 0,
            "start_date": None,
            "last_check_in": None,
            "status": "inactive"
        }
        print("[RESET] Old check-in data cleared.")

    # Setting a demo username if no username exists
    if not memory.get("username"):
        memory["username"] = "Demo User"

    # Setting the chosen problem if it has not been set yet
    if not memory.get("chosen_problem"):
        memory["chosen_problem"] = problem

    # Setting a "My Why" section data if it has not been set yet
    if not memory.get("my_why"):
        memory["my_why"] = "To build better habits and understand myself."

    memory["chosen_problem"] = problem  # Updates the focus area

    checkins = generate_checkins(days, problem)  # Fake check in data that was set

    memory["daily_checkins"].extend(checkins)  # Adding the fake check ins

    # This helps to generate the streak brakages according to the rules set
    from streak_system import SUCCESS_RULES
    streak_length = 0 
    streak_breaks = []  
    last_date = None  # Last check in date

    # Looping through all simulated data dates to check streak breakages
    for c in memory["daily_checkins"]:
        p = c.get("problem", problem)  
        b = c.get("behaviour", "")  
        success = b in SUCCESS_RULES.get(p, [])  
        if success:
            streak_length += 1

        else:
            # Saving the streak break details if it was ongoing before the break
            if streak_length > 0:
                streak_breaks.append({
                    "date": c["date"],
                    "problem": p,
                    "previous_streak_length": streak_length,
                    "mood": c.get("mood"),
                    "energy": c.get("energy"),
                    "triggers": c.get("triggers", []),
                    "environment": c.get("environment"),
                    "behaviour": b,
                    "time_of_day": c.get("time_of_day"),
                    "break_details": {}
                })

            streak_length = 0  # Resetting the streak
        last_date = c["date"]  # Updating the date

    memory["streak_breaks"] = streak_breaks  # Saving

    # Saving the rebuilt streak information into memory
    memory["streak"] = {
        "current_days": streak_length,
        "start_date": last_date,
        "last_check_in": last_date,
        "status": "active" if streak_length > 0 else "broken"
    }

    save_memory(memory)  # Saving all simulated data into the memory file
    total = len(memory["daily_checkins"])  # Counting the total check ins
    n_breaks = len(streak_breaks)  # Counting total streak breaks

    # Printing the summary
    print(f"[OK] Simulated {days} days of '{problem}' check-ins.")
    print(f"   Total check-ins: {total}")
    print(f"   Streak breaks: {n_breaks}")
    print(f"   Current streak: {streak_length} days")

# Running the simulator from the terminal
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate Gublu user data")  # Creating the command line parser
    parser.add_argument("--days", type=int, default=60, help="Number of days to simulate (30–100)")  # Adding days option
    parser.add_argument(  # Adding problem option
        "--problem",
        type=str,
        default="procrastination",
        choices=["procrastination", "overspending", "isolation"]
    )
    parser.add_argument("--reset", action="store_true", help="Clear old simulated data first")  # Adding reset option
    args = parser.parse_args()  # Reading the command line arguments
    simulate(days=args.days, problem=args.problem, reset=args.reset)  # Running the simulation with the selected options