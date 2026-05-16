# Gublu User Setup and Starting Page
# This file is to start the user setup process at the welcome screen, where the user chooses their area of focus (procrastination, overspending, or isolation).
# The user also answers the quick setup survey, which is saved into the memory in a .json file.

from memory_manager import load_memory, save_memory

# Creating a list that stores the areas of focus available to the user
PROBLEMS = [
    "procrastination",
    "overspending",
    "isolation"
]

# Storing the survey questions for each problem type and possible answers in a dictionary
SURVEYS = {

    "procrastination": [
        ("What usually triggers it?", [
            "stress", "tiredness", "argument", "lack of sleep", "missed meal", "phone/social media"
        ]),
        ("When does it usually happen?", [
            "morning", "afternoon", "evening", "night"
        ])
    ],

    "overspending": [
        ("What triggers your spending?", [
            "stress", "boredom", "peer pressure", "sales/discounts", "online shopping"
        ]),
        ("When do you usually spend?", [
            "morning", "afternoon", "evening", "night"
        ])
    ],

    "isolation": [
        ("What triggers isolation?", [
            "low mood", "anxiety", "lack of energy", "social fear"
        ]),
        ("When does it usually happen?", [
            "morning", "afternoon", "evening", "night"
        ])
    ]
}

# Selecting the area of focus process
def choose_problem():
    memory = load_memory()
    print("\nSelect the problem you want to work on:\n")

    # Enumerating the list of areas of focus shown to the user
    for i, p in enumerate(PROBLEMS, 1):
        print(f"{i}. {p}")

    # Validating the user's input
    while True:
        choice = input("\nEnter number: ")

        # Checking if the input is within the range
        if choice.isdigit() and 1 <= int(choice) <= len(PROBLEMS):

            # Getting the selected problem from the PROBLEMS list
            selected = PROBLEMS[int(choice) - 1]

            # Saving the selected problem into the memory
            memory["chosen_problem"] = selected

            # Writing the updated memory back into the .json file
            save_memory(memory)

            # Showing confirmation to the user
            print(f"\nSelected problem: {selected}\n")

            # Returning the selected problem so it can be used in the survey
            return selected

        else:
            # Showing this if the user enters something invalid
            print("Invalid choice. Try again.")

# Setting up the survey
def run_survey(problem):
    memory = load_memory()
    questions = SURVEYS.get(problem, [])  # Getting the survey questions
    answers = {}

    print("\n--- Quick Setup Survey ---\n")

    # Looping through each question and its answer options
    for question, options in questions:

        print(question)

        # Showing each option with a number beside it
        for i, opt in enumerate(options, 1):
            print(f"{i}. {opt}")

        print("Select options separated by commas (e.g. 1,3):")  # Lets the user choose more than one option

        # Keeps asking until the user gives a valid answer
        while True:
            user_input = input("> ")  # Getting the user's selected option numbers

            try:
                # Splitting the user's input by commas and converting them into numbers
                indices = [int(x.strip()) for x in user_input.split(",")]

                # Matching the selected numbers to the actual option text
                selected_options = [
                    options[i - 1] for i in indices if 1 <= i <= len(options)
                ]

                if selected_options:
                    answers[question] = selected_options  # Saving answers under the question
                    break

                else:
                    # Showing this if the numbers were outside the valid option range
                    print("Invalid selection. Try again.")

            except:
                # Showing this if the input could not be converted into numbers
                print("Invalid input. Try again.")

        print()

    # Saving all survey answers into the memory
    memory["survey_answers"] = answers

    # Writing the updated memory back into the gublu_memory.json file
    save_memory(memory)

    # Showing confirmation of the completed survey
    print("Survey completed!\n")

    return answers


def run_initial_setup():
    # Loading memory to check if the user has already completed setup
    memory = load_memory()

    # If the user already chose a problem and answered the survey, the setup does not run again
    # Using .get() makes this safer if the memory keys do not exist yet
    if memory.get("chosen_problem") and memory.get("survey_answers"):
        print("Setup already completed.\n")
        return memory

    # Asking the user to choose their problem
    problem = choose_problem()

    # Running the correct survey for the chosen problem
    answers = run_survey(problem)

    # Showing the final setup confirmation
    print("Setup complete. You're ready to start.\n")

    # Returning the setup result as a dictionary
    return {
        "problem": problem,
        "survey": answers
    }

# Testing the setup file (only runs if the file is run specifically)
if __name__ == "__main__":
    run_initial_setup()