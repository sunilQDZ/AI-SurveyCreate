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


def get_domain_dynamic_radio_options(question_text: str = "", topic_hint: str = "") -> list:
    """
    Generates dynamic, industry and topic-tailored options for radio questions.
    Analyzes question text and topic keywords (e.g., E-commerce, Healthcare, Banking, Food, Education, Software, Travel).
    """
    q_lower = (question_text or "").lower()
    t_lower = (topic_hint or "").lower()
    combined = f"{q_lower} {t_lower}"

    # Try OpenAI dynamic option generation first
    try:
        from services.ai_service import generate_dynamic_radio_options_with_openai
        ai_opts = generate_dynamic_radio_options_with_openai(question_text, topic_hint)
        if ai_opts and isinstance(ai_opts, list) and len(ai_opts) >= 2:
            return ai_opts
    except Exception as e:
        print("[WARNING] AI option generation fallback to heuristic:", e)


    # E-commerce / Retail / Delivery / Product
    if any(k in combined for k in ["delivery", "shipping", "courier", "dispatch", "order"]):
        if "time" in q_lower or "how fast" in q_lower or "when" in q_lower:
            return ["Same day delivery", "1–2 business days", "3–5 business days", "More than a week"]
        return ["Home Delivery", "Store Pickup / Click & Collect", "Locker Pickup", "Express Shipping"]

    if any(k in combined for k in ["return", "refund", "exchange"]):
        return ["Defective / Damaged item", "Wrong size / color", "Item not as described", "Changed mind"]

    if any(k in combined for k in ["shop", "store", "buy", "purchase", "e-commerce", "ecommerce", "retail"]):
        if "channel" in q_lower or "where" in q_lower or "how did you" in q_lower:
            return ["Online Website", "Mobile App", "Physical Store", "Social Media Marketplace"]
        return ["Very convenient", "Moderately convenient", "Difficult", "Extremely difficult"]

    # Food / Restaurant / Café / Dining
    if any(k in combined for k in ["food", "restaurant", "cafe", "café", "dining", "meal", "order", "eat", "menu", "pizza", "burger"]):
        if "channel" in q_lower or "how" in q_lower or "order" in q_lower:
            return ["Dine-in", "Takeaway / Pickup", "Home Delivery", "Drive-thru"]
        if "time" in q_lower or "meal" in q_lower:
            return ["Breakfast", "Lunch", "Dinner", "Snack / Beverages"]
        return ["Food Taste & Quality", "Portion Size", "Packaging & Hygiene", "Delivery Speed"]

    # Healthcare / Hospital / Clinic / Medical
    if any(k in combined for k in ["health", "hospital", "clinic", "medical", "doctor", "patient", "nurse", "pharmacy"]):
        if "department" in q_lower or "who" in q_lower or "staff" in q_lower:
            return ["Doctor / Specialist", "Nursing Staff", "Reception / Front Desk", "Billing & Insurance"]
        if "type" in q_lower or "channel" in q_lower or "visit" in q_lower:
            return ["In-person Clinic Visit", "Telehealth / Video Consultation", "Emergency Room", "Pharmacy / Lab"]
        return ["Fully recovered", "Significantly improved", "No change", "Needs follow-up"]


    # Banking / Finance / Payments / Billing
    if any(k in combined for k in ["bank", "banking", "finance", "payment", "billing", "loan", "card", "atm", "account"]):
        if "channel" in q_lower or "how" in q_lower:
            return ["Mobile Banking App", "Online Web Portal", "ATM", "Branch Visit", "Phone Customer Care"]
        if "payment" in q_lower or "method" in q_lower:
            return ["Credit / Debit Card", "UPI / Instant Transfer", "Net Banking", "Cash on Delivery / Cash"]
        return ["Instant / Immediate", "Within 24 hours", "2–3 business days", "Delayed / Over 3 days"]

    # Education / Learning / Course / School / Student
    if any(k in combined for k in ["education", "school", "university", "college", "course", "learning", "student", "teacher"]):
        if "mode" in q_lower or "how" in q_lower:
            return ["Online / Remote", "In-person Classroom", "Hybrid / Blended Learning"]
        return ["Video Lectures", "Interactive Assignments", "Reading Materials", "Live Sessions / Webinars"]

    # Software / App / SaaS / Tech Support
    if any(k in combined for k in ["app", "software", "website", "system", "tech", "laptop", "repair", "device"]):
        if "device" in q_lower or "platform" in q_lower:
            return ["Mobile App (iOS/Android)", "Desktop / Laptop Web", "Tablet", "In-Store Kiosk"]
        if "issue" in q_lower or "problem" in q_lower:
            return ["Login / Password Issue", "Navigation / UI Confusion", "System Lag / Slow Speed", "Payment Error"]

    # Travel / Hotel / Stay / Transport
    if any(k in combined for k in ["hotel", "travel", "flight", "booking", "trip", "stay", "room"]):
        if "purpose" in q_lower or "type" in q_lower:
            return ["Business Trip", "Leisure / Vacation", "Family Trip", "Solo Travel"]
        return ["Direct Hotel Website", "Mobile App", "Third-party Agent (OTA)", "Walk-in Desk"]

    # Frequency questions across any industry
    if any(k in q_lower for k in ["how often", "frequency", "how frequently", "how many times"]):
        return ["Daily", "2–3 times a week", "Monthly", "Rarely / First time"]

    # Default Yes/No/Partially for direct binary questions
    if q_lower.startswith(("did ", "do ", "does ", "is ", "are ", "was ", "were ", "have ", "has ", "can ")):
        return ["Yes, completely", "Partially", "No, not at all"]

    # Fallback balanced industry single choice options
    return ["Exceeded expectations", "Met expectations", "Below expectations", "Uncertain"]


def enforce_survey_pattern(template: dict, topic_hint: str = "", default_max: int = 5) -> dict:
    """
    Enforces strict question pattern constraints on survey templates:
    1. Default template length is EXACTLY 5 questions (unless customized).
    2. First question MUST be NPS ('scale_type': 'nps').
    3. Last question MUST be Text ('scale_type': 'text').
    4. Exactly ONE NPS question per template (at index 0).
    5. Exactly ONE Text question per template (at the last index).
    6. Middle questions are a randomized, varied mix of scale types (rating, csat, ces, radio, mcq).
    7. Radio and MCQ options are dynamically generated based on industry topic & question intent.
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
                q_filler["options"] = get_domain_dynamic_radio_options(q_filler["question"], topic)
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
            if new_scale == "radio":
                q["options"] = get_domain_dynamic_radio_options(q.get("question", ""), topic)
            elif new_scale == "mcq" and not q.get("options"):
                q["options"] = ["Quality", "Speed", "Price", "Customer Support"]

    # Step 5: Final strict enforcement of Q0 and Q_last scale types
    questions[0]["scale_type"] = "nps"
    questions[-1]["scale_type"] = "text"

    # Step 6: Ensure radio/mcq options exist & apply dynamic industry options if generic
    generic_sets = [
        {"yes", "no", "not sure"},
        {"option 1", "option 2", "option 3"},
        {"yes", "no"}
    ]
    for q in questions:
        st = q.get("scale_type")
        if st == "radio":
            raw_opts = [str(o).strip() for o in q.get("options", []) if str(o).strip()]
            opts_set = set(o.lower() for o in raw_opts)
            if not raw_opts or opts_set in generic_sets:
                q["options"] = get_domain_dynamic_radio_options(q.get("question", ""), topic)
            else:
                q["options"] = raw_opts

        elif st == "mcq" and not q.get("options"):
            q["options"] = ["Quality & Features", "Speed & Performance", "Pricing & Value", "Customer Service"]

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
