import re
from datetime import datetime
from flask import Blueprint, request, jsonify

from config import client, OPENAI_MODEL, ALLOWED_SCALE_TYPES
from utils.text_helpers import extract_json_array, extract_requested_question_count, clamp_duration, truncate_text_display
from services.validation_service import (
    is_greeting_input, is_invalid_input, is_valid_input_ai, is_off_topic_question
)
from services.template_engine import (
    enforce_survey_pattern, build_fallback_templates, infer_scale_type
)
from services.ai_service import analyze_user_input_with_openai
from services.storage_service import save_history, save_finalized_template

survey_bp = Blueprint("survey", __name__)


def extract_request_payload(req) -> dict:
    """
    Safely extract JSON body, URL query string arguments, or form data from request.
    Always guarantees returning a python dict regardless of method or content-type.
    """
    payload = {}
    if req.is_json:
        data = req.get_json(force=True, silent=True)
        if isinstance(data, dict):
            payload.update(data)
    if req.args:
        payload.update(req.args.to_dict())
    if req.form:
        payload.update(req.form.to_dict())
    return payload


def sanitize_string(val, default: str = "") -> str:
    """
    Enforces string data type and strips surrounding whitespace.
    Safely handles None, int, float, bool, list, dict without crashing.
    """
    if val is None:
        return default
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, (int, float, bool)):
        return str(val).strip()
    return default


# ---------- VALIDATE INPUT ----------
@survey_bp.route("/validate_input", methods=["GET", "POST"])
def validate_input():
    data = extract_request_payload(request)
    text = (
        sanitize_string(data.get("text"))
        or sanitize_string(data.get("user_input"))
        or sanitize_string(data.get("user_prompt"))
        or sanitize_string(data.get("answer"))
        or sanitize_string(data.get("prompt"))
        or sanitize_string(data.get("topic"))
        or sanitize_string(data.get("input"))
    )
    question_id = (
        sanitize_string(data.get("question_id"))
        or sanitize_string(data.get("field_type"))
    ).lower()

    if not text:
        return jsonify({
            "is_valid": False,
            "input": "",
            "message": "⚠️ Input cannot be empty. Please provide a valid response.",
            "question": None,
            "options": []
        }), 400

    display_text = truncate_text_display(text)
    is_greeting = is_greeting_input(text)
    is_invalid = not is_valid_input_ai(text) or is_off_topic_question(text)

    if question_id == "survey_type":
        low = text.lower()
        valid_types = ["nps", "csat", "ces", "general", "not sure"]
        mapped = any(t in low for t in valid_types) or not is_invalid
        if is_greeting or not mapped:
            msg = f"⚠️ \"{display_text}\" is a greeting." if is_greeting else f"⚠️ \"{display_text}\" is not a valid survey type."
            return jsonify({
                "is_valid": False,
                "input": text,
                "message": f"{msg} Please choose one of the options below (NPS, CSAT, CES, General) or type a valid requirement.",
                "question": "Which type of survey would you like to create?",
                "options": ["NPS", "CSAT", "CES", "General / Not sure"]
            })

    elif question_id == "audience":
        if is_greeting or is_invalid:
            msg = f"⚠️ \"{display_text}\" is a greeting." if is_greeting else f"⚠️ \"{display_text}\" is not a valid target audience."
            return jsonify({
                "is_valid": False,
                "input": text,
                "message": f"{msg} Please select an option below or type a valid audience (e.g., Customers, Employees, Students).",
                "question": "Who is your target audience for this survey?",
                "options": ["Customers", "Employees", "B2B", "Clients", "Users", "Learners", "Vendors", "Parents", "General users"]
            })

    elif question_id == "purpose":
        if is_greeting or is_invalid:
            msg = f"⚠️ \"{display_text}\" is a greeting." if is_greeting else f"⚠️ \"{display_text}\" is not a valid survey purpose."
            return jsonify({
                "is_valid": False,
                "input": text,
                "message": f"{msg} Please enter a clear survey topic or purpose (e.g., Customer Satisfaction, Service Feedback).",
                "question": "What is the main topic or purpose of this survey?",
                "options": []
            })

    elif question_id == "touchpoint":
        if is_greeting or is_invalid:
            msg = f"⚠️ \"{display_text}\" is a greeting." if is_greeting else f"⚠️ \"{display_text}\" is not a valid touchpoint."
            return jsonify({
                "is_valid": False,
                "input": text,
                "message": f"{msg} Please select an option below or enter a valid channel (e.g., Website, Mobile App, Store Visit).",
                "question": "Which touchpoint or channel is this survey primarily about?",
                "options": ["Website", "Mobile app", "Store visit / Branch visit", "Call center / Phone support", "Email support", "WhatsApp / Chat support", "Delivery experience", "Onboarding / Signup flow", "Billing & payments", "Other"]
            })

    if is_greeting:
        return jsonify({
            "is_valid": False,
            "input": text,
            "message": f"⚠️ \"{display_text}\" is a greeting. Please enter a specific survey requirement or topic.",
            "question": None,
            "options": []
        })

    is_valid = not is_invalid
    return jsonify({
        "is_valid": is_valid,
        "input": text,
        "message": None if is_valid else f"⚠️ \"{display_text}\" is not a valid survey topic or requirement. Please enter a meaningful input.",
        "question": None,
        "options": []
    })



# ---------- GENERATE QUESTION FLOW ----------
@survey_bp.route("/generate_question_flow", methods=["GET", "POST"])
def generate_question_flow():
    data = extract_request_payload(request)
    user_input = (
        sanitize_string(data.get("user_input"))
        or sanitize_string(data.get("user_prompt"))
        or sanitize_string(data.get("prompt"))
        or sanitize_string(data.get("text"))
        or sanitize_string(data.get("topic"))
        or sanitize_string(data.get("input"))
    )

    if is_greeting_input(user_input):
        question_flow = [
            {
                "id": "survey_type",
                "q": "Which type of survey would you like to create?",
                "options": ["NPS", "CSAT", "CES", "General / Not sure"]
            },
            {
                "id": "audience",
                "q": "Who is your target audience for this survey?",
                "options": ["Customers", "Employees", "B2B", "Clients", "Users", "Learners", "Vendors", "Parents", "General users"]
            },
            {
                "id": "purpose",
                "q": "What is the main topic or purpose of this survey?",
                "options": ["Customer Feedback", "Product Quality", "Service & Support", "Overall Experience", "Pricing & Value", "Other"],
                "allow_text_input": True
            },
            {
                "id": "touchpoint",
                "q": "Which touchpoint or channel is this survey primarily about?",
                "options": ["Website", "Mobile app", "Store visit / Branch visit", "Call center / Phone support", "Email support", "WhatsApp / Chat support", "Delivery experience", "Onboarding / Signup flow", "Billing & payments", "Other"],
                "allow_text_input": True
            }
        ]
        return jsonify({
            "is_greeting": True,
            "greeting_message": "👋 Hello! Welcome to Smart Survey Creator. Choose your survey details below or enter your survey idea to get started.",
            "all_detected": False,
            "skip_questions": False,
            "question_flow": question_flow,
            "detected_survey_type": None,
            "detected_audience": None,
            "detected_purpose": None,
            "detected_touchpoint": None,
            "original_user_input": user_input
        })

    if is_off_topic_question(user_input) or not is_valid_input_ai(user_input):
        question_flow = [
            {
                "id": "survey_type",
                "q": "Which type of survey would you like to create?",
                "options": ["NPS", "CSAT", "CES", "General / Not sure"]
            }
        ]
        display_input = truncate_text_display(user_input)
        return jsonify({
            "is_invalid": True,
            "invalid_message": f"⚠️ \"{display_input}\" is not a valid survey topic or requirement. Please provide a clear survey requirement (e.g., Customer Satisfaction, Laptop Repair, Mobile App Experience).",
            "all_detected": False,
            "skip_questions": False,
            "question_flow": question_flow,
            "detected_survey_type": None,
            "detected_audience": None,
            "detected_purpose": None,
            "detected_touchpoint": None,
            "original_user_input": user_input
        })


    requested_type_raw = (data.get("survey_type") or "").strip().lower()
    audience_from_payload = (data.get("audience") or "").strip()
    purpose_from_payload = (data.get("purpose") or "").strip()
    touchpoint_from_payload = (data.get("touchpoint") or "").strip()

    ai_result = analyze_user_input_with_openai(user_input) if user_input else {
        "survey_type": None,
        "audience": None,
        "purpose": None,
        "touchpoint": None,
        "audience_suggestion": None,
        "touchpoint_suggestion": None
    }

    ai_survey_type = ai_result.get("survey_type")
    ai_audience = ai_result.get("audience")
    ai_purpose = ai_result.get("purpose")
    ai_touchpoint = ai_result.get("touchpoint")
    ai_audience_suggestion = ai_result.get("audience_suggestion")
    ai_touchpoint_suggestion = ai_result.get("touchpoint_suggestion")

    survey_type = requested_type_raw if requested_type_raw in ["nps", "csat", "ces", "general"] else ai_survey_type
    audience = audience_from_payload or ai_audience
    purpose = purpose_from_payload or ai_purpose
    touchpoint = touchpoint_from_payload or ai_touchpoint

    if is_greeting_input(audience) or is_invalid_input(audience):
        audience = None
    if is_greeting_input(purpose) or is_invalid_input(purpose):
        purpose = None
    if is_greeting_input(touchpoint) or is_invalid_input(touchpoint):
        touchpoint = None

    all_detected = bool(survey_type and audience and purpose and touchpoint)

    summary_parts = []
    if survey_type:
        summary_parts.append(f"• <b>Survey Type:</b> {survey_type.upper()}")
    if audience:
        summary_parts.append(f"• <b>Target Audience:</b> {audience}")
    if purpose:
        summary_parts.append(f"• <b>Survey Purpose:</b> {purpose}")
    if touchpoint:
        summary_parts.append(f"• <b>Touchpoint / Channel:</b> {touchpoint}")

    summary_text = "<br>".join(summary_parts) if summary_parts else ""

    question_flow = []

    if not survey_type:
        question_flow.append({
            "id": "survey_type",
            "q": "Which type of survey would you like to create?",
            "options": ["NPS", "CSAT", "CES", "General / Not sure"]
        })

    if not audience:
        aud_q = {
            "id": "audience",
            "q": "Who is your target audience for this survey?",
            "options": ["Customers", "Employees", "B2B", "Clients", "Users", "Learners", "Vendors", "Parents", "General users"]
        }
        if ai_audience_suggestion and ai_audience_suggestion not in aud_q["options"]:
            aud_q["options"].insert(0, ai_audience_suggestion)
        question_flow.append(aud_q)

    if not purpose:
        question_flow.append({
            "id": "purpose",
            "q": "What is the main topic or purpose of this survey?",
            "options": ["Customer Feedback", "Product Quality", "Service & Support", "Overall Experience", "Pricing & Value", "Other"],
            "allow_text_input": True
        })

    if not touchpoint:
        touch_q = {
            "id": "touchpoint",
            "q": "Which touchpoint or channel is this survey primarily about?",
            "options": ["Website", "Mobile app", "Store visit / Branch visit", "Call center / Phone support", "Email support", "WhatsApp / Chat support", "Delivery experience", "Onboarding / Signup flow", "Billing & payments", "Other"],
            "allow_text_input": True
        }
        if ai_touchpoint_suggestion and ai_touchpoint_suggestion not in touch_q["options"]:
            touch_q["options"].insert(0, ai_touchpoint_suggestion)
        question_flow.append(touch_q)

    return jsonify({
        "all_detected": all_detected,
        "skip_questions": all_detected,
        "summary_text": summary_text,
        "question_flow": question_flow,
        "detected_survey_type": survey_type,
        "detected_audience": audience,
        "detected_purpose": purpose,
        "detected_touchpoint": touchpoint,
        "original_user_input": user_input
    })


# ---------- GENERATE SURVEY ----------
@survey_bp.route("/generate_survey", methods=["GET", "POST"])
def generate_survey():
    data = extract_request_payload(request)
    user_input = (
        sanitize_string(data.get("user_input"))
        or sanitize_string(data.get("user_prompt"))
        or sanitize_string(data.get("prompt"))
        or sanitize_string(data.get("text"))
        or sanitize_string(data.get("topic"))
        or sanitize_string(data.get("input"))
    )
    requested_type_raw = sanitize_string(data.get("survey_type")).lower()

    raw_answers = data.get("answers")
    if isinstance(raw_answers, str):
        try:
            import json
            raw_answers = json.loads(raw_answers)
        except Exception:
            raw_answers = {}
    answers = raw_answers if isinstance(raw_answers, dict) else {}

    purpose = (
        sanitize_string(data.get("target_purpose"))
        or sanitize_string(data.get("survey_purpose"))
        or sanitize_string(answers.get("purpose"))
    )
    touchpoint = (
        sanitize_string(data.get("touchpoint"))
        or sanitize_string(answers.get("touchpoint"))
    )
    audience = (
        sanitize_string(data.get("target_audience"))
        or sanitize_string(data.get("audience"))
        or sanitize_string(answers.get("audience"))
    )

    if is_greeting_input(purpose) or is_invalid_input(purpose):
        purpose = ""
    if is_greeting_input(touchpoint) or is_invalid_input(touchpoint):
        touchpoint = ""
    if is_greeting_input(audience) or is_invalid_input(audience):
        audience = ""

    display_input = truncate_text_display(user_input)
    if (not user_input or is_greeting_input(user_input) or is_invalid_input(user_input)) and not (purpose or touchpoint or audience):
        if is_greeting_input(user_input):
            return jsonify({
                "error": "Invalid input",
                "message": f"⚠️ \"{display_input}\" is a greeting. Please enter a specific survey topic or requirement."
            }), 400
        elif user_input and is_invalid_input(user_input):
            return jsonify({
                "error": "Invalid input",
                "message": f"⚠️ \"{display_input}\" is not a valid survey topic or requirement. Please enter a clear requirement (e.g., Customer Satisfaction, Laptop Repair, Pricing)."
            }), 400


        else:
            return jsonify({
                "error": "Missing user_input",
                "message": "⚠️ Please select an option or specify a valid survey topic, purpose, or target audience to generate survey templates."
            }), 400

    if is_greeting_input(user_input) or is_invalid_input(user_input) or (purpose or touchpoint or audience):
        topic_parts = []
        if purpose:
            topic_parts.append(purpose)
        if touchpoint:
            topic_parts.append(f"for {touchpoint}")
        if audience:
            topic_parts.append(f"targeting {audience}")
        topic = " ".join(topic_parts) if topic_parts else "Customer Feedback & Satisfaction"
    else:
        topic = user_input

    survey_type = None
    if requested_type_raw in ["nps", "csat", "ces", "general"]:
        survey_type = requested_type_raw
    else:
        ai_result = analyze_user_input_with_openai(topic)
        ai_type = ai_result.get("survey_type")
        if ai_type in ["nps", "csat", "ces", "general"]:
            survey_type = ai_type
        else:
            survey_type = "general"

    req_count = extract_requested_question_count(user_input) or extract_requested_question_count(topic) or 5
    processed_templates = []

    prompt = f"""
You are an elite CX and Market Research AI Expert.
Generate 3 distinct, highly tailored survey templates for the topic: "{topic}"
Target Survey Category: "{survey_type.upper()} Survey Template".

RULES & STRUCTURE:
- STRICT JSON array ONLY (no markdown fences, no conversational text).
- Each template object MUST have: "title", "purpose", "duration", "questions".
- "duration" MUST be around 2–2.5 minutes (e.g., "2–2.5 mins").
- QUESTION COUNT RULE: Each template MUST contain EXACTLY {req_count} domain-specific, actionable questions (Q1 = NPS, middle questions = feedback scales, Q{req_count} = Text).

QUESTION PATTERN RULES (MANDATORY):
1. FIRST question (Position 1): MUST be an NPS recommendation scale ("scale_type": "nps", 0–10 scale).
2. LAST question (Final Position): MUST be an open-ended feedback question ("scale_type": "text").
3. Template MUST contain EXACTLY ONE NPS question (at Position 1).
4. Template MUST contain EXACTLY ONE Text question (at Final Position).
5. Middle questions (Positions 2 to len-1): MUST be a randomized, varied mix of scale types selected from ["rating", "csat", "ces", "radio", "mcq", "matrix"]. DO NOT use "nps" or "text" in middle questions.

QUESTION FORMAT:
- Each question object must have:
    - "question": clear, relevant question text tailored to "{topic}"
    - "scale_type": one of ["nps","csat","ces","rating","text","radio","mcq","matrix","file"]
- For any question with "scale_type": "radio" or "mcq", include an "options" array of realistic choices.
- Avoid duplicate question intent within a single template.
"""

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            timeout=15,
            messages=[
                {"role": "system", "content": "You are an elite CX Survey AI Architect. Output a valid JSON array of templates ONLY. No explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=1500
        )
        text = resp.choices[0].message.content
        try:
            templates = extract_json_array(text)
        except Exception as e:
            print("[WARNING] extract_json_array failed:", e)
            templates = []
    except Exception as e:
        print("Generate survey error:", e)
        templates = []

    if not templates:
        print("[WARNING] OpenAI template generation returned empty or failed. Using fallback template engine.")
        templates = build_fallback_templates(survey_type, topic)

    for t in templates:
        t.setdefault("title", f"{survey_type.upper()} Survey Template")
        t.setdefault("purpose", f"Capture responses related to {user_input}")
        t["duration"] = clamp_duration(t.get("duration"))
        t.setdefault("questions", [])

        cleaned_questions = []
        for q in t["questions"]:
            if isinstance(q, str):
                question_text = q.strip()
                raw_options = []
            else:
                question_text = (q.get("question") or q.get("text") or q.get("label") or "").strip()
                raw_options = q.get("options") or []

            if not question_text:
                continue

            options_clean = []
            if isinstance(raw_options, list):
                for o in raw_options:
                    s = str(o).strip()
                    if s:
                        options_clean.append(s)

            detected = infer_scale_type(question_text)
            scale = detected if detected in ALLOWED_SCALE_TYPES else "rating"

            q_obj = {
                "question": question_text,
                "scale_type": scale
            }

            if scale == "radio":
                q_obj["options"] = options_clean if options_clean else ["Yes", "No", "Not sure"]
            if scale == "mcq" and options_clean:
                q_obj["options"] = options_clean

            cleaned_questions.append(q_obj)

        t["questions"] = cleaned_questions
        processed_templates.append(t)

    processed_templates = [
        enforce_survey_pattern(t, topic_hint=topic, default_max=req_count)
        for t in processed_templates
    ]

    save_history({
        "timestamp": datetime.now().isoformat(),
        "input": user_input,
        "survey_type": survey_type,
        "templates": processed_templates
    })

    return jsonify({
        "surveys": processed_templates,
        "templates": processed_templates,
        "detected_survey_type": survey_type
    })


# ---------- GENERATE MORE ----------
@survey_bp.route("/generate_more_surveys", methods=["GET", "POST"])
def generate_more_surveys():
    data = extract_request_payload(request)
    focus_area = (
        sanitize_string(data.get("focus_area"))
        or sanitize_string(data.get("user_input"))
        or sanitize_string(data.get("prompt"))
        or sanitize_string(data.get("refinement"))
    )

    if not focus_area:
        return jsonify({"error": "Missing focus_area", "message": "⚠️ Please enter a focus area for generating more survey variations."}), 400

    display_focus = truncate_text_display(focus_area)
    if is_greeting_input(focus_area):
        return jsonify({"error": "Invalid focus_area", "message": f"⚠️ \"{display_focus}\" is a greeting. Please enter a specific focus area or requirement (e.g., Customer Satisfaction, Pricing)."}), 400

    if not is_valid_input_ai(focus_area) or is_off_topic_question(focus_area):
        return jsonify({"error": "Invalid focus_area", "message": f"⚠️ \"{display_focus}\" is not a valid focus area. Please enter a clear requirement (e.g., Customer Satisfaction, 7 questions, Pricing)."}), 400



    ctx = data.get("context")
    if isinstance(ctx, str):
        try:
            import json
            ctx = json.loads(ctx)
        except Exception:
            ctx = {}
    if not isinstance(ctx, dict):
        ctx = {}

    original_user_input = (ctx.get("original_user_input") or "").strip()
    detected_survey_type = (ctx.get("detected_survey_type") or "").strip()
    detected_audience = (ctx.get("detected_audience") or "").strip()
    detected_purpose = (ctx.get("detected_purpose") or "").strip()
    detected_touchpoint = (ctx.get("detected_touchpoint") or "").strip()


    if not ctx or not original_user_input:
        ai_re = analyze_user_input_with_openai(focus_area)
        original_user_input = original_user_input or focus_area
        detected_survey_type = detected_survey_type or ai_re.get("survey_type") or "general"
        detected_audience = detected_audience or ai_re.get("audience") or ""
        detected_purpose = detected_purpose or ai_re.get("purpose") or ""
        detected_touchpoint = detected_touchpoint or ai_re.get("touchpoint") or ""

    survey_type = (data.get("survey_type") or "").strip().lower()
    if survey_type not in ["nps", "csat", "ces", "general"]:
        survey_type = (detected_survey_type or "general").lower()

    topic_parts = []
    if detected_purpose:
        topic_parts.append(detected_purpose)
    if detected_touchpoint:
        topic_parts.append(f"for {detected_touchpoint}")
    if detected_audience:
        topic_parts.append(f"targeting {detected_audience}")

    base_topic = " ".join(topic_parts) if topic_parts else original_user_input

    req_count = (
        extract_requested_question_count(focus_area)
        or extract_requested_question_count(original_user_input)
        or 5
    )

    prompt = f"""
You are an elite CX Survey AI Specialist.

CONTEXT FROM FIRST GENERATION:
- Main Survey Topic: "{base_topic}"
- Target Survey Category: "{survey_type.upper()} Survey Template"
- Target Audience: "{detected_audience or 'N/A'}"
- Primary Touchpoint: "{detected_touchpoint or 'N/A'}"

NEW FOCUS AREA / REFINEMENT INSTRUCTION:
"{focus_area}"

YOUR TASK:
Generate 3 distinct, high-quality survey templates that:
1. Maintain the overall survey category ({survey_type.upper()}).
2. Focus specifically on the requested focus area: "{focus_area}".
3. Keep questions relevant to the target audience ({detected_audience}) and touchpoint ({detected_touchpoint}).

QUESTION PATTERN RULES (MANDATORY):
1. FIRST question (Position 1): MUST be an NPS recommendation scale ("scale_type": "nps", 0–10 scale).
2. LAST question (Final Position): MUST be an open-ended feedback question ("scale_type": "text").
3. Template MUST contain EXACTLY ONE NPS question (at Position 1).
4. Template MUST contain EXACTLY ONE Text question (at Final Position).
5. Middle questions (Positions 2 to len-1): MUST be a randomized, varied mix of scale types selected from ["rating", "csat", "ces", "radio", "mcq", "matrix"]. DO NOT use "nps" or "text" in middle questions.

OUTPUT FORMAT:
- Output a STRICT JSON array ONLY of 3 template objects.
- Each template object MUST have:
  - "title": descriptive title including the focus area (e.g. "{survey_type.upper()} Survey - {focus_area.title()}")
  - "purpose": clear description of what this template evaluates
  - "duration": "2–2.5 mins"
  - "questions": array of EXACTLY {req_count} question objects:
      - "question": clear text
      - "scale_type": one of ["nps","csat","ces","rating","text","radio","mcq","matrix","file"]
      - "options": list of choices for radio/mcq types
"""

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            timeout=15,
            messages=[
                {"role": "system", "content": "You are a CX Survey AI Architect. Respond with a strict JSON array of templates ONLY."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=1500
        )
        text = resp.choices[0].message.content
        try:
            templates = extract_json_array(text)
        except Exception as ex:
            print("[ERROR] extract_json_array failed in generate_more_surveys:", ex)
            templates = []
    except Exception as e:
        print("[ERROR] OpenAI generate_more_surveys call failed:", e)
        templates = []

    if not templates:
        print("[WARNING] Using fallback template engine for generate_more_surveys.")
        templates = build_fallback_templates(survey_type, focus_area or original_user_input)

    templates = [
        enforce_survey_pattern(t, topic_hint=focus_area or original_user_input, default_max=req_count)
        for t in templates
    ]

    for t in templates:
        t["duration"] = clamp_duration(t.get("duration"))

    return jsonify({
        "surveys": templates,
        "templates": templates,
        "focus_area": focus_area,
        "survey_type": survey_type,
        "context_used": ctx
    })


# ---------- CUSTOMIZE SELECTED TEMPLATE ----------
@survey_bp.route("/customize_selected_template", methods=["GET", "POST"])
def customize_selected_template():
    data = extract_request_payload(request)
    templates = data.get("templates")
    if isinstance(templates, str):
        try:
            import json
            templates = json.loads(templates)
        except Exception:
            templates = []
    if not isinstance(templates, list):
        templates = []

    choice = sanitize_string(data.get("choice")).lower()
    action = sanitize_string(data.get("action")).lower()
    focus_area = sanitize_string(data.get("focus_area"))
    complexity = sanitize_string(data.get("complexity"))
    scale_action = sanitize_string(data.get("scale_action")).lower()

    raw_scale_changes = data.get("scale_changes")
    if isinstance(raw_scale_changes, str):
        try:
            import json
            raw_scale_changes = json.loads(raw_scale_changes)
        except Exception:
            raw_scale_changes = {}
    scale_changes = raw_scale_changes if isinstance(raw_scale_changes, dict) else {}
    remove_input = sanitize_string(data.get("remove_input"))

    if focus_area:
        display_focus = truncate_text_display(focus_area)
        if is_greeting_input(focus_area):
            return jsonify({"error": "Invalid focus_area", "message": f"⚠️ \"{display_focus}\" is a greeting. Please enter a specific focus area or requirement (e.g., Customer Satisfaction, Pricing)."}), 400

        if not is_valid_input_ai(focus_area) or is_off_topic_question(focus_area):
            return jsonify({"error": "Invalid focus_area", "message": f"⚠️ \"{display_focus}\" is not a valid focus area. Please enter a clear requirement (e.g., Customer Satisfaction, 7 questions, Pricing)."}), 400




    if not templates or not choice:
        return jsonify({"error": "Missing 'templates' or 'choice'.", "message": "⚠️ Please select a template first to customize."}), 400

    try:
        match = re.search(r"\d+", choice)
        if not match:
            return jsonify({"error": "Invalid template choice format.", "message": "⚠️ Please select a valid template choice (e.g. Template 1)."}), 400
        index = int(match.group()) - 1
        if index < 0 or index >= len(templates):
            return jsonify({"error": "Template choice out of bounds.", "message": f"⚠️ Template choice '{choice}' is out of bounds. Please select a valid template choice."}), 400
        selected = templates[index]
    except Exception:
        return jsonify({"error": "Invalid template choice format.", "message": "⚠️ Please select a valid template choice."}), 400


    if not selected or not isinstance(selected, dict):
        return jsonify({"error": "Invalid template format.", "message": "⚠️ Invalid template format."}), 400

    questions = selected.get("questions", [])
    title = selected.get("title", "General Feedback")

    custom_title = data.get("title")
    if custom_title and isinstance(custom_title, str):
        selected["title"] = custom_title.strip()

    custom_purpose = data.get("purpose")
    if custom_purpose and isinstance(custom_purpose, str):
        selected["purpose"] = custom_purpose.strip()

    edited_questions = data.get("edited_questions") or data.get("updated_questions")
    if isinstance(edited_questions, str):
        try:
            import json
            edited_questions = json.loads(edited_questions)
        except Exception:
            edited_questions = []

    if edited_questions and isinstance(edited_questions, list):
        for i, edited_q in enumerate(edited_questions):
            if i < len(questions) and isinstance(edited_q, dict):
                if "question" in edited_q and edited_q["question"]:
                    questions[i]["question"] = str(edited_q["question"]).strip()
                if "scale_type" in edited_q and edited_q["scale_type"]:
                    questions[i]["scale_type"] = edited_q["scale_type"]
                if "options" in edited_q and isinstance(edited_q["options"], list):
                    questions[i]["options"] = edited_q["options"]

    primary_survey_type = (
        questions[0].get("scale_type", "").lower()
        if questions else "general"
    )

    ai_questions_added = False

    if action in ["add", "remove"]:
        if action == "add":
            topic = focus_area or title
            try:
                tone_map = {
                    "simple": "easy and straightforward",
                    "moderate": "balanced and thoughtful",
                    "detailed": "analytical and in-depth"
                }
                tone = tone_map.get(complexity.lower(), "balanced and thoughtful")

                prompt = f"""
                Generate 3–4 {tone} survey questions about '{topic}'.
                Avoid numbering or prefixes. Keep them concise, neutral, and measurable.
                Example: How satisfied are you with our {topic} process?
                For any yes/no or single-choice question, explicitly mention if it is radio style.
                """

                response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    timeout=15,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=500
                )
                content = response.choices[0].message.content.strip()
                ai_questions = [
                    re.sub(r"^\s*(\d+[\.\)]|[-•])\s*", "", q.strip())
                    for q in content.split("\n") if q.strip()
                ]

            except Exception as e:
                print(f"[WARNING] AI question generation failed (add): {e}")
                ai_questions = [
                    f"How satisfied are you with our {topic} process?",
                    f"How clear was the communication regarding {topic}?",
                    f"Did you experience any difficulty with {topic}?",
                    f"What improvements do you suggest for {topic}?"
                ]

            def infer_add_scale(question: str) -> str:
                lower_q = question.lower()
                if "nps" in lower_q or "recommend" in lower_q or "likely" in lower_q:
                    return "nps"
                if "satisfied" in lower_q or "csat" in lower_q:
                    return "csat"
                if "ease" in lower_q or "ces" in lower_q:
                    return "ces"
                if any(x in lower_q for x in ["rate", "rating", "score"]):
                    return "rating"
                if any(x in lower_q for x in ["why", "describe", "explain", "feedback", "suggest"]):
                    return "text"
                if any(x in lower_q for x in ["choose", "select", "pick one", "yes or no", "yes/no"]):
                    return "radio"
                if any(x in lower_q for x in ["multiple", "select all", "choose all"]):
                    return "mcq"
                if "matrix" in lower_q or "compare" in lower_q:
                    return "matrix"
                if "upload" in lower_q or "file" in lower_q:
                    return "file"
                return "rating"

            new_qs = []
            for q in ai_questions[:4]:
                inferred = infer_add_scale(q)
                if inferred in ["nps", "csat", "ces", "rating"]:
                    final_scale = (
                        primary_survey_type
                        if primary_survey_type in ["nps", "csat", "ces"]
                        else inferred
                    )
                else:
                    final_scale = inferred

                q_obj = {"question": q, "scale_type": final_scale}
                if final_scale == "radio":
                    q_obj["options"] = ["Yes", "No", "Not sure"]

                new_qs.append(q_obj)

            questions.extend(new_qs)
            ai_questions_added = True

        elif action == "remove":
            if not remove_input:
                return jsonify({"error": "Missing remove_input", "message": "⚠️ Specify which question to remove (e.g., Q2 or keyword)."}), 400

            display_remove = truncate_text_display(remove_input)
            remove_targets = [r.strip().lower() for r in remove_input.split(",") if r.strip()]
            to_remove = []

            for i, q in enumerate(questions):
                q_text = q["question"].lower()
                for target in remove_targets:
                    if target == f"q{i+1}".lower() or target in q_text:
                        to_remove.append(i)
                        break

            if not to_remove:
                return jsonify({"error": "Question not found", "message": f"⚠️ No question found matching '{display_remove}'."}), 404

            for i in sorted(set(to_remove), reverse=True):
                questions.pop(i)

            return jsonify({
                "message": f"[DELETED] Removed {len(to_remove)} question(s) successfully.",
                "ask_add": True,
                "customization_questions": [{
                    "question": "Would you like to add any questions to this template now?",
                    "options": ["Yes", "No"]
                }],
                "selected_template": selected
            })


    if scale_action == "yes" and scale_changes:
        for key, new_scale in scale_changes.items():
            if key.startswith("q") and key[1:].isdigit():
                idx = int(key[1:]) - 1
                if 0 <= idx < len(questions):
                    questions[idx]["scale_type"] = new_scale
                    if new_scale == "radio" and not questions[idx].get("options"):
                        questions[idx]["options"] = ["Yes", "No", "Not sure"]

    selected["questions"] = questions

    if ai_questions_added:
        customization_qs = [{
            "question": "Would you like to adjust individual scale_types for specific questions?",
            "options": ["Yes", "No"]
        }]
    else:
        customization_qs = [
            {
                "question": "Would you like to add or remove any questions from this template?",
                "options": ["Add", "Remove", "No Changes"]
            },
            {
                "question": "Would you like to add questions related to any specific focus area?",
                "allow_text_input": True
            },
            {
                "question": "What complexity level of questions do you prefer in this survey?",
                "options": ["Simple", "Moderate", "Detailed"]
            }
        ]

    return jsonify({
        "message": "[SUCCESS] Template customization completed successfully.",
        "selected_template": selected,
        "customization_questions": customization_qs
    })


# ---------- FINALIZE TEMPLATE ----------
@survey_bp.route("/finalize_template", methods=["GET", "POST"])
def finalize_template():
    data = extract_request_payload(request)
    final_template = data.get("final_template")
    if isinstance(final_template, str):
        try:
            import json
            final_template = json.loads(final_template)
        except Exception:
            final_template = None

    if not final_template or not isinstance(final_template, dict):
        return jsonify({"error": "Missing or invalid final_template", "message": "⚠️ Please select a template first to finalize."}), 400

    template_id, file_path = save_finalized_template(final_template)

    return jsonify({
        "message": "Template finalized successfully.",
        "template_id": template_id,
        "path": file_path
    })



