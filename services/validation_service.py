import json
import re
import unicodedata
from config import client, OPENAI_MODEL


def is_off_topic_question(text: str) -> bool:
    clean = (text or "").strip().lower()
    if not clean:
        return False
    
    # If text contains survey keywords, it's NOT off-topic
    survey_keywords = [
        "survey", "feedback", "nps", "csat", "ces", "rating", "question",
        "template", "poll", "review", "score", "promoter", "detractor",
        "satisfaction", "touchpoint", "audience", "customer", "employee",
        "client", "user", "create", "make", "build", "generate"
    ]
    if any(k in clean for k in survey_keywords):
        return False

    # Common off-topic question patterns
    off_topic_patterns = [
        r"^(who|what|where|when|why|how)\s+(is|are|was|were|do|does|did|to|can|will|should)\b",
        r"\b(tell me|weather|capital|president|prime minister|code|script|recipe|sports|movie|song|game|joke|news)\b"
    ]
    for pat in off_topic_patterns:
        if re.search(pat, clean):
            return True
            
    return False


def is_greeting_input(text: str) -> bool:
    clean = (text or "").strip().lower()
    if not clean:
        return False
    greetings = {
        "hy", "hyy", "hyyy", "hi", "hii", "hiii", "hey", "heyy", "hello",
        "hola", "greetings", "good morning", "good afternoon", "good evening", "namaste"
    }
    if clean in greetings:
        return True
    if re.match(r"^(h[eyiai]+|hello|greetings|good\s+(morning|afternoon|evening))\b", clean):
        return True
    return False


def is_invalid_input_heuristic(text: str) -> bool:
    """
    Fast local safety fallback when AI API is unavailable.
    Checks structural invalidity (empty, symbols, single char repeat, pure digits, 4+ consonant smashes).
    """
    clean = (text or "").strip()
    if not clean:
        return True

    clean_norm = unicodedata.normalize("NFKD", clean).encode("ASCII", "ignore").decode("utf-8") or clean

    # Pure symbols or punctuation
    if re.match(r"^[\s\?\!\.\,\;\:\-\_\@\#\$\%\^\&\*\(\)\/\<\>\\\"\'\`\~\+\=\|\[\]\{\}]+$", clean_norm):
        return True
    # Single character repeated e.g. "aaaaa", "zzzzz"
    if len(set(clean_norm.lower())) == 1 and len(clean_norm) >= 3:
        return True
    # Pure numbers without context e.g. "123456"
    if clean_norm.isdigit():
        return True
    # Must contain at least 1 letter overall
    letters_all = re.sub(r"[^a-zA-Z]", "", clean_norm)
    if len(letters_all) < 1:
        return True

    words = clean_norm.lower().split()
    allowed_vowelless = {"rhythm", "lynx", "nymph", "slyly", "dryly", "wryly", "by", "my", "try", "fly", "sky", "why", "cry", "fry", "dry"}
    for w in words:
        letters_only = re.sub(r"[^a-z]", "", w)
        if not letters_only:
            continue
        # 4+ consecutive consonants in a single word e.g. "gfhdfjh", "sdgsdh", "segfhdfjh"
        if re.search(r"[bcdfghjklmnpqrstvwxz]{4,}", letters_only):
            return True
        # 4+ letters with no standard vowels
        if len(letters_only) >= 4 and not re.search(r"[aeiou]", letters_only) and letters_only not in allowed_vowelless:
            return True

    return False


def is_valid_input_ai(text: str) -> bool:
    """
    AI-powered validator using OpenAI to check if text is a meaningful,
    valid survey topic/requirement or response vs gibberish/nonsense/off-topic.
    Runs fast local structural heuristic check first.
    """
    clean = (text or "").strip()
    if not clean:
        return False

    # 1. Fast local checks (greetings, structural invalidity, off-topic)
    if is_greeting_input(clean):
        return False

    if is_invalid_input_heuristic(clean):
        return False

    # Normalize accented characters e.g. "Café" -> "Cafe"
    clean_norm = unicodedata.normalize("NFKD", clean).encode("ASCII", "ignore").decode("utf-8")
    if not clean_norm:
        clean_norm = clean

    # Fast local checks for pure symbols, single char repeat, or pure numbers
    if re.match(r"^[\s\?\!\.\,\;\:\-\_\@\#\$\%\^\&\*\(\)\/\<\>\\\"\'\`\~\+\=\|\[\]\{\}]+$", clean_norm):
        return False
    if len(set(clean_norm.lower())) == 1 and len(clean_norm) >= 3:
        return False
    if clean_norm.isdigit():
        return False
    letters_all = re.sub(r"[^a-zA-Z]", "", clean_norm)
    if len(letters_all) < 1:
        return False

    # AI validation via OpenAI
    prompt = f"""
Evaluate if the following user input is a MEANINGFUL, valid survey topic, requirement, or answer.

Return ONLY this JSON object:
{{"is_valid": true | false, "reason": "brief reason"}}

RULES FOR `is_valid`:
- Set `is_valid` to FALSE if the text is:
  1) Random keyboard smash, gibberish, or nonsense letters (e.g., "wer", "qwer", "fdfnhndfn", "sdgsdh", "asdfgh", "zxcvb", "qwerty").
  2) Completely off-topic question or statement (e.g., "What is the weather today?", "Who is the president", "Tell me a joke").
  3) Meaningless random character sequences or non-words.

- Set `is_valid` to TRUE if the text is:
  1) A meaningful survey domain topic, requirement, or concept (e.g., "Customer satisfaction", "Mobile app experience", "Café feedback", "Store visit", "Education department").
  2) Valid domain short words, acronyms, or common terms (e.g., "nps", "csat", "ces", "app", "web", "pay", "tax", "cx", "ux", "ui", "b2b", "food", "help", "work", "store", "chat", "call").
  3) Any survey refinement or customization instruction (e.g., "i want 7 questions", "add questions about price", "make it shorter", "focus on customer support", "change middle questions").


User Input:
\"\"\"{clean}\"\"\"
"""
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            timeout=8,
            messages=[
                {"role": "system", "content": "You evaluate input validity for a survey builder application. Respond with strict JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=100
        )
        content = resp.choices[0].message.content.strip()
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            data = json.loads(m.group())
            return bool(data.get("is_valid", False))
    except Exception as e:
        print("[WARNING] AI input validation API call failed/timed out, using heuristic fallback:", e)

    # Fallback to local heuristic if API fails/timeouts
    return not is_invalid_input_heuristic(clean)


def is_invalid_input(text: str) -> bool:
    return not is_valid_input_ai(text)
