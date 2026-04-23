"""
Test script for the voice assistant.
- Run with text input to simulate commands (no microphone needed).
- Optionally use --voice to test with real voice input.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def test_with_text():
    """Test assistant with predefined text commands (no mic)."""
    from assistant import load_model, predict_intent
    from intent_executor import execute_intent

    MODEL_DIR = BASE_DIR / "models"
    MODEL_PATH = MODEL_DIR / "intent_model.pkl"

    if not MODEL_PATH.exists():
        print("Run 'python train.py' first to create the model.")
        return

    pipe, le = load_model()

    def predict(text):
        return predict_intent(pipe, le, text)

    # Test cases: (user command, expected intent or None)
    test_commands = [
        "Can you tell me a joke?",
        "Tell me a joke",
        "What time is it?",
        "What is today's date?",
        "Open notepad",
        "Open calculator",
        "Open Chrome",
        "Hello",
        "Hi there",
        "Close notepad",
        "Tell me a quote",
        "Calculate 2 plus 2",
        "What's the weather",
        "Open YouTube",
        "Lock screen",
    ]

    print("=" * 60)
    print("  Voice Assistant – Text command tests")
    print("=" * 60)

    for cmd in test_commands:
        intent, conf = predict(cmd)
        response = execute_intent(intent, cmd) if intent else "No intent"
        print(f"\nInput:    {cmd}")
        print(f"Intent:   {intent} (confidence: {conf:.2f})")
        print(f"Response: {response}")
        print("-" * 60)

    print("\nInteractive mode: type a command and press Enter (or 'q' to quit).")
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input or user_input.lower() == "q":
            break
        intent, conf = predict(user_input)
        response = execute_intent(intent, user_input) if intent else "I didn't understand."
        print(f"Intent: {intent} ({conf:.2f})")
        print(f"Assistant: {response}")


def test_with_voice():
    """Run the full assistant with voice input (requires mic + pyttsx3 + SpeechRecognition)."""
    sys.argv = [sys.argv[0]]  # remove --voice so assistant uses mic
    from assistant import load_model, run_voice_loop
    pipe, le = load_model()
    run_voice_loop(pipe, le, use_voice_input=True)


if __name__ == "__main__":
    if "--voice" in sys.argv:
        test_with_voice()
    else:
        test_with_text()
