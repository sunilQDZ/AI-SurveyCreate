
# from flask import Flask, request, jsonify, render_template
# import json, os, re
# from datetime import datetime
# import openai

# app = Flask(__name__)

# # --- Configuration: prefer setting OPENAI_API_KEY as an environment variable ---
# openai.api_key = os.getenv("OPENAI_API_KEY", "")

# OUTPUT_FILE = "saved_surveys.json"
# RESPONSES_FILE = "responses.json"

# for path, default in [(OUTPUT_FILE, []), (RESPONSES_FILE, [])]:
#     if not os.path.exists(path):
#         with open(path, "w", encoding="utf-8") as fh:
#             json.dump(default, fh, indent=2)

# # -----------------------
# # Constants & Helpers
# # -----------------------
# ALLOWED_SCALE_TYPES = [
#     "nps", "csat", "ces", "rating",
#     "text", "radio", "mcq", "matrix", "file"
# ]


# def save_history(entry: dict):
#     try:
#         with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
#             data = json.load(f)
#     except Exception:
#         data = []
#     data.append(entry)
#     with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=2, ensure_ascii=False)


# def extract_json_array(text: str):
#     """
#     Robust JSON array extractor from model output.
#     """
#     m = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
#     if not m:
#         m = re.search(r"\[.*\]", text, re.DOTALL)
#     if not m:
#         raise ValueError("No JSON array found in model response")
#     return json.loads(m.group())


# def get_first_question_for_type(survey_type: str, topic_hint: str | None = None) -> dict:
#     """
#     First question + scale_type per survey type.
#     NPS → 0–10 recommendation
#     CSAT → 1–5 satisfaction
#     CES → 1–5 ease/effort
#     """
#     topic = topic_hint or "your recent experience"

#     if survey_type == "nps":
#         return {
#             "question": (
#                 f"On a scale of 0–10, how likely are you to recommend us to a friend or "
#                 f"colleague based on {topic}?"
#             ),
#             "scale_type": "nps"
#         }
#     if survey_type == "csat":
#         return {
#             "question": f"On a scale of 1–5, how satisfied are you with {topic}?",
#             "scale_type": "csat"
#         }
#     if survey_type == "ces":
#         return {
#             "question": f"On a scale of 1–5, how easy was it for you to complete {topic}?",
#             "scale_type": "ces"
#         }

#     # general fallback
#     return {
#         "question": f"On a scale of 1–10, how satisfied are you with {topic}?",
#         "scale_type": "rating"
#     }


# def infer_scale_type(question: str) -> str:
#     """
#     Infer *intent* of the question:
#     - nps / csat / ces for numeric ratings
#     - radio / mcq / matrix / file / text for others
#     """
#     q = (question or "").lower().strip()

#     # ----- numeric rating intents -----
#     if any(x in q for x in ["recommend", "likely to recommend", "nps"]):
#         return "nps"
#     if any(x in q for x in ["satisfied", "satisfaction", "rate your", "overall satisfaction"]):
#         return "csat"
#     if any(x in q for x in ["easy", "effort", "difficulty", "how easy"]):
#         return "ces"

#     # ----- yes/no / single choice -----
#     if (q.startswith("did ") or q.startswith("do ") or q.startswith("does ") or
#         q.startswith("is ") or q.startswith("are ") or q.startswith("was ") or
#         "yes or no" in q or "yes/no" in q):
#         return "radio"

#     if any(x in q for x in ["which of the following", "choose one", "select one", "single best"]):
#         return "radio"

#     # ----- multiple choice -----
#     if any(x in q for x in ["select all", "choose all", "multiple options", "check all that apply"]):
#         return "mcq"

#     # ----- matrix / comparison -----
#     if any(x in q for x in ["rate the following", "rate each", "for each of the following", "across these"]):
#         return "matrix"

#     # ----- file upload -----
#     if any(x in q for x in ["upload", "attach", "file", "document", "screenshot"]):
#         return "file"

#     # default: open text
#     return "text"


# def normalize_template_scales(template: dict, forced_type: str):
#     """
#     Strict scale enforcement:
#     - NPS → Only 'nps', 'radio', 'mcq', 'text','matrix' ,'file'
#     - CSAT → Only 'csat', 'radio', 'mcq', 'text','matrix' ,'file'
#     - CES → Only 'ces', 'radio', 'mcq', 'text','matrix' ,'file'
#     - GENERAL → All ok
#     """
#     allowed_by_type = {
#         "nps": ["nps", "radio", "mcq", "text", "matrix", "file"],
#         "csat": ["csat", "radio", "mcq", "text", "matrix", "file"],
#         "ces": ["ces", "radio", "mcq", "text", "matrix", "file"],
#         "general": ALLOWED_SCALE_TYPES,
#     }.get(forced_type, ALLOWED_SCALE_TYPES)

#     for q in template.get("questions", []):
#         inferred = infer_scale_type(q.get("question", ""))

#         if inferred not in allowed_by_type:
#             if forced_type == "nps":
#                 q["scale_type"] = "nps"
#             elif forced_type == "csat":
#                 q["scale_type"] = "csat"
#             elif forced_type == "ces":
#                 q["scale_type"] = "ces"
#             else:
#                 q["scale_type"] = "text"
#         else:
#             q["scale_type"] = inferred

#     return template


# def clamp_duration(duration: str | None) -> str:
#     """
#     Force duration within ~2–2.5 minutes.
#     """
#     if not duration:
#         return "2–2.5 mins"
#     d = duration.lower()
#     # accept already-correct values
#     if any(x in d for x in ["2–2.5", "2-2.5", "2 to 2.5"]):
#         return duration
#     # anything else → clamp
#     return "2–2.5 mins"


# # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# # NEW: AI-BASED PARAMETER ANALYSIS (ONLY BRAIN, 3 FIELDS)
# # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

# def analyze_user_input_with_openai(user_input: str) -> dict:
#     """
#     AI-only extractor for:
#       - survey_type  ∈ {"nps","csat","ces","general"} or None
#       - audience     ∈ any dynamic string or None
#       - purpose      ∈ any dynamic string or None

#     STRICT RULES:
#       - If unsure about any field → return null for that field.
#       - Do NOT guess. Prefer null.
#       - "education department" and similar SHOULD be purpose, NOT audience.
#       - Words like 'department','team','branch','office','unit','center' are NOT audiences.
#     """
#     empty_result = {
#         "survey_type": None,
#         "audience": None,
#         "purpose": None
#     }

#     user_input = (user_input or "").strip()
#     if not user_input:
#         return empty_result

#     prompt = f"""
# You analyze a user's survey request and extract EXACT metadata.

# Return ONLY this JSON object:
# {{
#   "survey_type": "nps" | "csat" | "ces" | "general" | null,
#   "audience": string | null,
#   "purpose": string | null
# }}

# DEFINITIONS:

# 1) survey_type:
#    - "nps"     → if user talks about recommendation, likelihood to recommend, promoters, detractors.
#    - "csat"    → if user talks about satisfaction (happy / satisfied with service, repair, product).
#    - "ces"     → if user talks about effort or ease ("how easy", "difficulty").
#    - "general" → ONLY if user clearly says they want a general survey.
#    - If survey type is not clear → return null (do NOT auto use "general").

# 2) audience:
#    - Who will ANSWER the survey (people group).
#    - Allowed examples: "Customers", "Employees", "Students", "Teachers",
#      "Parents", "Vendors", "Users", "Staff", "Patients", "Visitors".
#    - Detect only when the text clearly mentions such groups.
#    - Phrases like "as a customer" → audience = "Customers".
#    - IMPORTANT: Words like "department", "team", "branch", "office",
#      "unit", "center", "school department", "education department" are
#      NOT audiences. These should never be returned as audience.
#    - If audience is not clearly a people group → return null.

# 3) purpose:
#    - Short phrase about what the survey is about.
#    - Use phrases from patterns like:
#        "survey for X", "survey on X", "survey about X", "survey regarding X".
#    - Example:
#        "survey for education department" → purpose = "education department"
#        "csat survey for laptop repair" → purpose = "laptop repair"
#        "nps survey about our mobile app" → purpose = "our mobile app"
#    - Keep purpose close to original user wording.
#    - If no clear topic is given, allow purpose to be null.

# RULES:
# - If you are NOT clearly sure about a field, set it to null.
# - Do NOT invent or guess extra information.
# - NEVER use a department/team/office as audience. That belongs to purpose.
# - Respond with STRICT JSON only. No explanation, no markdown.

# User request:
# \"\"\"{user_input}\"\"\"
# """

#     try:
#         resp = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {
#                     "role": "system",
#                     "content": "You extract survey parameters and MUST respond with strict JSON only."
#                 },
#                 {
#                     "role": "user",
#                     "content": prompt
#                 }
#             ],
#             temperature=0.0,
#             max_tokens=400,
#         )
#         content = resp["choices"][0]["message"]["content"].strip()

#         # Try direct JSON parse first
#         try:
#             data = json.loads(content)
#         except Exception:
#             m = re.search(r"\{.*\}", content, re.DOTALL)
#             if not m:
#                 return empty_result
#             data = json.loads(m.group())

#         def norm_str(val):
#             if not isinstance(val, str):
#                 return None
#             s = val.strip()
#             return s or None

#         raw_survey_type = norm_str(data.get("survey_type"))
#         audience = norm_str(data.get("audience"))
#         purpose = norm_str(data.get("purpose"))

#         # Normalize survey_type to allowed values or None
#         survey_type = None
#         if raw_survey_type:
#             st = raw_survey_type.lower()
#             if "nps" in st or "net promoter" in st:
#                 survey_type = "nps"
#             elif "csat" in st or "satisfaction" in st:
#                 survey_type = "csat"
#             elif "ces" in st or "effort" in st or "easy" in st:
#                 survey_type = "ces"
#             elif "general" in st or "not sure" in st or "other" in st:
#                 survey_type = "general"
#             else:
#                 survey_type = None

#         # Extra safety: if audience looks like a department/team, push it to purpose
#         if audience:
#             lower_aud = audience.lower()
#             dept_words = ["department", "team", "branch", "office", "unit", "center", "centre"]
#             if any(w in lower_aud for w in dept_words):
#                 # if purpose is empty and audience looks like dept → treat as purpose instead
#                 if not purpose:
#                     purpose = audience
#                 audience = None

#         return {
#             "survey_type": survey_type,
#             "audience": audience,
#             "purpose": purpose
#         }

#     except Exception as e:
#         print("⚠️ OpenAI analysis failed:", e)
#         # On any failure: we will ask all questions again
#         return empty_result


# # -----------------------
# # ROUTES
# # -----------------------
# @app.route("/")
# def home():
#     return render_template("index.html")


# # ---------- UPDATED QUESTION FLOW (AI-only detection, NO TOUCHPOINT) ----------
# @app.route("/generate_question_flow", methods=["POST"])
# def generate_question_flow():
#     """
#     AI-first behavior:
#     - Analyze user_input for:
#         - survey_type (NPS/CSAT/CES/general)
#         - audience (dynamic)
#         - purpose/topic (dynamic)
#     - Ask ONLY for the pieces that are missing.
#     - If everything is already present → skip follow-up questions and let
#       frontend jump directly to sample/template creation.
#     """
#     data = request.get_json(force=True) or {}
#     user_input = (data.get("user_input") or "").strip()

#     # Explicit values from payload (user might have selected these in UI already)
#     requested_type_raw = (data.get("survey_type") or "").strip().lower()
#     audience_from_payload = (data.get("audience") or "").strip()
#     purpose_from_payload = (data.get("purpose") or "").strip()

#     # --- AI analysis (single call) ---
#     ai_result = analyze_user_input_with_openai(user_input) if user_input else {
#         "survey_type": None,
#         "audience": None,
#         "purpose": None
#     }

#     ai_survey_type = ai_result.get("survey_type")
#     ai_audience = ai_result.get("audience")
#     ai_purpose = ai_result.get("purpose")

#     # --- Survey type precedence: payload > AI > None ---
#     survey_type = None
#     if requested_type_raw in ["nps", "csat", "ces", "general"]:
#         survey_type = requested_type_raw
#     elif ai_survey_type in ["nps", "csat", "ces", "general"]:
#         survey_type = ai_survey_type
#     else:
#         survey_type = None  # DO NOT default to general here

#     # Type is known only if it is explicitly NPS/CSAT/CES
#     type_known = survey_type in ["nps", "csat", "ces"]

#     # --- Audience / purpose: payload overrides AI ---
#     detected_audience = audience_from_payload or ai_audience
#     detected_purpose = purpose_from_payload or ai_purpose

#     question_flow = []

#     # Ask ONLY for missing fields
#     if not type_known:
#         question_flow.append({
#             "id": "survey_type",
#             "q": "Which type of survey would you like to create?",
#             "options": ["NPS", "CSAT", "CES", "General / Not sure"]
#         })

#     if not detected_audience:
#         question_flow.append({
#             "id": "audience",
#             "q": "Who is your audience for this survey?",
#             "options": [
#                 "Customers",
#                 "Employees",
#                 "B2B",
#                 "Clients",
#                 "Users",
#                 "Learners",
#                 "Vendors",
#                 "Parents",
#                 "General users"
#             ]
#         })


#     if not detected_purpose:
#         question_flow.append({
#             "id": "purpose",
#             "q": "What is the main topic or purpose of this survey?",
#             "allow_text_input": True
#         })

#     # If NOTHING is missing → skip follow-up questions
#     if not question_flow:
#         return jsonify({
#             "skip_questions": True,
#             "question_flow": [],
#             "detected_survey_type": survey_type,
#             "detected_audience": detected_audience,
#             "detected_purpose": detected_purpose,
#             "original_user_input": user_input
#         })

#     # Otherwise, return only the missing questions
#     return jsonify({
#         "skip_questions": False,
#         "question_flow": question_flow,
#         "detected_survey_type": survey_type,
#         "detected_audience": detected_audience,
#         "detected_purpose": detected_purpose,
#         "original_user_input": user_input
#     })


# # ---------- MAIN TEMPLATE GENERATION ----------
# @app.route("/generate_survey", methods=["POST"])
# def generate_survey():
#     data = request.get_json() or {}
#     user_input = (data.get("user_input") or "").strip()
#     requested_type_raw = (data.get("survey_type") or "").strip().lower()

#     if not user_input:
#         return jsonify({"error": "Missing user_input"}), 400

#     # survey_type: prefer explicit payload, else AI, else general
#     survey_type = None
#     if requested_type_raw in ["nps", "csat", "ces", "general"]:
#         survey_type = requested_type_raw
#     else:
#         ai_result = analyze_user_input_with_openai(user_input)
#         ai_type = ai_result.get("survey_type")
#         if ai_type in ["nps", "csat", "ces", "general"]:
#             survey_type = ai_type
#         else:
#             survey_type = "general"

#     processed_templates = []

#     # Prompt for GPT (templates generation)
#     prompt = f"""
# You are a CX survey expert.
# Generate 3 survey templates for: "{user_input}"
# Survey type: "{survey_type.upper()} Survey Template" (NPS/CSAT/CES/GENERAL).

# Rules:
# - STRICT JSON array ONLY (no explanation).
# - Each template object must have keys: "title", "purpose", "duration", "questions".
# - duration MUST be around 2–2.5 minutes only (e.g., "2–2.5 mins").
# - FIRST question MUST be a rating question that matches survey_type its be on the basis of gnerated survey type.:
#     NPS  → 0–10 "likelihood to recommend" → scale_type "nps"
#     CSAT → 1–5 or 1–7 "satisfaction"      → scale_type "csat"
#     CES  → 1–5 or 1–7 "ease/effort"       → scale_type "ces"
# - DO NOT mix NPS/CSAT/CES scales in one template.
# - Each template MUST contain 5–7 questions.
# - For every question, return an object with at least:
#     - "question": text of the question
#     - "scale_type": one of ["nps","csat","ces","rating","text","radio","mcq","matrix","file"]
# - For any question with "scale_type": "radio" or "mcq", include an "options" array of labels.
# - Avoid duplicate question meaning in a single template.
# - this is our model totally a survey generator tool give me more accurate result better result.
# """

#     try:
#         resp = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": "Return strict JSON only, no explanation."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.4,
#             max_tokens=1000
#         )
#         text = resp["choices"][0]["message"]["content"]
#         try:
#             templates = extract_json_array(text)
#         except Exception:
#             templates = []

#     except Exception as e:
#         print("Generate survey error:", e)
#         templates = []

#     enforced_first_q = get_first_question_for_type(survey_type, user_input)

#     # Clean and enforce constraints on each template
#     for t in templates:
#         t.setdefault("title", f"{survey_type.upper()} Survey Template")
#         t.setdefault("purpose", f"Capture responses related to {user_input}")
#         t["duration"] = clamp_duration(t.get("duration"))
#         t.setdefault("questions", [])

#         cleaned_questions = []

#         for q in t["questions"]:
#             # Collect question text + any provided options
#             if isinstance(q, str):
#                 question_text = q.strip()
#                 raw_options = []
#             else:
#                 question_text = (
#                     q.get("question")
#                     or q.get("text")
#                     or q.get("label")
#                     or ""
#                 ).strip()
#                 raw_options = q.get("options") or []

#             if not question_text:
#                 continue

#             # Ensure options is list of strings
#             options_clean = []
#             if isinstance(raw_options, list):
#                 for o in raw_options:
#                     s = str(o).strip()
#                     if s:
#                         options_clean.append(s)

#             detected = infer_scale_type(question_text)

#             # Smart scale selection
#             if detected in ["nps", "csat", "ces", "rating"]:
#                 if survey_type in ["nps", "csat", "ces"]:
#                     scale = survey_type
#                 else:
#                     scale = detected if detected in ["nps", "csat", "ces"] else "rating"
#             else:
#                 scale = detected if detected in ["text", "radio", "mcq", "matrix", "file"] else "text"

#             q_obj = {
#                 "question": question_text,
#                 "scale_type": scale
#             }

#             # RADIO OPTIONS: ensure radio questions have options
#             if scale == "radio":
#                 if options_clean:
#                     q_obj["options"] = options_clean
#                 else:
#                     q_obj["options"] = ["Yes", "No", "Not sure"]

#             # MCQ options if provided
#             if scale == "mcq" and options_clean:
#                 q_obj["options"] = options_clean

#             cleaned_questions.append(q_obj)

#         t["questions"] = cleaned_questions

#         # Ensure FIRST question is correct
#         if not t["questions"] or t["questions"][0]["scale_type"] != (
#             survey_type if survey_type in ["nps", "csat", "ces"] else t["questions"][0]["scale_type"]
#         ):
#             t["questions"].insert(0, enforced_first_q)

#         # Guarantee 5–7 questions
#         if len(t["questions"]) < 5:
#             while len(t["questions"]) < 5:
#                 t["questions"].append({
#                     "question": f"Please share any additional feedback about {user_input}.",
#                     "scale_type": "text"
#                 })
#         elif len(t["questions"]) > 7:
#             t["questions"] = t["questions"][:7]

#         processed_templates.append(t)

#     # Normalize template scales
#     processed_templates = [
#         normalize_template_scales(t, forced_type=survey_type)
#         for t in processed_templates
#     ]

#     # For any radio question still missing options, add default Yes/No options
#     for t in processed_templates:
#         for q in t.get("questions", []):
#             if q.get("scale_type") == "radio" and not q.get("options"):
#                 q["options"] = ["Yes", "No", "Not sure"]

#     # Save to history
#     save_history({
#         "timestamp": datetime.now().isoformat(),
#         "input": user_input,
#         "survey_type": survey_type,
#         "templates": processed_templates
#     })

#     return jsonify({
#         "surveys": processed_templates,
#         "detected_survey_type": survey_type
#     })


# # ---------- GENERATE MORE ----------
# @app.route("/generate_more_surveys", methods=["POST"])
# def generate_more_surveys():
#     """
#     Generate 3 short survey templates based on a focus area.
#     Uses ALL wanted context from the first API: generate_question_flow.
#     """
#     data = request.get_json() or {}

#     focus_area = (data.get("focus_area") or "").strip()
#     if not focus_area:
#         return jsonify({"error": "Missing focus_area"}), 400

#     # FRONTEND context from generate_question_flow
#     ctx = data.get("context") or {}
#     original_user_input = (ctx.get("original_user_input") or "").strip()
#     detected_survey_type = (ctx.get("detected_survey_type") or "").strip()
#     detected_audience = (ctx.get("detected_audience") or "").strip()
#     detected_purpose = (ctx.get("detected_purpose") or "").strip()
#     detected_touchpoint = (ctx.get("detected_touchpoint") or "").strip()

#     # Survey type ALWAYS from first API context
#     survey_type = detected_survey_type if detected_survey_type in ["nps", "csat", "ces", "general"] else "general"

#     # 🔥 Your new PERFECT prompt
#     prompt = f"""
# You are a CX survey expert.

# ORIGINAL USER REQUEST:
# \"\"\"{original_user_input}\"\"\"

# Extracted from the FIRST API:
# - Audience: {detected_audience}
# - Purpose: {detected_purpose}
# - Touchpoint: {detected_touchpoint}

# Your job:
# Generate 3 NEW survey templates that are:
# - related to the original user input context
# - AND focused on this refinement: "{focus_area}"
# - Survey type: "{survey_type.upper()}"

# EXAMPLES (do NOT copy, only understand):
# - If original request = Café experience survey
#   and focus_area = Food
#   → Output MUST be: "Café Food Experience Survey Template X"

# - If original request = Hospital patient feedback
#   and focus_area = Doctor Interaction
#   → Output MUST be: "Doctor Interaction Feedback Template X"

# STRICT RULES:
# - Return ONLY a JSON array of templates.
# - Each template MUST have:
#     "title"
#     "purpose"
#     "duration"
#     "questions"
# - Duration MUST ALWAYS be: "2–2.5 mins"
# - EXACT 5 questions per template.
# - Questions MUST have:
#     "question"
#     "scale_type"
#     "options" (required only for radio/mcq)

# SCALE RULES:
# - nps → 0–10 likelihood to recommend
# - csat → 1–5 satisfaction
# - ces → 1–5 effort/ease
# - radio/mcq → MUST include "options"

# DO NOT add any extra keys.
# DO NOT rename any keys.
# DO NOT output text before/after JSON.
# """

#     try:
#         resp = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.5,
#             max_tokens=700
#         )
#         text = resp["choices"][0]["message"]["content"]

#         try:
#             templates = extract_json_array(text)
#         except Exception:
#             templates = []

#         # Normalize scales
#         templates = [
#             normalize_template_scales(t, forced_type=survey_type)
#             for t in templates
#         ]

#         # Ensure radio questions have options
#         for t in templates:
#             for q in t.get("questions", []):
#                 if q.get("scale_type") == "radio" and not q.get("options"):
#                     q["options"] = ["Yes", "No", "Not sure"]

#         # Clamp duration
#         for t in templates:
#             t["duration"] = clamp_duration(t.get("duration"))

#         return jsonify({
#             "templates": templates,
#             "focus_area": focus_area,
#             "survey_type": survey_type,
#             "context_used": ctx  # To debug if needed
#         })

#     except Exception as e:
#         print("Error generate_more:", e)
#         return jsonify({"error": str(e)}), 500



# # ---------- CUSTOMIZE SELECTED TEMPLATE ----------
# @app.route("/customize_selected_template", methods=["POST"])
# def customize_selected_template():
#     """
#     Unified endpoint for survey customization.
#     - Handles Add / Remove actions
#     - Adds AI-generated questions based on focus/complexity
#     - Ensures newly added rating questions match template survey_type
#     - Updates scale types
#     - Returns next-step customization prompts
#     """
#     import re

#     data = request.get_json() or {}
#     templates = data.get("templates", [])
#     choice = (data.get("choice") or "").lower()
#     action = (data.get("action") or "").lower()
#     focus_area = (data.get("focus_area") or "").strip()
#     complexity = (data.get("complexity") or "").strip()
#     scale_action = (data.get("scale_action") or "").lower()
#     scale_changes = data.get("scale_changes", {}) or {}
#     remove_input = (data.get("remove_input") or "").strip()

#     if not templates or not choice:
#         return jsonify({"error": "Missing 'templates' or 'choice'."}), 400

#     # Identify selected template
#     try:
#         index = int(re.search(r"\d+", choice).group()) - 1
#         selected = templates[index]
#     except Exception:
#         return jsonify({"error": "Invalid template choice format."}), 400

#     questions = selected.get("questions", [])
#     title = selected.get("title", "General Feedback")

#     # Detect survey_type from first question
#     primary_survey_type = (
#         questions[0].get("scale_type", "").lower()
#         if questions else "general"
#     )

#     # ---------------------- STEP 1: ADD OR REMOVE QUESTIONS ----------------------
#     ai_questions_added = False  # Track if AI-generated questions were added

#     if action in ["add", "remove"]:

#         # ----- ADDing questions -----
#         if action == "add":
#             topic = focus_area or title
#             try:
#                 tone_map = {
#                     "simple": "easy and straightforward",
#                     "moderate": "balanced and thoughtful",
#                     "detailed": "analytical and in-depth"
#                 }
#                 tone = tone_map.get(complexity.lower(), "balanced and thoughtful")

#                 prompt = f"""
#                 Generate 3–4 {tone} survey questions about '{topic}'.
#                 Avoid numbering or prefixes. Keep them concise, neutral, and measurable.
#                 Example: How satisfied are you with our {topic} process?
#                 For any yes/no or single-choice question, explicitly mention if it is radio style.
#                 """

#                 response = openai.ChatCompletion.create(
#                     model="gpt-3.5-turbo",
#                     messages=[{"role": "user", "content": prompt}],
#                     temperature=0.7,
#                     max_tokens=250
#                 )
#                 content = response["choices"][0]["message"]["content"].strip()
#                 ai_questions = [
#                     re.sub(r"^\s*(\d+[\.\)]|[-•])\s*", "", q.strip())
#                     for q in content.split("\n") if q.strip()
#                 ]

#                 # Local scale type inference for added questions
#                 def infer_add_scale(question: str) -> str:
#                     lower_q = question.lower()
#                     if "nps" in lower_q or "recommend" in lower_q or "likely" in lower_q:
#                         return "nps"
#                     if "satisfied" in lower_q or "csat" in lower_q:
#                         return "csat"
#                     if "ease" in lower_q or "ces" in lower_q:
#                         return "ces"
#                     if any(x in lower_q for x in ["rate", "rating", "score"]):
#                         return "rating"
#                     if any(x in lower_q for x in ["why", "describe", "explain", "feedback", "suggest"]):
#                         return "text"
#                     if any(x in lower_q for x in ["choose", "select", "pick one", "yes or no", "yes/no"]):
#                         return "radio"
#                     if any(x in lower_q for x in ["multiple", "select all", "choose all"]):
#                         return "mcq"
#                     if "matrix" in lower_q or "compare" in lower_q:
#                         return "matrix"
#                     if "upload" in lower_q or "file" in lower_q:
#                         return "file"
#                     return "rating"

#                 new_qs = []
#                 for q in ai_questions[:4]:
#                     inferred = infer_add_scale(q)

#                     # Force match with template survey type for rating questions
#                     if inferred in ["nps", "csat", "ces", "rating"]:
#                         final_scale = (
#                             primary_survey_type
#                             if primary_survey_type in ["nps", "csat", "ces"]
#                             else inferred
#                         )
#                     else:
#                         final_scale = inferred

#                     q_obj = {"question": q, "scale_type": final_scale}

#                     # RADIO OPTIONS for added questions
#                     if final_scale == "radio":
#                         q_obj["options"] = ["Yes", "No", "Not sure"]

#                     new_qs.append(q_obj)

#                 questions.extend(new_qs)
#                 ai_questions_added = True

#             except Exception as e:
#                 print(f"⚠️ AI question generation failed (add): {e}")
#                 return jsonify({"error": f"AI customization failed: {str(e)}"}), 500

#         # ----- REMOVING questions -----
#         elif action == "remove":
#             if not remove_input:
#                 return jsonify({"message": "Specify which question to remove (e.g., Q2 or keyword)."}), 400

#             remove_targets = [r.strip().lower() for r in remove_input.split(",") if r.strip()]
#             to_remove = []

#             for i, q in enumerate(questions):
#                 q_text = q["question"].lower()
#                 for target in remove_targets:
#                     if target == f"q{i+1}".lower() or target in q_text:
#                         to_remove.append(i)
#                         break

#             if not to_remove:
#                 return jsonify({"message": f"No question found matching '{remove_input}'."}), 404

#             for i in sorted(set(to_remove), reverse=True):
#                 questions.pop(i)

#             return jsonify({
#                 "message": f"🗑️ Removed {len(to_remove)} question(s) successfully.",
#                 "ask_add": True,
#                 "customization_questions": [{
#                     "question": "Would you like to add any questions to this template now?",
#                     "options": ["Yes", "No"]
#                 }],
#                 "selected_template": selected
#             })

#     # ---------------------- STEP 2: SCALE TYPE CUSTOMIZATION ----------------------
#     if scale_action == "yes" and scale_changes:
#         for key, new_scale in scale_changes.items():
#             if key.startswith("q") and key[1:].isdigit():
#                 idx = int(key[1:]) - 1
#                 if 0 <= idx < len(questions):
#                     questions[idx]["scale_type"] = new_scale
#                     # ensure radio options
#                     if new_scale == "radio" and not questions[idx].get("options"):
#                         questions[idx]["options"] = ["Yes", "No", "Not sure"]

#     selected["questions"] = questions

#     # ---------------------- STEP 3: NEXT CUSTOMIZATION QUESTIONS ----------------------
#     if ai_questions_added:
#         customization_qs = [{
#             "question": "Would you like to adjust individual scale_types for specific questions?",
#             "options": ["Yes", "No"]
#         }]
#     else:
#         customization_qs = [
#             {
#                 "question": "Would you like to add or remove any questions from this template?",
#                 "options": ["Add", "Remove", "No Changes"]
#             },
#             {
#                 "question": "Would you like to add questions related to any specific focus area?",
#                 "allow_text_input": True
#             },
#             {
#                 "question": "What complexity level of questions do you prefer in this survey?",
#                 "options": ["Simple", "Moderate", "Detailed"]
#             }
#         ]

#     return jsonify({
#         "message": "✅ Template customization completed successfully.",
#         "selected_template": selected,
#         "customization_questions": customization_qs
#     })


# # ---------- FINALIZE ----------
# @app.route("/finalize_template", methods=["POST"])
# def finalize_template():
#     data = request.get_json() or {}
#     final_template = data.get("final_template")
#     if not final_template:
#         return jsonify({"error": "Missing final_template"}), 400

#     template_id = datetime.now().strftime("%Y%m%d%H%M%S")
#     os.makedirs("finalized_templates", exist_ok=True)
#     file_path = os.path.join("finalized_templates", f"template_{template_id}.json")

#     with open(file_path, "w", encoding="utf-8") as f:
#         json.dump(final_template, f, ensure_ascii=False, indent=2)

#     save_history({
#         "timestamp": datetime.now().isoformat(),
#         "action": "finalize",
#         "path": file_path,
#         "template": final_template
#     })

#     return jsonify({
#         "message": "Template finalized successfully.",
#         "template_id": template_id,
#         "path": file_path
#     })


# # -----------------------
# # RUN APP
# # -----------------------
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=True)
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import json, os, re
from datetime import datetime
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
CORS(app) # Enable CORS for all routes so external frontends can call APIs

# --- Configuration: prefer setting OPENAI_API_KEY as an environment variable ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

OUTPUT_FILE = "saved_surveys.json"
RESPONSES_FILE = "responses.json"

for path, default in [(OUTPUT_FILE, []), (RESPONSES_FILE, [])]:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(default, fh, indent=2)

# -----------------------
# Constants & Helpers
# -----------------------
ALLOWED_SCALE_TYPES = [
    "nps", "csat", "ces", "rating",
    "text", "radio", "mcq", "matrix", "file"
]


def save_history(entry: dict):
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    data.append(entry)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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

    # general fallback
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

    # default: open text
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


def clamp_duration(duration: str | None) -> str:
    """
    Force duration within ~2–2.5 minutes.
    """
    if not duration:
        return "2–2.5 mins"
    d = duration.lower()
    # accept already-correct values
    if any(x in d for x in ["2–2.5", "2-2.5", "2 to 2.5"]):
        return duration
    # anything else → clamp
    return "2–2.5 mins"


def build_fallback_templates(survey_type: str, user_input: str) -> list:
    """
    Production fallback template engine in case of OpenAI API limits or outages.
    """
    topic = user_input or "our services"
    st_upper = (survey_type or "general").upper()
    first_q = get_first_question_for_type(survey_type or "general", topic)
    return [
        {
            "title": f"{st_upper} Survey - {topic.title()}",
            "purpose": f"Capture responses related to {topic}",
            "duration": "2–2.5 mins",
            "questions": [
                first_q,
                {"question": f"How clear and easy to understand was the information provided about {topic}?", "scale_type": "text"},
                {"question": "Did you encounter any issues during your experience?", "scale_type": "radio", "options": ["Yes", "No", "Not sure"]},
                {"question": "How likely are you to continue using our services?", "scale_type": "rating"},
                {"question": "What improvements or suggestions do you have for us?", "scale_type": "text"}
            ]
        },
        {
            "title": f"Detailed {st_upper} Feedback - {topic.title()}",
            "purpose": f"Detailed evaluation survey for {topic}",
            "duration": "2–2.5 mins",
            "questions": [
                first_q,
                {"question": "How satisfied are you with the overall speed and quality of service?", "scale_type": "rating"},
                {"question": "Were your expectations met during this interaction?", "scale_type": "radio", "options": ["Yes", "No", "Partially"]},
                {"question": "How would you rate the helpfulness of our team?", "scale_type": "rating"},
                {"question": "Please share any additional comments or ideas.", "scale_type": "text"}
            ]
        },
        {
            "title": f"Quick {st_upper} Check-in - {topic.title()}",
            "purpose": f"Quick pulse check survey for {topic}",
            "duration": "2–2.5 mins",
            "questions": [
                first_q,
                {"question": "How easy was it to complete your task today?", "scale_type": "rating"},
                {"question": "Would you recommend our product/service to a colleague or friend?", "scale_type": "radio", "options": ["Yes", "No", "Maybe"]},
                {"question": "How well did the service meet your needs?", "scale_type": "rating"},
                {"question": "Is there anything else you would like us to know?", "scale_type": "text"}
            ]
        }
    ]


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# NEW: AI-BASED PARAMETER ANALYSIS (4 FIELDS + SUGGESTIONS)
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

def analyze_user_input_with_openai(user_input: str) -> dict:
    """
    AI-only extractor for:
      - survey_type  ∈ {"nps","csat","ces","general"} or None
      - audience     ∈ any dynamic string or None
      - purpose      ∈ any dynamic string or None
      - touchpoint   ∈ any dynamic string or None

    PLUS:
      - audience_suggestion    ∈ string or None
      - touchpoint_suggestion  ∈ string or None

    STRICT RULES:
      - If unsure about any main field → return null for that field.
      - Do NOT guess random values. Suggestions should still be reasonable.
      - "education department" and similar SHOULD be purpose, NOT audience.
      - Words like 'department','team','branch','office','unit','center' are NOT audiences.
    """
    empty_result = {
        "survey_type": None,
        "audience": None,
        "purpose": None,
        "touchpoint": None,
        "audience_suggestion": None,
        "touchpoint_suggestion": None
    }

    user_input = (user_input or "").strip()
    if not user_input:
        return empty_result

    prompt = f"""
You analyze a user's survey request and extract EXACT metadata.

Return ONLY this JSON object:
{{
  "survey_type": "nps" | "csat" | "ces" | "general" | null,
  "audience": string | null,
  "purpose": string | null,
  "touchpoint": string | null,
  "audience_suggestion": string | null,
  "touchpoint_suggestion": string | null
}}

DEFINITIONS:

1) survey_type:
   - "nps"     → if user talks about recommendation, likelihood to recommend, promoters, detractors.
   - "csat"    → if user talks about satisfaction (happy / satisfied with service, repair, product).
   - "ces"     → if user talks about effort or ease ("how easy", "difficulty").
   - "general" → ONLY if user clearly says they want a general survey.
   - If survey type is not clear → return null (do NOT auto use "general").

2) audience:
   - Who will ANSWER the survey (people group).
   - Allowed examples: "Customers", "Employees", "Students", "Teachers",
     "Parents", "Vendors", "Users", "Staff", "Patients", "Visitors".
   - Detect only when the text clearly mentions such groups.
   - Phrases like "as a customer" → audience = "Customers".
   - IMPORTANT: Words like "department", "team", "branch", "office",
     "unit", "center", "centre", "education department" are NOT audiences.
     These should never be returned as audience.
   - If audience is not clearly a people group → return null.

3) purpose:
   - Short phrase about what the survey is about.
   - Use phrases from patterns like:
       "survey for X", "survey on X", "survey about X", "survey regarding X".
   - Example:
       "survey for education department" → purpose = "education department"
       "csat survey for laptop repair" → purpose = "laptop repair"
       "nps survey about our mobile app" → purpose = "our mobile app"
   - Keep purpose close to original user wording.
   - If no clear topic is given, allow purpose to be null.

4) touchpoint:
   - Channel or interaction point where the experience happens.
   - Examples: "Website", "Mobile app", "Store visit", "Branch visit",
     "Call center", "Support ticket", "WhatsApp chat", "Delivery",
     "Onboarding flow", "Billing & payments", "Doctor consultation",
     "Online classes".
   - Only set touchpoint when the user CLEARLY mentions such a channel or
     interaction (e.g. "mobile app", "website", "store", "call center").
   - If not clearly present → touchpoint can be null.

5) audience_suggestion:
   - If audience is clearly mentioned → audience_suggestion = same audience.
   - If audience is NOT detected, you MUST still give the most suitable audience suggestion.
   - NEVER return null for audience_suggestion when audience is null.
   - Use domain logic:
       - education / school / learning → Students or Parents
       - hospital / clinic / doctor / health → Patients
       - employee / HR / workplace → Employees
       - software / mobile app / website → Users
       - service / repair / branch / retail → Customers
       - government / public services → Citizens
       - college / university → Students
   - Keep suggestion short (1–2 words).


6) touchpoint_suggestion:
   - If touchpoint is clearly mentioned → touchpoint_suggestion = same touchpoint.
   - If touchpoint is NOT clearly mentioned, suggest the MOST likely channel
     based on context:
       - product / app / software feedback → "Mobile app" or "Web app"
       - store / branch / showroom → "Store visit" or "Branch visit"
       - service / repair center → "Service center" or "Repair center"
       - call / phone experience → "Call center"
       - online learning → "Online classes platform"
   - Keep suggestion short (2–4 words).
   - If you truly cannot decide, return null.

RULES:
- If you are NOT clearly sure about a main field, set it to null.
- Suggestions must still be reasonable and based on the text.
- NEVER use a department/team/office as audience. That belongs to purpose.
- Respond with STRICT JSON only. No explanation, no markdown.

User request:
\"\"\"{user_input}\"\"\"
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            timeout=15,
            messages=[
                {
                    "role": "system",
                    "content": "You extract survey parameters and MUST respond with strict JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,
            max_tokens=400,
        )
        content = resp.choices[0].message.content.strip()

        # Try direct JSON parse first
        try:
            data = json.loads(content)
        except Exception:
            m = re.search(r"\{.*\}", content, re.DOTALL)
            if not m:
                return empty_result
            data = json.loads(m.group())

        def norm_str(val):
            if not isinstance(val, str):
                return None
            s = val.strip()
            return s or None

        raw_survey_type = norm_str(data.get("survey_type"))
        audience = norm_str(data.get("audience"))
        purpose = norm_str(data.get("purpose"))
        touchpoint = norm_str(data.get("touchpoint"))
        audience_suggestion = norm_str(data.get("audience_suggestion"))
        touchpoint_suggestion = norm_str(data.get("touchpoint_suggestion"))

        # Normalize survey_type to allowed values or None
        survey_type = None
        if raw_survey_type:
            st = raw_survey_type.lower()
            if "nps" in st or "net promoter" in st:
                survey_type = "nps"
            elif "csat" in st or "satisfaction" in st:
                survey_type = "csat"
            elif "ces" in st or "effort" in st or "easy" in st:
                survey_type = "ces"
            elif "general" in st or "not sure" in st or "other" in st:
                survey_type = "general"
            else:
                survey_type = None

        # Extra safety: if audience looks like a department/team, push it to purpose
        if audience:
            lower_aud = audience.lower()
            dept_words = ["department", "team", "branch", "office", "unit", "center", "centre"]
            if any(w in lower_aud for w in dept_words):
                # if purpose is empty and audience looks like dept → treat as purpose instead
                if not purpose:
                    purpose = audience
                audience = None

        # Keep suggestions consistent: if no suggestion but we have main value, reuse
        if audience and not audience_suggestion:
            audience_suggestion = audience
        if touchpoint and not touchpoint_suggestion:
            touchpoint_suggestion = touchpoint

        return {
            "survey_type": survey_type,
            "audience": audience,
            "purpose": purpose,
            "touchpoint": touchpoint,
            "audience_suggestion": audience_suggestion,
            "touchpoint_suggestion": touchpoint_suggestion
        }

    except Exception as e:
        print("⚠️ OpenAI analysis failed:", e)
        # On any failure: we will ask all questions again
        return empty_result


# -----------------------
# ROUTES
# -----------------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------- UPDATED QUESTION FLOW (AI-only detection, with TOUCHPOINT) ----------
@app.route("/generate_question_flow", methods=["POST"])
def generate_question_flow():
    """
    AI-first behavior:
    - Analyze user_input for:
        - survey_type (NPS/CSAT/CES/general)
        - audience (dynamic)
        - purpose/topic (dynamic)
        - touchpoint (dynamic)
    - Ask ONLY for the pieces that are missing.
    - If everything is already present → skip follow-up questions and let
      frontend jump directly to sample/template creation.
    """
    data = request.get_json(force=True) or {}
    user_input = (data.get("user_input") or "").strip()

    # Explicit values from payload (user might have selected these in UI already)
    requested_type_raw = (data.get("survey_type") or "").strip().lower()
    audience_from_payload = (data.get("audience") or "").strip()
    purpose_from_payload = (data.get("purpose") or "").strip()
    touchpoint_from_payload = (data.get("touchpoint") or "").strip()

    # --- AI analysis (single call) ---
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

    # --- Survey type precedence: payload > AI > None ---
    survey_type = None
    if requested_type_raw in ["nps", "csat", "ces", "general"]:
        survey_type = requested_type_raw
    elif ai_survey_type in ["nps", "csat", "ces", "general"]:
        survey_type = ai_survey_type
    else:
        survey_type = None  # DO NOT default to general here

    # Type is known only if it is explicitly NPS/CSAT/CES
    type_known = survey_type in ["nps", "csat", "ces"]

    # --- Audience / purpose / touchpoint: payload overrides AI ---
    detected_audience = audience_from_payload or ai_audience
    detected_purpose = purpose_from_payload or ai_purpose
    detected_touchpoint = touchpoint_from_payload or ai_touchpoint

    question_flow = []

    # Ask ONLY for missing fields
    if not type_known:
        question_flow.append({
            "id": "survey_type",
            "q": "Which type of survey would you like to create?",
            "options": ["NPS", "CSAT", "CES", "General / Not sure"]
        })

    if not detected_audience:
        # Base audience options (unchanged IDs/structure)
        base_audience_options = [
            "Customers",
            "Employees",
            "B2B",
            "Clients",
            "Users",
            "Learners",
            "Vendors",
            "Parents",
            "General users"
        ]
        # Inject AI suggestion (if available)
        options = base_audience_options.copy()
        if ai_audience_suggestion:
            suggested_label = f"Suggested: {ai_audience_suggestion}"
            # Put suggestion at the front if not already there
            if suggested_label not in options:
                options.insert(0, suggested_label)

        question_flow.append({
            "id": "audience",
            "q": "Who is your audience for this survey?",
            "options": options
        })

    if not detected_purpose:
        question_flow.append({
            "id": "purpose",
            "q": "What is the main topic or purpose of this survey?",
            "allow_text_input": True
        })

    if not detected_touchpoint:
        # Base touchpoint options
        base_touchpoint_options = [
            "Website",
            "Mobile app",
            "Store visit / Branch visit",
            "Call center / Phone support",
            "Email support",
            "WhatsApp / Chat support",
            "Delivery experience",
            "Onboarding / Signup flow",
            "Billing & payments",
            "Other"
        ]
        options_tp = base_touchpoint_options.copy()
        if ai_touchpoint_suggestion:
            suggested_tp_label = f"Suggested: {ai_touchpoint_suggestion}"
            if suggested_tp_label not in options_tp:
                options_tp.insert(0, suggested_tp_label)

        question_flow.append({
            "id": "touchpoint",
            "q": "Which touchpoint is this survey primarily about?",
            "options": options_tp,
            "allow_text_input": True
        })

    # If NOTHING is missing → skip follow-up questions
    if not question_flow:
        return jsonify({
            "skip_questions": True,
            "question_flow": [],
            "detected_survey_type": survey_type,
            "detected_audience": detected_audience,
            "detected_purpose": detected_purpose,
            "detected_touchpoint": detected_touchpoint,
            "original_user_input": user_input
        })

    # Otherwise, return only the missing questions
    return jsonify({
        "skip_questions": False,
        "question_flow": question_flow,
        "detected_survey_type": survey_type,
        "detected_audience": detected_audience,
        "detected_purpose": detected_purpose,
        "detected_touchpoint": detected_touchpoint,
        "original_user_input": user_input
    })


# ---------- MAIN TEMPLATE GENERATION ----------
@app.route("/generate_survey", methods=["POST"])
def generate_survey():
    data = request.get_json() or {}
    user_input = (data.get("user_input") or "").strip()
    requested_type_raw = (data.get("survey_type") or "").strip().lower()

    if not user_input:
        return jsonify({"error": "Missing user_input"}), 400

    # survey_type: prefer explicit payload, else AI, else general
    survey_type = None
    if requested_type_raw in ["nps", "csat", "ces", "general"]:
        survey_type = requested_type_raw
    else:
        ai_result = analyze_user_input_with_openai(user_input)
        ai_type = ai_result.get("survey_type")
        if ai_type in ["nps", "csat", "ces", "general"]:
            survey_type = ai_type
        else:
            survey_type = "general"

    processed_templates = []

    # Prompt for GPT (templates generation)
    prompt = f"""
You are a CX survey expert.
Generate 3 survey templates for: "{user_input}"
Survey type: "{survey_type.upper()} Survey Template" (NPS/CSAT/CES/GENERAL).

Rules:
- STRICT JSON array ONLY (no explanation).
- Each template object must have keys: "title", "purpose", "duration", "questions".
- duration MUST be around 2–2.5 minutes only (e.g., "2–2.5 mins").
- FIRST question MUST be a rating question that matches survey_type its be on the basis of gnerated survey type.:
    NPS  → 0–10 "likelihood to recommend" → scale_type "nps"
    CSAT → 1–5 or 1–7 "satisfaction"      → scale_type "csat"
    CES  → 1–5 or 1–7 "ease/effort"       → scale_type "ces"
- DO NOT mix NPS/CSAT/CES scales in one template.
- Each template MUST contain 5–7 questions.
- For every question, return an object with at least:
    - "question": text of the question
    - "scale_type": one of ["nps","csat","ces","rating","text","radio","mcq","matrix","file"]
- For any question with "scale_type": "radio" or "mcq", include an "options" array of labels.
- Avoid duplicate question meaning in a single template.
- this is our model totally a survey generator tool give me more accurate result better result.
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            timeout=15,
            messages=[
                {"role": "system", "content": "Return strict JSON only, no explanation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=1500
        )
        text = resp.choices[0].message.content
        try:
            templates = extract_json_array(text)
        except Exception as e:
            print("⚠️ extract_json_array failed:", e)
            templates = []

    except Exception as e:
        print("Generate survey error:", e)
        templates = []

    if not templates:
        print("⚠️ OpenAI template generation returned empty or failed. Using fallback template engine.")
        templates = build_fallback_templates(survey_type, user_input)

    enforced_first_q = get_first_question_for_type(survey_type, user_input)

    # Clean and enforce constraints on each template
    for t in templates:
        t.setdefault("title", f"{survey_type.upper()} Survey Template")
        t.setdefault("purpose", f"Capture responses related to {user_input}")
        t["duration"] = clamp_duration(t.get("duration"))
        t.setdefault("questions", [])

        cleaned_questions = []

        for q in t["questions"]:
            # Collect question text + any provided options
            if isinstance(q, str):
                question_text = q.strip()
                raw_options = []
            else:
                question_text = (
                    q.get("question")
                    or q.get("text")
                    or q.get("label")
                    or ""
                ).strip()
                raw_options = q.get("options") or []

            if not question_text:
                continue

            # Ensure options is list of strings
            options_clean = []
            if isinstance(raw_options, list):
                for o in raw_options:
                    s = str(o).strip()
                    if s:
                        options_clean.append(s)

            detected = infer_scale_type(question_text)

            # Smart scale selection
            if detected in ["nps", "csat", "ces", "rating"]:
                if survey_type in ["nps", "csat", "ces"]:
                    scale = survey_type
                else:
                    scale = detected if detected in ["nps", "csat", "ces"] else "rating"
            else:
                scale = detected if detected in ["text", "radio", "mcq", "matrix", "file"] else "text"

            q_obj = {
                "question": question_text,
                "scale_type": scale
            }

            # RADIO OPTIONS: ensure radio questions have options
            if scale == "radio":
                if options_clean:
                    q_obj["options"] = options_clean
                else:
                    q_obj["options"] = ["Yes", "No", "Not sure"]

            # MCQ options if provided
            if scale == "mcq" and options_clean:
                q_obj["options"] = options_clean

            cleaned_questions.append(q_obj)

        t["questions"] = cleaned_questions

        # Ensure FIRST question is correct
        if not t["questions"] or t["questions"][0]["scale_type"] != (
            survey_type if survey_type in ["nps", "csat", "ces"] else t["questions"][0]["scale_type"]
        ):
            t["questions"].insert(0, enforced_first_q)

        # Guarantee 5–7 questions
        if len(t["questions"]) < 5:
            while len(t["questions"]) < 5:
                t["questions"].append({
                    "question": f"Please share any additional feedback about {user_input}.",
                    "scale_type": "text"
                })
        elif len(t["questions"]) > 7:
            t["questions"] = t["questions"][:7]

        processed_templates.append(t)

    # Normalize template scales
    processed_templates = [
        normalize_template_scales(t, forced_type=survey_type)
        for t in processed_templates
    ]

    # For any radio question still missing options, add default Yes/No options
    for t in processed_templates:
        for q in t.get("questions", []):
            if q.get("scale_type") == "radio" and not q.get("options"):
                q["options"] = ["Yes", "No", "Not sure"]

    # Save to history
    save_history({
        "timestamp": datetime.now().isoformat(),
        "input": user_input,
        "survey_type": survey_type,
        "templates": processed_templates
    })

    return jsonify({
        "surveys": processed_templates,
        "detected_survey_type": survey_type
    })


# ---------- GENERATE MORE ----------
@app.route("/generate_more_surveys", methods=["POST"])
def generate_more_surveys():
    """
    Generate 3 short survey templates based on a focus area.
    Uses ALL wanted context from the first API: generate_question_flow.
    """
    data = request.get_json() or {}

    focus_area = (data.get("focus_area") or "").strip()
    if not focus_area:
        return jsonify({"error": "Missing focus_area"}), 400

    # FRONTEND context from generate_question_flow
    # FRONTEND context from generate_question_flow
    ctx = data.get("context") or {}

    # Extract fields safely
    original_user_input = (ctx.get("original_user_input") or "").strip()
    detected_survey_type = (ctx.get("detected_survey_type") or "").strip()
    detected_audience = (ctx.get("detected_audience") or "").strip()
    detected_purpose = (ctx.get("detected_purpose") or "").strip()
    detected_touchpoint = (ctx.get("detected_touchpoint") or "").strip()

    # Fallback: If context missing OR original_user_input missing → re-extract using AI
    if not ctx or not original_user_input:
        ai_re = analyze_user_input_with_openai(focus_area)

        original_user_input = original_user_input or focus_area
        detected_survey_type = detected_survey_type or ai_re.get("survey_type") or "general"
        detected_audience = detected_audience or ai_re.get("audience") or ""
        detected_purpose = detected_purpose or ai_re.get("purpose") or ""
        detected_touchpoint = detected_touchpoint or ai_re.get("touchpoint") or ""


    # Survey type ALWAYS from first API context
    survey_type = detected_survey_type if detected_survey_type in ["nps", "csat", "ces", "general"] else "general"

    # 🔥 Your new PERFECT prompt
    prompt = f"""
You are a CX survey expert.

ORIGINAL USER REQUEST:
\"\"\"{original_user_input}\"\"\"

Extracted from the FIRST API:
- Audience: {detected_audience}
- Purpose: {detected_purpose}
- Touchpoint: {detected_touchpoint}

Your job:
Generate 3 NEW survey templates that are:
- related to the original user input context
- AND focused on this refinement: "{focus_area}"
- Survey type: "{survey_type.upper()}"

EXAMPLES (do NOT copy, only understand):
- If original request = Café experience survey
  and focus_area = Food
  → Output MUST be: "Café Food Experience Survey Template X"

- If original request = Hospital patient feedback
  and focus_area = Doctor Interaction
  → Output MUST be: "Doctor Interaction Feedback Template X"

STRICT RULES:
- Return ONLY a JSON array of templates.
- Each template MUST have:
    "title"
    "purpose"
    "duration"
    "questions"
- Duration MUST ALWAYS be: "2–2.5 mins"
- EXACT 5 questions per template.
- Questions MUST have:
    "question"
    "scale_type"
    "options" (required only for radio/mcq)

SCALE RULES:
- nps → 0–10 likelihood to recommend
- csat → 1–5 satisfaction
- ces → 1–5 effort/ease
- radio/mcq → MUST include "options"

DO NOT add any extra keys.
DO NOT rename any keys.
DO NOT output text before/after JSON.
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            timeout=15,
            messages=[
                {"role": "system", "content": "You are a survey expert. Output a valid JSON array of templates ONLY. No markdown, no explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=1500
        )
        text = resp.choices[0].message.content

        try:
            templates = extract_json_array(text)
        except Exception as ex:
            print("❌ extract_json_array failed in generate_more_surveys:", ex)
            print("RAW TEXT FROM GPT:\n", repr(text))
            templates = []

        # Normalize scales
        templates = [
            normalize_template_scales(t, forced_type=survey_type)
            for t in templates
        ]

        # Ensure radio questions have options
        for t in templates:
            for q in t.get("questions", []):
                if q.get("scale_type") == "radio" and not q.get("options"):
                    q["options"] = ["Yes", "No", "Not sure"]

        # Clamp duration
        for t in templates:
            t["duration"] = clamp_duration(t.get("duration"))

        return jsonify({
            "templates": templates,
            "focus_area": focus_area,
            "survey_type": survey_type,
            "context_used": ctx  # To debug if needed
        })

    except Exception as e:
        print("Error generate_more:", e)
        return jsonify({"error": str(e)}), 500


# ---------- CUSTOMIZE SELECTED TEMPLATE ----------
@app.route("/customize_selected_template", methods=["POST"])
def customize_selected_template():
    """
    Unified endpoint for survey customization.
    - Handles Add / Remove actions
    - Adds AI-generated questions based on focus/complexity
    - Ensures newly added rating questions match template survey_type
    - Updates scale types
    - Returns next-step customization prompts
    """
    import re

    data = request.get_json() or {}
    templates = data.get("templates", [])
    choice = (data.get("choice") or "").lower()
    action = (data.get("action") or "").lower()
    focus_area = (data.get("focus_area") or "").strip()
    complexity = (data.get("complexity") or "").strip()
    scale_action = (data.get("scale_action") or "").lower()
    scale_changes = data.get("scale_changes", {}) or {}
    remove_input = (data.get("remove_input") or "").strip()

    if not templates or not choice:
        return jsonify({"error": "Missing 'templates' or 'choice'."}), 400

    # Identify selected template
    try:
        index = int(re.search(r"\d+", choice).group()) - 1
        selected = templates[index]
    except Exception:
        return jsonify({"error": "Invalid template choice format."}), 400

    questions = selected.get("questions", [])
    title = selected.get("title", "General Feedback")

    # Detect survey_type from first question
    primary_survey_type = (
        questions[0].get("scale_type", "").lower()
        if questions else "general"
    )

    # ---------------------- STEP 1: ADD OR REMOVE QUESTIONS ----------------------
    ai_questions_added = False  # Track if AI-generated questions were added

    if action in ["add", "remove"]:

        # ----- ADDing questions -----
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
                    model="gpt-3.5-turbo",
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

                # Local scale type inference for added questions
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

                    # Force match with template survey type for rating questions
                    if inferred in ["nps", "csat", "ces", "rating"]:
                        final_scale = (
                            primary_survey_type
                            if primary_survey_type in ["nps", "csat", "ces"]
                            else inferred
                        )
                    else:
                        final_scale = inferred

                    q_obj = {"question": q, "scale_type": final_scale}

                    # RADIO OPTIONS for added questions
                    if final_scale == "radio":
                        q_obj["options"] = ["Yes", "No", "Not sure"]

                    new_qs.append(q_obj)

                questions.extend(new_qs)
                ai_questions_added = True

            except Exception as e:
                print(f"⚠️ AI question generation failed (add): {e}")
                return jsonify({"error": f"AI customization failed: {str(e)}"}), 500

        # ----- REMOVING questions -----
        elif action == "remove":
            if not remove_input:
                return jsonify({"message": "Specify which question to remove (e.g., Q2 or keyword)."}), 400

            remove_targets = [r.strip().lower() for r in remove_input.split(",") if r.strip()]
            to_remove = []

            for i, q in enumerate(questions):
                q_text = q["question"].lower()
                for target in remove_targets:
                    if target == f"q{i+1}".lower() or target in q_text:
                        to_remove.append(i)
                        break

            if not to_remove:
                return jsonify({"message": f"No question found matching '{remove_input}'."}), 404

            for i in sorted(set(to_remove), reverse=True):
                questions.pop(i)

            return jsonify({
                "message": f"🗑️ Removed {len(to_remove)} question(s) successfully.",
                "ask_add": True,
                "customization_questions": [{
                    "question": "Would you like to add any questions to this template now?",
                    "options": ["Yes", "No"]
                }],
                "selected_template": selected
            })

    # ---------------------- STEP 2: SCALE TYPE CUSTOMIZATION ----------------------
    if scale_action == "yes" and scale_changes:
        for key, new_scale in scale_changes.items():
            if key.startswith("q") and key[1:].isdigit():
                idx = int(key[1:]) - 1
                if 0 <= idx < len(questions):
                    questions[idx]["scale_type"] = new_scale
                    # ensure radio options
                    if new_scale == "radio" and not questions[idx].get("options"):
                        questions[idx]["options"] = ["Yes", "No", "Not sure"]

    selected["questions"] = questions

    # ---------------------- STEP 3: NEXT CUSTOMIZATION QUESTIONS ----------------------
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
        "message": "✅ Template customization completed successfully.",
        "selected_template": selected,
        "customization_questions": customization_qs
    })


# ---------- FINALIZE ----------
@app.route("/finalize_template", methods=["POST"])
def finalize_template():
    data = request.get_json() or {}
    final_template = data.get("final_template")
    if not final_template:
        return jsonify({"error": "Missing final_template"}), 400

    template_id = datetime.now().strftime("%Y%m%d%H%M%S")
    os.makedirs("finalized_templates", exist_ok=True)
    file_path = os.path.join("finalized_templates", f"template_{template_id}.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(final_template, f, ensure_ascii=False, indent=2)

    save_history({
        "timestamp": datetime.now().isoformat(),
        "action": "finalize",
        "path": file_path,
        "template": final_template
    })

    return jsonify({
        "message": "Template finalized successfully.",
        "template_id": template_id,
        "path": file_path
    })


# -----------------------
# RUN APP
# -----------------------
if __name__ == "__main__":
    env = os.getenv("FLASK_ENV", "development")
    if env == "production":
        from waitress import serve
        print("Starting production server with Waitress on http://0.0.0.0:5000 ...")
        serve(app, host="0.0.0.0", port=5000, threads=8)
    else:
        print("Starting development server...")
        app.run(host="0.0.0.0", port=5000, debug=True)
