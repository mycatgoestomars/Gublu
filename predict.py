# Loads a pre-trained ML model from Hugging Face to predict emotions from text
# Ignors love in the output because it isn't relevant to Gublu
# Returns a dictionary of emotion scores

from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

# The Hugging Face model name used for emotion classification
MODEL_NAME = "bhadresh-savani/distilbert-base-uncased-emotion"

# Loads the tokenizer and model from Hugging Face
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
emotion_model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

# Builds the text classification pipeline using the loaded model
# Setting top_k=None returns all emotion scores
emotion_classifier = pipeline(
    "text-classification",
    model=emotion_model,
    tokenizer=tokenizer,
    top_k=None
)


# Emotion prediction

def predict_emotions(text):
    # Takes a user's message and returns a dictionary of their emotion scores
    # Neutral is set to 0.0 because the model does not produce it
    # Runs the text through the classification pipeline
    raw_results = emotion_classifier(text)[0]

    emotion_scores = {}

    # Converts the model's list output into a clean dictionary
    for item in raw_results:
        emotion_label = item["label"].lower()
        score = float(item["score"])

        # Skips love since it's not relevant for Gublu
        if emotion_label != "love":
            emotion_scores[emotion_label] = score

    # Ensures all expected emotion keys are in the dictionary
    for emotion in ["sadness", "joy", "anger", "fear", "surprise"]:
        if emotion not in emotion_scores:
            emotion_scores[emotion] = 0.0

    # Sets neutral to 0.0 manually
    emotion_scores["neutral"] = 0.0

    return emotion_scores