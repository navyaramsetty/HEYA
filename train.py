"""
train.py  ─  Waku Intent Model Trainer
=======================================
Reads intents.json, trains a TF-IDF + Logistic Regression classifier,
and saves intent_model.pkl ready for the launcher.

Run:
    python train.py
"""

import json
import pickle
import os
import sys

# ── auto-install scikit-learn if missing ──────────────────────────────────────
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import cross_val_score
    import numpy as np
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "scikit-learn", "-q"])
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import cross_val_score
    import numpy as np

# ── paths ─────────────────────────────────────────────────────────────────────
HERE         = os.path.dirname(os.path.abspath(__file__))
INTENTS_FILE = os.path.join(HERE, "intents.json")
MODEL_FILE   = os.path.join(HERE, "intent_model.pkl")


# ── load & flatten intents.json ───────────────────────────────────────────────
def load_data(path: str):
    """
    Supports two formats:
      1. [ [{"text":..,"label":..}, ..], .. ]   ← uploaded format (list of groups)
      2. {"intents": [{"tag":..,"patterns":[..]}, ..]}  ← standard format
    Returns (X, y) lists.
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    X, y = [], []

    if isinstance(raw, list):
        # Format 1: list of groups
        for group in raw:
            for item in group:
                if "text" in item and "label" in item:
                    X.append(item["text"].lower().strip())
                    y.append(item["label"].strip())

    elif isinstance(raw, dict) and "intents" in raw:
        # Format 2: standard intents.json
        for intent in raw["intents"]:
            for pattern in intent.get("patterns", []):
                X.append(pattern.lower().strip())
                y.append(intent["tag"].strip())

    return X, y


# ── train ─────────────────────────────────────────────────────────────────────
def train(X: list, y: list) -> Pipeline:
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 3),
            analyzer="char_wb",
            min_df=1,
        )),
        ("clf", LogisticRegression(
            max_iter=2000,
            C=10.0,
            solver="lbfgs",
        )),
    ])
    pipe.fit(X, y)
    return pipe


# ── evaluate ──────────────────────────────────────────────────────────────────
def evaluate(pipe: Pipeline, X: list, y: list) -> dict:
    preds  = pipe.predict(X)
    train_acc = sum(p == t for p, t in zip(preds, y)) / len(y) * 100

    label_counts = {}
    for label in y:
        label_counts[label] = label_counts.get(label, 0) + 1
    min_count = min(label_counts.values())

    cv_acc = None
    if min_count >= 2:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            splits = min(5, min_count)
            scores = cross_val_score(pipe, X, y, cv=splits, scoring="accuracy")
            cv_acc = (scores.mean() * 100, scores.std() * 100)

    return {"train_acc": train_acc, "cv_acc": cv_acc,
            "n_samples": len(X), "n_labels": len(set(y))}


# ── save ──────────────────────────────────────────────────────────────────────
def save(pipe: Pipeline, path: str):
    with open(path, "wb") as f:
        pickle.dump(pipe, f)


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  Waku Intent Model Trainer")
    print("=" * 55)

    if not os.path.exists(INTENTS_FILE):
        print(f"\n  ERROR: intents.json not found at:\n  {INTENTS_FILE}")
        sys.exit(1)

    print(f"\n  Loading  : {INTENTS_FILE}")
    X, y = load_data(INTENTS_FILE)
    labels = sorted(set(y))

    print(f"  Samples  : {len(X)}")
    print(f"  Labels   : {len(labels)}")

    print("\n  Training model...")
    pipe = train(X, y)

    print("  Evaluating...")
    stats = evaluate(pipe, X, y)
    print(f"  Train accuracy : {stats['train_acc']:.1f}%")
    if stats["cv_acc"]:
        print(f"  CV accuracy    : {stats['cv_acc'][0]:.1f}% ± {stats['cv_acc'][1]:.1f}%")

    save(pipe, MODEL_FILE)
    print(f"\n  Model saved → {MODEL_FILE}")

    print("\n  Sample predictions:")
    tests = [
        "play music",        "stop the music",     "next song please",
        "what time is it",   "open youtube",        "close chrome",
        "tell me a joke",    "take a screenshot",   "open vscode",
        "open calculator",   "open gmail",          "shutdown computer",
        "set a timer",       "translate this word", "tell me a quote",
    ]
    for t in tests:
        tag  = pipe.predict([t])[0]
        conf = max(pipe.predict_proba([t])[0]) * 100
        bar  = "█" * int(conf / 10) + "░" * (10 - int(conf / 10))
        print(f"    {bar} {conf:5.1f}%  '{t}' → {tag}")

    print("\n  All intents:")
    for i, lbl in enumerate(labels, 1):
        print(f"    {i:3}. {lbl}")

    print("\n  Training complete!")
    print("=" * 55)


if __name__ == "__main__":
    main()
