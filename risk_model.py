# Uses a pre-trained toxicity classifier from Hugging Face to check if a user's message contains passive or indirect risk signals
# Acts as a backup safety check inside detect_risk in Gublu.py when a message contains soft warning phrases

from transformers import pipeline

# Loads the toxic-bert classifier from Hugging Face which classifies text as toxic or non-toxic and detects threats
risk_classifier = pipeline(
    "text-classification",
    model="unitary/toxic-bert"
)


def ml_risk_check(text):
    # Runs an ambiguous user message through the toxic-bert model to figure out if it carries a real risk signal
    # Returns high if it detects a threat with high confidence and low otherwise
    # Runs the text through the classifier
    classification = risk_classifier(text)[0]

    detected_label = classification["label"].lower()
    confidence_score = classification["score"]

    # Only flags it as high risk if the label is a danger category and the model is confident about it
    if detected_label in ["toxic", "severe_toxic", "threat"] and confidence_score > 0.6:
        return "high"

    return "low"