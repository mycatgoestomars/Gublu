# Prepares the dataset for training
# Loads HuggingFace dataset, converts labels, merges emotions, remaps labels, encodes emotions, and saves clean CSV files
# Ensures no label mismatch and prevents training errors

# Imports libraries

from datasets import load_dataset
import pandas as pd
import os

# Loads dataset
dataset = load_dataset("dair-ai/emotion")

print("Dataset loaded")

# Original label map
label_map_original = {
    0: "sadness",
    1: "joy",
    2: "love",
    3: "anger",
    4: "fear",
    5: "surprise"
}

# Adds label names
def add_label_name(example):
    example["label_name"] = label_map_original[example["label"]]
    return example

dataset = dataset.map(add_label_name)

# Merges "love" into "joy"
def merge_labels(example):
    if example["label_name"] == "love":
        example["label_name"] = "joy"
    return example

dataset = dataset.map(merge_labels)

# Converts to Pandas DataFrame
train_df = dataset["train"].to_pandas()
val_df = dataset["validation"].to_pandas()
test_df = dataset["test"].to_pandas()

# Fixes label indices by redefining labels to be 0-4 only
# This prevents training errors like Target 5 is out of bounds
label_map_fixed = {
    "sadness": 0,
    "joy": 1,
    "anger": 2,
    "fear": 3,
    "surprise": 4
}

train_df["label"] = train_df["label_name"].map(label_map_fixed)
val_df["label"] = val_df["label_name"].map(label_map_fixed)
test_df["label"] = test_df["label_name"].map(label_map_fixed)

# Applies one hot encoding
def one_hot_encode(df):
    emotions = ["sadness", "joy", "anger", "fear", "surprise"]

    for emotion in emotions:
        df[emotion] = (df["label_name"] == emotion).astype(int)

    return df

train_df = one_hot_encode(train_df)
val_df = one_hot_encode(val_df)
test_df = one_hot_encode(test_df)

# Reorders columns
def reorder_columns(df):
    return df[
        [
            "text",
            "label",
            "label_name",
            "sadness",
            "joy",
            "anger",
            "fear",
            "surprise"
        ]
    ]

train_df = reorder_columns(train_df)
val_df = reorder_columns(val_df)
test_df = reorder_columns(test_df)

# Saves to local folder
base_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(base_dir, "Dataset Split")
os.makedirs(output_dir, exist_ok=True)
train_df.to_csv(os.path.join(output_dir, "train_emotion.csv"), index=False)
val_df.to_csv(os.path.join(output_dir, "val_emotion.csv"), index=False)
test_df.to_csv(os.path.join(output_dir, "test_emotion.csv"), index=False)

print("Datasets saved successfully")

# Verifies labels
print("Unique labels in train set:", sorted(train_df["label"].unique()))