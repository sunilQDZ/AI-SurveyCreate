import json
import re


def extract_json_array(text: str):
    """
    Robust JSON array extractor from model output.
    """
    if not text:
        raise ValueError("Empty text received from model")

    # Clean markdown code blocks if present
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE).strip()

    # Try parsing cleaned text directly
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
    except Exception:
        pass

    # Fallback to regex matching
    m = re.search(r"\[\s*\{.*\}\s*\]", cleaned, re.DOTALL)
    if not m:
        m = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if not m:
        raise ValueError("No JSON array found in model response")

    raw_match = m.group().strip()
    try:
        return json.loads(raw_match)
    except Exception:
        # Try cleaning trailing commas before ] or }
        fixed = re.sub(r",\s*([\]}])", r"\1", raw_match)
        return json.loads(fixed)


def clamp_duration(duration: str | None) -> str:
    """
    Force duration within ~2–2.5 minutes.
    """
    if not duration:
        return "2–2.5 mins"
    d = duration.lower()
    if any(x in d for x in ["2–2.5", "2-2.5", "2 to 2.5"]):
        return duration
    return "2–2.5 mins"


def extract_requested_question_count(text: str) -> int | None:
    if not text:
        return None
    m = re.search(r"(\d+)\s*(?:questions?|q\b)", text, re.IGNORECASE)
    if m:
        try:
            val = int(m.group(1))
            if 1 <= val <= 20:
                return val
        except ValueError:
            pass
    words_map = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
    }
    m2 = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s*questions?", text, re.IGNORECASE)
    if m2:
        return words_map.get(m2.group(1).lower())
    return None


def truncate_text_display(text: str, max_chars: int = 35) -> str:
    """
    Truncate long user input text for UI warning messages (e.g. 35 chars max + '...').
    Prevents bloated UI error messages when users input long text/gibberish.
    """
    if not text:
        return ""
    clean = str(text).strip()
    if len(clean) <= max_chars:
        return clean
    return clean[:max_chars].strip() + "..."

