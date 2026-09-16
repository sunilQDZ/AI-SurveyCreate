import random
from config import ALLOWED_SCALE_TYPES


def get_first_question_for_type(survey_type: str, topic_hint: str | None = None) -> dict:
    """
    First question + scale_type per survey type.
    NPS → 0–10 recommendation
    CSAT → 1–5 satisfaction
    CES → 1–5 ease/effort
    """
    topic = topic_hint or "your recent experience"

    if survey_type == "nps":
        return {
            "question": (
                f"On a scale of 0–10, how likely are you to recommend us to a friend or "
                f"colleague based on {topic}?"
            ),
            "scale_type": "nps"
        }
    if survey_type == "csat":
        return {
            "question": f"On a scale of 1–5, how satisfied are you with {topic}?",
            "scale_type": "csat"
        }
    if survey_type == "ces":
        return {
            "question": f"On a scale of 1–5, how easy was it for you to complete {topic}?",
            "scale_type": "ces"
        }

    return {
        "question": f"On a scale of 1–10, how satisfied are you with {topic}?",
        "scale_type": "rating"
    }


def infer_scale_type(question: str) -> str:
    """
    Infer *intent* of the question:
    - nps / csat / ces for numeric ratings
    - radio / mcq / matrix / file / text for others
    """
    q = (question or "").lower().strip()

    # ----- numeric rating intents -----
    if any(x in q for x in ["recommend", "likely to recommend", "nps"]):
        return "nps"
    if any(x in q for x in ["satisfied", "satisfaction", "rate your", "overall satisfaction"]):
        return "csat"
    if any(x in q for x in ["easy", "effort", "difficulty", "how easy"]):
        return "ces"

    # ----- yes/no / single choice -----
    if (q.startswith("did ") or q.startswith("do ") or q.startswith("does ") or
        q.startswith("is ") or q.startswith("are ") or q.startswith("was ") or
        "yes or no" in q or "yes/no" in q):
        return "radio"

    if any(x in q for x in ["which of the following", "choose one", "select one", "single best"]):
        return "radio"

    # ----- multiple choice -----
    if any(x in q for x in ["select all", "choose all", "multiple options", "check all that apply"]):
        return "mcq"

    # ----- matrix / comparison -----
    if any(x in q for x in ["rate the following", "rate each", "for each of the following", "across these"]):
        return "matrix"

    # ----- file upload -----
    if any(x in q for x in ["upload", "attach", "file", "document", "screenshot"]):
        return "file"

    return "text"


def normalize_template_scales(template: dict, forced_type: str):
    """
    Strict scale enforcement:
    - NPS → Only 'nps', 'radio', 'mcq', 'text','matrix' ,'file'
    - CSAT → Only 'csat', 'radio', 'mcq', 'text','matrix' ,'file'
    - CES → Only 'ces', 'radio', 'mcq', 'text','matrix' ,'file'
    - GENERAL → All ok
    """
    allowed_by_type = {
        "nps": ["nps", "radio", "mcq", "text", "matrix", "file"],
        "csat": ["csat", "radio", "mcq", "text", "matrix", "file"],
        "ces": ["ces", "radio", "mcq", "text", "matrix", "file"],
        "general": ALLOWED_SCALE_TYPES,
    }.get(forced_type, ALLOWED_SCALE_TYPES)

    for q in template.get("questions", []):
        inferred = infer_scale_type(q.get("question", ""))

        if inferred not in allowed_by_type:
            if forced_type == "nps":
                q["scale_type"] = "nps"
            elif forced_type == "csat":
                q["scale_type"] = "csat"
            elif forced_type == "ces":
                q["scale_type"] = "ces"
            else:
                q["scale_type"] = "text"
        else:
            q["scale_type"] = inferred

    return template


def enforce_survey_pattern(template: dict, topic_hint: str = "", default_max: int = 5) -> dict:
    """
    Enforces strict question pattern constraints on survey templates:
    1. Default template length is EXACTLY 5 questions (unless customized).
    2. First question MUST be NPS ('scale_type': 'nps').
    3. Last question MUST be Text ('scale_type': 'text').
    4. Exactly ONE NPS question per template (at index 0).
    5. Exactly ONE Text question per template (at the last index).
    6. Middle questions are a randomized, varied mix of scale types (rating, csat, ces, radio, mcq).
    """
    questions = template.get("questions", [])
    if not isinstance(questions, list):
        questions = []

    topic = topic_hint or "your recent experience"
    allowed_middle_scales = ["rating", "csat", "ces", "radio", "mcq"]

    target_count = max(2, default_max)

    # Step 1: Ensure question count matches target_count
    if len(questions) < target_count:
        while len(questions) < target_count:
            r_scale = random.choice(allowed_middle_scales)
            q_filler = {
                "question": f"How would you rate your overall experience with {topic}?",
                "scale_type": r_scale
            }
            if r_scale in ["radio", "mcq"]:
                q_filler["options"] = ["Very satisfied", "Satisfied", "Neutral", "Unsatisfied"]
            questions.append(q_filler)
    elif len(questions) > target_count:
        questions = questions[:target_count]

    # Step 2: Ensure Question 1 (index 0) is NPS
    standard_nps_q = {
        "question": f"On a scale of 0–10, how likely are you to recommend us to a friend or colleague based on {topic}?",
        "scale_type": "nps"
    }

    if questions[0].get("scale_type") == "nps":
        pass
    else:
        nps_idx = -1
        for i, q in enumerate(questions):
            if q.get("scale_type") == "nps":
                nps_idx = i
                break
        if nps_idx > 0:
            nps_q = questions.pop(nps_idx)
            questions.insert(0, nps_q)
        else:
            questions[0] = standard_nps_q

    # Step 3: Ensure Last Question (index -1) is Text
    standard_text_q = {
        "question": "What improvements or additional feedback do you have for us?",
        "scale_type": "text"
    }

    if questions[-1].get("scale_type") == "text":
        pass
    else:
        text_idx = -1
        for i in range(len(questions) - 1, 0, -1):
            if questions[i].get("scale_type") == "text":
                text_idx = i
                break
        if text_idx > 0:
            text_q = questions.pop(text_idx)
            questions.append(text_q)
        else:
            questions[-1] = standard_text_q

    # Step 4: Fix middle questions (index 1 to len-2) so NONE are 'nps' or 'text'
    for i in range(1, len(questions) - 1):
        q = questions[i]
        st = q.get("scale_type")

        if st in ["nps", "text"]:
            new_scale = random.choice(allowed_middle_scales)
            q["scale_type"] = new_scale
            if new_scale == "radio" and not q.get("options"):
                q["options"] = ["Yes", "No", "Not sure"]
            elif new_scale == "mcq" and not q.get("options"):
                q["options"] = ["Quality", "Speed", "Price", "Customer Service"]

    # Step 5: Final strict enforcement of Q0 and Q_last scale types
    questions[0]["scale_type"] = "nps"
    questions[-1]["scale_type"] = "text"

    # Step 6: Ensure radio/mcq options exist
    for q in questions:
        if q.get("scale_type") == "radio" and not q.get("options"):
            q["options"] = ["Yes", "No", "Not sure"]
        elif q.get("scale_type") == "mcq" and not q.get("options"):
            q["options"] = ["Option 1", "Option 2", "Option 3"]

    template["questions"] = questions
    return template


def build_fallback_templates(survey_type: str, user_input: str) -> list:
    """
    Production fallback template engine in case of OpenAI API limits or outages.
    """
    topic = user_input or "our services"
    st_upper = (survey_type or "general").upper()
    nps_q = {
        "question": f"On a scale of 0–10, how likely are you to recommend us to a friend or colleague based on {topic}?",
        "scale_type": "nps"
    }
    fallback_templates = [
        {
            "title": f"Quick {st_upper} Pulse Check - {topic.title()}",
            "purpose": f"Quick pulse check survey for {topic}",
            "duration": "2 mins",
            "questions": [
                nps_q,
                {"question": f"How clear and easy to understand was the information provided about {topic}?", "scale_type": "rating"},
                {"question": "Did you encounter any issues during your experience?", "scale_type": "radio", "options": ["Yes", "No", "Not sure"]},
                {"question": "How likely are you to continue using our services?", "scale_type": "rating"},
                {"question": "What improvements or suggestions do you have for us?", "scale_type": "text"}
            ]
        },
        {
            "title": f"Standard {st_upper} Survey - {topic.title()}",
            "purpose": f"Capture balanced feedback related to {topic}",
            "duration": "2–2.5 mins",
            "questions": [
                nps_q,
                {"question": "How satisfied are you with the overall speed and quality of service?", "scale_type": "csat"},
                {"question": "Were your expectations met during this interaction?", "scale_type": "radio", "options": ["Yes", "No", "Partially"]},
                {"question": "How easy was it to complete your transaction or request?", "scale_type": "ces"},
                {"question": "Please share any additional comments or ideas.", "scale_type": "text"}
            ]
        },
        {
            "title": f"Core {st_upper} Feedback - {topic.title()}",
            "purpose": f"Core evaluation survey for {topic}",
            "duration": "2 mins",
            "questions": [
                nps_q,
                {"question": "How would you rate the overall quality of service?", "scale_type": "rating"},
                {"question": "How satisfied are you with the support provided?", "scale_type": "csat"},
                {"question": "Which aspect of our service stood out most to you?", "scale_type": "mcq", "options": ["Quality", "Speed", "Reliability", "Support"]},
                {"question": "Is there anything specific we could do to improve your overall experience?", "scale_type": "text"}
            ]
        }
    ]
    return [enforce_survey_pattern(t, topic, default_max=5) for t in fallback_templates]
