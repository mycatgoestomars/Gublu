# Stores the most recent conversation exchanges so the chatbot can remember what was said earlier
# This is separate from permanent journal entries

from datetime import datetime

# Keeps only the last 5 messages
MAX_HISTORY = 5

# In-memory list for the current session only
chat_history = []


def add_message(user, bot, emotions=None, distress=None, label=None, risk_level=None):
    # Adds a user and bot exchange to the short term chat history
    # Stores emotion analysis data alongside the text
    chat_history.append({
        "user":       user,
        "bot":        bot,
        "emotions":   emotions or {},
        "distress":   distress,
        "label":      label,
        "risk_level": risk_level,
        "timestamp":  datetime.now().isoformat()
    })

    # Throws away older messages to keep the history short
    if len(chat_history) > MAX_HISTORY:
        chat_history.pop(0)


def get_history_text():
    # Returns the session conversation history as a plain text string
    # Returns an empty string if nothing has been said yet
    if not chat_history:
        return ""

    history_text = "Recent conversation:\n"

    for item in chat_history:
        history_text += f"User: {item['user']}\n"
        history_text += f"Assistant: {item['bot']}\n"

    return history_text


def get_history_entries():
    # Returns the full list of enriched history dictionary entries
    return list(chat_history)


def clear_history():
    # Clears all messages from the session chat history
    global chat_history
    chat_history = []