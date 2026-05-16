# Handles the terminal based daily check in flow
# Asks the user about their mood, energy, triggers, environment, behaviour, and time of day
from memory_manager import load_memory, save_memory
from datetime import datetime


# Shared check in options
# These lists match the options shown in the frontend check in page
MOODS = ["good", "okay", "low", "frustrated", "anxious"]

ENERGY = ["high", "normal", "low", "very low"]

TRIGGERS = [
    "stress",
    "boredom",
    "argument",
    "loneliness",
    "tiredness",
    "nothing"
]

ENVIRONMENT = [
    "alone",
    "with friends",
    "with family",
    "busy (work/school)",
    "mostly online"
]


# Problem specific behaviours
# Each problem type has its own set of behaviour options
BEHAVIOUR_OPTIONS = {

    "procrastination": [
        "focused well",
        "slightly distracted",
        "procrastinated",
        "avoided tasks"
    ],

    "overspending": [
        "no spending",
        "planned spending",
        "impulse purchase",
        "overspent"
    ],

    "isolation": [
        "connected well",
        "some interaction",
        "minimal interaction",
        "completely isolated"
    ]
}


# Input helpers
def choose_one(options):
    # Displays a numbered list and asks the user to pick one item
    if not options:
        return None  # Safety fallback if no options are provided

    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")

    while True:
        try:
            choice = int(input("> "))
            if 1 <= choice <= len(options):
                return options[choice - 1]
        except Exception:
            pass
        print("Invalid input, try again.")


def choose_multiple(options):
    # Displays a numbered list and asks the user to pick one or more items
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
    print("Enter numbers separated by commas:")

    while True:
        try:
            raw_input = input("> ")
            chosen_indices = [int(x.strip()) for x in raw_input.split(",")]
            selected = [options[i - 1] for i in chosen_indices if 1 <= i <= len(options)]
            if selected:
                return selected
        except Exception:
            pass
        print("Invalid input, try again.")


# Streak break follow up
def streak_break_questions():
    # Asks a short follow up to understand what led to a streak break
    print("\n--- Let's understand what happened ---\n")

    causes = [
        "stress",
        "tiredness",
        "emotion",
        "environment",
        "habit",
        "impulse"
    ]

    print("What led to this?")
    cause = choose_multiple(causes)

    print("\nDid you realise it was happening?")
    awareness = choose_one(["yes", "no", "too late"])

    print("\nCould this have been avoided?")
    could_prevent = choose_one(["yes", "maybe", "no"])

    return {
        "cause": cause,
        "awareness": awareness,
        "preventable": could_prevent
    }


# Main daily check in function
def run_daily_checkin(broken=False):
    # Runs the full daily check in flow in the terminal
    memory = load_memory()

    # Uses the user's saved problem type
    selected_problem = memory.get("chosen_problem", "procrastination")

    print("\n--- Daily Check-in ---\n")

    # Asks follow up questions if the streak broke today
    break_details = None
    if broken:
        break_details = streak_break_questions()

    # Mood
    print("\nHow did you feel today?")
    mood = choose_one(MOODS)

    # Energy
    print("\nHow was your energy today?")
    energy = choose_one(ENERGY)

    # -Triggers
    print("\nDid any of these affect you today?")
    triggers = choose_multiple(TRIGGERS)

    # Environment
    print("\nWhat was your environment like?")
    environment = choose_one(ENVIRONMENT)

    # Behaviour according to the problem
    print(f"\nHow was your {selected_problem} behaviour today?")

    available_behaviours = BEHAVIOUR_OPTIONS.get(selected_problem)

    if not available_behaviours:
        print("No behaviour options found for this problem.")
        behaviour = "unknown"
    else:
        behaviour = choose_one(available_behaviours)

    # Time of day
    print("\nWhen was it strongest?")
    time_of_day = choose_one(["morning", "afternoon", "evening", "night"])

    # Builds the check in entry dictionary
    checkin_entry = {
        "date": datetime.now().date().isoformat(),
        "problem": selected_problem,
        "mood": mood,
        "energy": energy,
        "triggers": triggers,
        "environment": environment,
        "behaviour": behaviour,
        "time_of_day": time_of_day,
        "streak_broken": broken,
        "break_details": break_details
    }

    # Makes sure the list fields exist in memory before appending
    memory["daily_checkins"] = memory.get("daily_checkins", [])
    memory["streak_breaks"] = memory.get("streak_breaks", [])

    # Saves the check in to the full history
    memory["daily_checkins"].append(checkin_entry)

    # Logs it as a streak break entry if today was a bad day
    if broken:
        memory["streak_breaks"].append(checkin_entry)

    save_memory(memory)

    print("\nCheck-in saved!\n")

    return checkin_entry


# Test
if __name__ == "__main__":

    print("Test normal check-in:")
    run_daily_checkin(broken=False)

    print("\nTest streak break check-in:")
    run_daily_checkin(broken=True)