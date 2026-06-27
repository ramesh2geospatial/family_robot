import json
import os
from datetime import datetime


def format_time(iso_str):
    try:
        # Handle trailing Z or offset for python < 3.11
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso_str


def main():
    log_path = "data/conversations.jsonl"
    if not os.path.exists(log_path):
        print("No conversation logs found yet.")
        return

    print(f"\n=== RECENT CONVERSATIONS (from {log_path}) ===")
    print("=" * 60)
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            ts = format_time(entry.get("ts", ""))
            user = entry.get("user_id", "unknown")
            role = entry.get("user_role", "guest")
            speech_len = entry.get("audio_duration_s", 0.0)
            lang = entry.get("detected_language", "en")
            inp = entry.get("input_text", "")
            intent = entry.get("intent", "unknown")
            conf = entry.get("intent_confidence", 0.0)
            resp = entry.get("response_text", "")
            lat = entry.get("processing_time_s", 0.0)

            print(f"[{ts}] {user} ({role}) | Audio: {speech_len}s | Lang: {lang}")
            print(f'  User:   "{inp}"')
            print(f"  Intent:  {intent} (conf: {conf})")
            print(f'  Robot:  "{resp}"')
            print(f"  Latency: {lat}s | TTS: {entry.get('tts_engine', 'pyttsx3')}")
            print("-" * 60)


if __name__ == "__main__":
    main()
