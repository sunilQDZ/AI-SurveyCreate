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


# def detect_survey_type(text: str) -> str:
#     """
#     Lightweight detection of NPS / CSAT / CES from text.
#     """
#     t = (text or "").lower()
#     if any(k in t for k in [
#         "nps", "recommend", "likelihood to recommend",
#         "promoter", "detractor", "likely to recommend"
#     ]):
#         return "nps"
#     if any(k in t for k in [
#         "csat", "satisfied", "satisfaction", "how satisfied"
#     ]):
#         return "csat"
#     if any(k in t for k in [
#         "ces", "effort", "easy", "ease", "how easy"
#     ]):
#         return "ces"
#     return "general"


# def normalize_survey_type(s_type: str | None, user_input: str = "") -> str:
#     if not s_type:
#         return detect_survey_type(user_input)
#     s = s_type.strip().lower()
#     if s in ("nps", "net promoter", "net promoter score"):
#         return "nps"
#     if s in ("csat", "customer satisfaction"):
#         return "csat"
#     if s in ("ces", "customer effort"):
#         return "ces"
#     return detect_survey_type(user_input)


# def get_first_question_for_type(survey_type: str, topic_hint: str | None = None) -> dict:
#     """
#     First question + scale_type per survey type.
#     NPS → 0–10 recommendation
#     CSAT → 1–5 satisfaction  (other ranges like 1–3 or 1–7 can be handled by UI)
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
#         "nps": ["nps", "radio", "mcq", "text","matrix" ,"file"],
#         "csat": ["csat", "radio", "mcq", "text","matrix" ,"file"],
#         "ces": ["ces", "radio", "mcq", "text","matrix" ,"file"],
#         "general": ALLOWED_SCALE_TYPES,
#     }.get(forced_type, ALLOWED_SCALE_TYPES)

#     for q in template.get("questions", []):
#         inferred = infer_scale_type(q.get("question", ""))

#         if inferred not in allowed_by_type:
#             # Force correct scale type for primary rating
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



# def should_skip_question(q_dict: dict, user_input: str) -> bool:
#     """
#     Avoid repeating audience/touchpoint/product that user already specified in the query.
#     Safely handles questions with or without 'q' key.
#     """
#     t = (user_input or "").lower()

#     question_text = q_dict.get("q")
#     if not isinstance(question_text, str):
#         return False  # Safe: ignore skipping for non-text questions

#     q = question_text.lower()

#     audience_keywords = ["customer", "customers", "employee", "employees", "staff",
#                          "vendor", "vendors", "manager", "managers"]
#     touchpoint_keywords = ["purchase", "checkout", "support", "delivery", "website",
#                            "app", "branch", "store", "call center"]
#     product_keywords = ["product", "service", "subscription", "plan", "software", "app", "portal"]

#     # Skip repeated context
#     if "audience" in q and any(k in t for k in audience_keywords):
#         return True
#     if "touchpoint" in q and any(k in t for k in touchpoint_keywords):
#         return True
#     if "product" in q and any(k in t for k in product_keywords):
#         return True

#     return False



# # -----------------------
# # ROUTES
# # -----------------------
# @app.route("/")
# def home():
#     return render_template("index.html")


# # ---------- QUESTION FLOW (hybrid: predefined + AI) ----------
# @app.route("/generate_question_flow", methods=["POST"])
# def generate_question_flow():
#     data = request.get_json(force=True) or {}
#     user_input = (data.get("user_input") or "").strip()
#     survey_type = normalize_survey_type(data.get("survey_type"), user_input)

#     def should_ask_survey_type_q(text):
#         t = text.lower()
#         return not any(k in t for k in [
#             "nps", "net promoter", "recommend",
#             "csat", "satisfaction",
#             "ces", "effort", "how easy"
#         ])

#     flow = []

#     # Ask survey type only if not already implied in user_input
#     if should_ask_survey_type_q(user_input):
#         flow.append({
#             "q": "Which type of survey would you like to create?",
#             "options": ["NPS", "CSAT", "CES", "Not sure"]
#         })

#     # Base mandatory setup questions
#     flow += [
#         {
#             "q": "Who is your audience?",
#             "options": ["Customers", "Employees", "Vendors", "General users"]
#         },
#         {
#             "q": "What is the main objective of your survey?",
#             "options": ["Understanding loyalty", "Improving satisfaction", "Reducing effort", "General feedback"]
#         }
#     ]

#     # ---------------- PREDEFINED QUESTIONS based on survey type ----------------

#     predefined_map = {
#         "nps": [
#             {
#                 "q": "Which product/service is being evaluated for recommendation?",
#                 "options": ["Product", "Service", "Both"]
#             },
#             {
#                 "q": "Which touchpoint drives recommendation the most?",
#                 "options": ["Website/App", "Support Interaction", "Purchase Experience", "Store Visit"]
#             },
#             {
#                 "q": "What type of audience are you measuring loyalty for?",
#                 "options": ["New users", "Existing customers", "Churn-risk customers", "All customers"]
#             },
#             {
#                 "q": "Is this survey focused on a specific geographic region?",
#                 "options": ["Yes", "No"]
#             }
#         ],
#         "csat": [
#             {
#                 "q": "Which aspect's satisfaction are you measuring?",
#                 "options": ["Product Quality", "Service Experience", "Customer Support", "Delivery/Turnaround"]
#             },
#             {
#                 "q": "Is this survey for a specific interaction or overall experience?",
#                 "options": ["Specific interaction", "Overall experience"]
#             },
#             {
#                 "q": "Is the survey for a particular feature or service area?",
#                 "options": ["Yes", "No"]
#             },
#             {
#                 "q": "Are you focusing on a specific customer segment?",
#                 "options": ["Retail", "Enterprise", "Internal Users", "All"]
#             }
#         ],
#         "ces": [
#             {
#                 "q": "Which process or task is being evaluated for ease?",
#                 "options": ["Signup", "Support Resolution", "Usage/Operations", "Checkout / Payment"]
#             },
#             {
#                 "q": "Is this task self-service or assisted?",
#                 "options": ["Self-service", "Assisted"]
#             },
#             {
#                 "q": "Are there known steps where effort increases?",
#                 "options": ["Yes, multiple", "Some", "None"]
#             },
#             {
#                 "q": "Which channel did the customer use?",
#                 "options": ["Mobile App", "Website", "Call Center", "In-Store"]
#             }
#         ],
#         "general": [
#             {
#                 "q": "Which part of customer journey is being evaluated?",
#                 "options": ["Pre-purchase", "Purchase", "Post-purchase", "Whole journey"]
#             },
#             {
#                 "q": "What type of audience is being targeted?",
#                 "options": ["Customers", "Employees", "Vendors", "General Users"]
#             }
#         ]
#     }


#     survey_specific_questions = predefined_map.get(survey_type, predefined_map["general"])

#     for q in survey_specific_questions[:4]:
#         flow.append(q)

#     # ---------------- Hybrid AI question ----------------
#     try:
#         ai_prompt = f"""
# Suggest 1 short contextual question for this survey.

# User topic: "{user_input}"
# Survey type: "{survey_type.upper()}"

# Rules:
# - Question must be focused and measurable.
# - Do NOT ask again about audience, purpose, duration, or NPS/CSAT/CES type.
# - Return only the question text, no numbering.
# """
#         ai_resp = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": ai_prompt}],
#             temperature=0.4,
#             max_tokens=50
#         )

#         qtext = ai_resp["choices"][0]["message"]["content"].strip()
#         if qtext:
#             flow.append({"q": qtext})
#     except Exception as e:
#         print("Hybrid question failure:", e)

#     # Duration choice
#     flow.append({
#         "q": "Would you like to add purpose & estimated duration in the survey?",
#         "options": ["Yes", "No"]
#     })

#     # Skip repetitive context questions
#     flow = [q for q in flow if not should_skip_question(q, user_input)]

#     return jsonify({
#         "question_flow": flow,
#         "detected_survey_type": survey_type,
#         "original_user_input": user_input
#     })



# # ---------- MAIN TEMPLATE GENERATION ----------
# @app.route("/generate_survey", methods=["POST"])
# def generate_survey():
#     data = request.get_json() or {}
#     user_input = (data.get("user_input") or "").strip()
#     requested_type = data.get("survey_type")

#     if not user_input:
#         return jsonify({"error": "Missing user_input"}), 400

#     survey_type = normalize_survey_type(requested_type, user_input)
#     processed_templates = []

#     prompt = f"""
# You are a CX survey expert.
# Generate 4 survey templates for: "{user_input}"
# Survey type: {survey_type.upper()}.

# Rules:
# - STRICT JSON array ONLY (no explanation).
# - Each template object must have keys: "title", "purpose", "duration", "questions".
# - duration MUST be around 2–2.5 minutes only (e.g., "2–2.5 mins").
# - FIRST question MUST be a rating question that matches survey_type scale:
#     NPS  → 0–10 "likelihood to recommend" → scale_type "nps"
#     CSAT → 1–5 or 1–7 "satisfaction"      → scale_type "csat"
#     CES  → 1–5 or 1–7 "ease/effort"       → scale_type "ces"
# - DO NOT mix NPS/CSAT/CES scales in one template.
# - Each template MUST contain 5–7 questions.
# - For every question, return an object with at least:
#     - "question": text of the question
#     - (You may include other keys, but they will be ignored.)
# - Use these scale_type values ONLY:
#     - "nps", "csat", "ces" for numeric rating questions
#     - "text", "radio", "mcq", "matrix", "file" for non-rating questions
# - Use "radio" for yes/no or single-choice options.
# - Use "mcq" when multiple selections are expected.
# - Use "matrix" for "rate the following" style multi-row rating.
# - Use "file" only if asking to upload/attach evidence.
# - Avoid duplicate question meaning in a single template.
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

#     for t in templates:
#         # duration & questions default
#         t.setdefault("title", f"{survey_type.upper()} Survey Template")
#         t.setdefault("purpose", f"Capture responses related to {user_input}")
#         t["duration"] = clamp_duration(t.get("duration"))
#         t.setdefault("questions", [])

#         cleaned_questions = []

#         for q in t["questions"]:
#             # Accept either string or object
#             if isinstance(q, str):
#                 question_text = q.strip()
#             else:
#                 question_text = (
#                     q.get("question")
#                     or q.get("text")
#                     or q.get("label")
#                     or ""
#                 ).strip()

#             if not question_text:
#                 continue

#             detected = infer_scale_type(question_text)

#             # If the question is a rating-style question,
#             # force it to the selected survey_type (if NPS/CSAT/CES).
#             if detected in ["nps", "csat", "ces", "rating"]:
#                 if survey_type in ["nps", "csat", "ces"]:
#                     scale = survey_type
#                 else:
#                     # fallback when survey_type is "general"
#                     scale = detected if detected in ["nps", "csat", "ces"] else "rating"
#             else:
#                 # Non-rating → keep as is if valid, else fallback to text
#                 if detected in ["text", "radio", "mcq", "matrix", "file"]:
#                     scale = detected
#                 else:
#                     scale = "text"


#             cleaned_questions.append({
#                 "question": question_text,
#                 "scale_type": scale
#             })

#         t["questions"] = cleaned_questions

#         # Ensure correct FIRST rating question for selected survey_type
#         if not t["questions"] or t["questions"][0]["scale_type"] != (
#             survey_type if survey_type in ["nps", "csat", "ces"] else t["questions"][0]["scale_type"]
#         ):
#             # Insert enforced first rating Q
#             t["questions"].insert(0, enforced_first_q)

#         # Guarantee 5–7 questions per template
#         if len(t["questions"]) < 5:
#             while len(t["questions"]) < 5:
#                 t["questions"].append({
#                     "question": f"Please share any additional feedback about {user_input}.",
#                     "scale_type": "text"
#                 })
#         elif len(t["questions"]) > 7:
#             t["questions"] = t["questions"][:7]

#         processed_templates.append(t)
#         # Extra safety: ensure each template's scales are consistent with survey_type
#     processed_templates = [
#         normalize_template_scales(t, forced_type=survey_type)
#         for t in processed_templates
#     ]

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
#     Generate a few more focused templates when user asks for variations.
#     Uses NPS / CSAT / CES orientation as well.
#     """
#     data = request.get_json() or {}
#     focus_area = (data.get("focus_area") or "").strip()
#     requested_type = data.get("survey_type")
#     if not focus_area:
#         return jsonify({"error": "Missing focus_area"}), 400

#     survey_type = normalize_survey_type(requested_type, focus_area)

#     prompt = f"""
# You are a CX survey expert.
# Generate 3 short survey templates focused on: "{focus_area}" for survey type "{survey_type.upper()}" (NPS/CSAT/CES).
# Rules:
# - Each template should have: "title", "purpose", "duration", and exactly 4 questions.
# - Duration must be around 2–2.5 minutes only.
# - Each question must have "question" and "scale_type" from: {ALLOWED_SCALE_TYPES}.
# - Use NPS 0–10 scale questions only when scale_type is "nps".
# - Use CSAT 1–5 satisfaction questions when scale_type is "csat".
# - Use CES 1–5 ease/effort questions when scale_type is "ces".
# Return ONLY a JSON array.
# """

#     try:
#         resp = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.6,
#             max_tokens=700
#         )
#         text = resp["choices"][0]["message"]["content"]
#         try:
#             templates = extract_json_array(text)
#         except Exception:
#             templates = []
#         templates = [normalize_template_scales(t, forced_type=survey_type) for t in templates]
#         for t in templates:
#             t["duration"] = clamp_duration(t.get("duration"))
#         return jsonify({
#             "templates": templates,
#             "focus_area": focus_area,
#             "survey_type": survey_type
#         })
#     except Exception as e:
#         print("Error generate_more:", e)
#         return jsonify({"error": str(e)}), 500
    
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
#     import openai
#     from flask import request, jsonify

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

#                 # Infer scale type (same logic as existing code)
#                 def infer_scale_type(question: str) -> str:
#                     q = question.lower()
#                     if "nps" in q or "recommend" in q or "likely" in q:
#                         return "nps"
#                     if "satisfied" in q or "csat" in q:
#                         return "csat"
#                     if "ease" in q or "ces" in q:
#                         return "ces"
#                     if "rate" in q or "rating" in q or "score" in q:
#                         return "rating"
#                     if any(x in q for x in ["why", "describe", "explain", "feedback", "suggest"]):
#                         return "text"
#                     if any(x in q for x in ["choose", "select", "pick one"]):
#                         return "radio"
#                     if any(x in q for x in ["multiple", "select all", "choose all"]):
#                         return "mcq"
#                     if "matrix" in q or "compare" in q:
#                         return "matrix"
#                     if "upload" in q or "file" in q:
#                         return "file"
#                     return "rating"

#                 # ✓ NEW FIX: Force scale to match existing survey type
#                 new_qs = []
#                 for q in ai_questions[:4]:
#                     inferred = infer_scale_type(q)

#                     if inferred in ["nps", "csat", "ces", "rating"]:
#                         scale_final = (
#                             primary_survey_type
#                             if primary_survey_type in ["nps", "csat", "ces"]
#                             else inferred
#                         )
#                     else:
#                         scale_final = inferred

#                     new_qs.append({"question": q, "scale_type": scale_final})

#                 questions.extend(new_qs)
#                 ai_questions_added = True

#             except Exception as e:
#                 print(f"⚠️ AI question generation failed (add): {e}")
#                 return jsonify({"error": f"AI customization failed: {str(e)}"}), 500

#         elif action == "remove":
#             if not remove_input:
#                 return jsonify({"message": "Specify which question to remove (e.g., Q2 or keyword)."}), 400

#             remove_targets = [r.strip().lower() for r in remove_input.split(",") if r.strip()]

#             to_remove = []
#             for i, q in enumerate(questions):
#                 for target in remove_targets:
#                     if target == f"q{i+1}".lower() or target in q["question"].lower():
#                         to_remove.append(i)
#                         break

#             if not to_remove:
#                 return jsonify({"message": f"No question found matching '{remove_input}'."}), 404

#             for i in sorted(set(to_remove), reverse=True):
#                 removed_q = questions.pop(i)

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

#     selected["questions"] = questions

#     # ---------------------- STEP 3: NEXT CUSTOMIZATION QUESTIONS ----------------------
#     customization_qs = []

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
# # RUN
# # -----------------------
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=True)

# from flask import Flask, request, jsonify, render_template
# import json, os, re
# from datetime import datetime
# import difflib
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


# def detect_survey_type(text: str) -> str:
#     """
#     Lightweight detection of NPS / CSAT / CES from text.
#     """
#     t = (text or "").lower()
#     if any(k in t for k in [
#         "nps", "recommend", "likelihood to recommend",
#         "promoter", "detractor", "likely to recommend"
#     ]):
#         return "nps"
#     if any(k in t for k in [
#         "csat", "satisfied", "satisfaction", "how satisfied"
#     ]):
#         return "csat"
#     if any(k in t for k in [
#         "ces", "effort", "easy", "ease", "how easy"
#     ]):
#         return "ces"
#     return "general"


# def normalize_survey_type(s_type: str | None, user_input: str = "") -> str:
#     if not s_type:
#         return detect_survey_type(user_input)
#     s = s_type.strip().lower()
#     if s in ("nps", "net promoter", "net promoter score"):
#         return "nps"
#     if s in ("csat", "customer satisfaction"):
#         return "csat"
#     if s in ("ces", "customer effort"):
#         return "ces"
#     return detect_survey_type(user_input)


# def get_first_question_for_type(survey_type: str, topic_hint: str | None = None) -> dict:
#     """
#     First question + scale_type per survey type.
#     NPS → 0–10 recommendation
#     CSAT → 1–5 satisfaction  (other ranges like 1–3 or 1–7 can be handled by UI)
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
#             # Force correct scale type for primary rating
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


# # ---------- NEW HELPERS: audience + purpose detection (without AI) ----------

# AUDIENCE_CANONICAL = {
#     "customer": "Customers",
#     "customers": "Customers",
#     "client": "Customers",
#     "clients": "Customers",
#     "employee": "Employees",
#     "employees": "Employees",
#     "staff": "Staff",
#     "user": "Users",
#     "users": "Users",
#     "student": "Students",
#     "students": "Students",
#     "teacher": "Teachers",
#     "teachers": "Teachers",
#     "parent": "Parents",
#     "parents": "Parents",
#     "vendor": "Vendors",
#     "vendors": "Vendors",
# }


# def detect_audience(user_input: str) -> str | None:
#     """
#     Detect audience from free-text using exact + fuzzy matching.
#     Returns a human-readable audience label (e.g., "Customers") or None.
#     """
#     if not user_input:
#         return None

#     text = user_input.lower()
#     tokens = re.findall(r"[a-zA-Z]+", text)

#     found_labels: list[str] = []

#     # 1) Exact matches
#     for tok in tokens:
#         if tok in AUDIENCE_CANONICAL:
#             found_labels.append(AUDIENCE_CANONICAL[tok])

#     # 2) Fuzzy matches for typos
#     if not found_labels:
#         keys = list(AUDIENCE_CANONICAL.keys())
#         for tok in tokens:
#             matches = difflib.get_close_matches(tok, keys, n=1, cutoff=0.8)
#             if matches:
#                 found_labels.append(AUDIENCE_CANONICAL[matches[0]])

#     if not found_labels:
#         return None

#     # Priority order if multiple detected
#     priority = [
#         "Customers",
#         "Employees",
#         "Students",
#         "Teachers",
#         "Parents",
#         "Vendors",
#         "Staff",
#         "Users",
#     ]
#     for p in priority:
#         if p in found_labels:
#             return p

#     return found_labels[0]


# PURPOSE_MARKERS = [
#     "survey on",
#     "survey for",
#     "survey about",
#     "survey of",
#     "survey regarding",
# ]


# def extract_purpose(user_input: str) -> str | None:
#     """
#     Extract purpose/topic from phrases like:
#     - "survey on education"
#     - "survey for customer support"
#     - "survey of education department as a customer"
#     """
#     if not user_input:
#         return None

#     text_lower = user_input.lower()

#     for marker in PURPOSE_MARKERS:
#         idx = text_lower.find(marker)
#         if idx != -1:
#             start = idx + len(marker)
#             # Use original text slice to preserve case
#             raw = user_input[start:].strip()

#             # Remove trailing audience phrases like "as a customer", "from customers"
#             lower_raw = raw.lower()
#             for splitter in [" as ", " for ", " from ", " by "]:
#                 sidx = lower_raw.find(splitter)
#                 if sidx != -1:
#                     raw = raw[:sidx].strip()
#                     lower_raw = raw.lower()
#                     break

#             # If still too short, ignore
#             if len(raw) < 2:
#                 return None
#             return raw

#     return None


# def should_skip_question(q_dict: dict, user_input: str) -> bool:
#     """
#     OLD helper – kept for compatibility.
#     Currently not used in the new flow, but retained in case you
#     want to re-use it later.
#     """
#     t = (user_input or "").lower()

#     question_text = q_dict.get("q")
#     if not isinstance(question_text, str):
#         return False  # Safe: ignore skipping for non-text questions

#     q = question_text.lower()

#     audience_keywords = ["customer", "customers", "employee", "employees", "staff",
#                          "vendor", "vendors", "manager", "managers"]
#     touchpoint_keywords = ["purchase", "checkout", "support", "delivery", "website",
#                            "app", "branch", "store", "call center"]
#     product_keywords = ["product", "service", "subscription", "plan", "software", "app", "portal"]

#     # Skip repeated context
#     if "audience" in q and any(k in t for k in audience_keywords):
#         return True
#     if "touchpoint" in q and any(k in t for k in touchpoint_keywords):
#         return True
#     if "product" in q and any(k in t for k in product_keywords):
#         return True

#     return False


# # -----------------------
# # ROUTES
# # -----------------------
# @app.route("/")
# def home():
#     return render_template("index.html")


# # ---------- UPDATED QUESTION FLOW (smart: only missing questions) ----------
# @app.route("/generate_question_flow", methods=["POST"])
# def generate_question_flow():
#     """
#     New behavior:
#     - Analyze user_input for:
#         - survey_type (NPS/CSAT/CES/general)
#         - audience (customers/employees/students/teachers/vendors/etc.)
#         - purpose/topic (e.g. "education department", "customer support")
#     - Ask ONLY for the pieces that are missing.
#     - If everything is already present → skip follow-up questions and let
#       frontend jump directly to sample/template creation.
#     """
#     data = request.get_json(force=True) or {}
#     user_input = (data.get("user_input") or "").strip()

#     requested_type_raw = (data.get("survey_type") or "").strip().lower()

#     survey_type = normalize_survey_type(requested_type_raw, user_input)

#     # Type is known only if we explicitly detect NPS/CSAT/CES
#     type_known = survey_type in ["nps", "csat", "ces"]


#     # 2) Audience & purpose detection (new logic)
#     audience_from_payload = (data.get("audience") or "").strip()
#     purpose_from_payload = (data.get("purpose") or "").strip()

#     detected_audience = audience_from_payload or detect_audience(user_input)
#     detected_purpose = purpose_from_payload or extract_purpose(user_input)

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
#                 "Students",
#                 "Teachers",
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
#     requested_type = data.get("survey_type")

#     if not user_input:
#         return jsonify({"error": "Missing user_input"}), 400

#     # Detect / normalize survey type
#     survey_type = normalize_survey_type(requested_type, user_input)
#     processed_templates = []

#     # Prompt for GPT (templates generation)
#     prompt = f"""
# You are a CX survey expert.
# Generate 3 survey templates for: "{user_input}"
# Survey type: {survey_type.upper()}.

# Rules:
# - STRICT JSON array ONLY (no explanation).
# - Each template object must have keys: "title", "purpose", "duration", "questions".
# - duration MUST be around 2–2.5 minutes only (e.g., "2–2.5 mins").
# - FIRST question MUST be a rating question that matches survey_type scale:
#     NPS  → 0–10 "likelihood to recommend" → scale_type "nps"
#     CSAT → 1–5 or 1–7 "satisfaction"      → scale_type "csat"
#     CES  → 1–5 or 1–7 "ease/effort"       → scale_type "ces"
# - DO NOT mix NPS/CSAT/CES scales in one template.
# - Each template MUST contain 5–7 questions.
# - For every question, return an object with at least:
#     - "question": text of the question
# - Use these scale_type values ONLY:
#     - "nps", "csat", "ces" for numeric rating questions
#     - "text", "radio", "mcq", "matrix", "file" for non-rating questions
# - Avoid duplicate question meaning in a single template.
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
#             if isinstance(q, str):
#                 question_text = q.strip()
#             else:
#                 question_text = (
#                     q.get("question")
#                     or q.get("text")
#                     or q.get("label")
#                     or ""
#                 ).strip()

#             if not question_text:
#                 continue

#             detected = infer_scale_type(question_text)

#             # Smart scale selection
#             if detected in ["nps", "csat", "ces", "rating"]:
#                 if survey_type in ["nps", "csat", "ces"]:
#                     scale = survey_type
#                 else:
#                     scale = detected if detected in ["nps", "csat", "ces"] else "rating"
#             else:
#                 scale = detected if detected in ["text", "radio", "mcq", "matrix", "file"] else "text"

#             cleaned_questions.append({
#                 "question": question_text,
#                 "scale_type": scale
#             })

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
#     """
#     data = request.get_json() or {}
#     focus_area = (data.get("focus_area") or "").strip()
#     requested_type = data.get("survey_type")

#     if not focus_area:
#         return jsonify({"error": "Missing focus_area"}), 400

#     survey_type = normalize_survey_type(requested_type, focus_area)

#     prompt = f"""
# You are a CX survey expert.
# Generate 3 short survey templates focused on: "{focus_area}" for survey type "{survey_type.upper()}" (NPS/CSAT/CES).
# Rules:
# - Each template should have: "title", "purpose", "duration", and exactly 4 questions.
# - Duration must be around 2–2.5 minutes only.
# - Each question must have "question" and "scale_type".
# - Use NPS 0–10 scale questions only when scale_type is "nps".
# - Use CSAT 1–5 satisfaction questions when scale_type is "csat".
# - Use CES 1–5 ease/effort questions when scale_type is "ces".
# Return ONLY a JSON array.
# """

#     try:
#         resp = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.6,
#             max_tokens=700
#         )
#         text = resp["choices"][0]["message"]["content"]

#         try:
#             templates = extract_json_array(text)
#         except Exception:
#             templates = []

#         templates = [
#             normalize_template_scales(t, forced_type=survey_type)
#             for t in templates
#         ]

#         for t in templates:
#             t["duration"] = clamp_duration(t.get("duration"))

#         return jsonify({
#             "templates": templates,
#             "focus_area": focus_area,
#             "survey_type": survey_type
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
#         import re
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
#                     if any(x in lower_q for x in ["choose", "select", "pick one"]):
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

#                     new_qs.append({"question": q, "scale_type": final_scale})

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
#                 removed_q = questions.pop(i)

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
## full working code below
# from flask import Flask, request, jsonify, render_template
# import json, os, re
# from datetime import datetime
# import difflib
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


# def detect_survey_type(text: str) -> str:
#     """
#     Lightweight detection of NPS / CSAT / CES from text.
#     """
#     t = (text or "").lower()
#     if any(k in t for k in [
#         "nps", "recommend", "likelihood to recommend",
#         "promoter", "detractor", "likely to recommend"
#     ]):
#         return "nps"
#     if any(k in t for k in [
#         "csat", "satisfied", "satisfaction", "how satisfied"
#     ]):
#         return "csat"
#     if any(k in t for k in [
#         "ces", "effort", "easy", "ease", "how easy"
#     ]):
#         return "ces"
#     return "general"


# def normalize_survey_type(s_type: str | None, user_input: str = "") -> str:
#     if not s_type:
#         return detect_survey_type(user_input)
#     s = s_type.strip().lower()
#     if s in ("nps", "net promoter", "net promoter score"):
#         return "nps"
#     if s in ("csat", "customer satisfaction"):
#         return "csat"
#     if s in ("ces", "customer effort"):
#         return "ces"
#     return detect_survey_type(user_input)


# def get_first_question_for_type(survey_type: str, topic_hint: str | None = None) -> dict:
#     """
#     First question + scale_type per survey type.
#     NPS → 0–10 recommendation
#     CSAT → 1–5 satisfaction  (other ranges like 1–3 or 1–7 can be handled by UI)
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
#             # Force correct scale type for primary rating
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


# # ---------- NEW HELPERS: audience + purpose detection (without AI) ----------

# AUDIENCE_CANONICAL = {
#     "customer": "Customers",
#     "customers": "Customers",
#     "client": "Customers",
#     "clients": "Customers",
#     "employee": "Employees",
#     "employees": "Employees",
#     "staff": "Staff",
#     "user": "Users",
#     "users": "Users",
#     "student": "Students",
#     "students": "Students",
#     "teacher": "Teachers",
#     "teachers": "Teachers",
#     "parent": "Parents",
#     "parents": "Parents",
#     "vendor": "Vendors",
#     "vendors": "Vendors",
# }


# def detect_audience(user_input: str) -> str | None:
#     """
#     Detect audience from free-text using exact + fuzzy matching.
#     Returns a human-readable audience label (e.g., "Customers") or None.
#     """
#     if not user_input:
#         return None

#     text = user_input.lower()
#     tokens = re.findall(r"[a-zA-Z]+", text)

#     found_labels: list[str] = []

#     # 1) Exact matches
#     for tok in tokens:
#         if tok in AUDIENCE_CANONICAL:
#             found_labels.append(AUDIENCE_CANONICAL[tok])

#     # 2) Fuzzy matches for typos
#     if not found_labels:
#         keys = list(AUDIENCE_CANONICAL.keys())
#         for tok in tokens:
#             matches = difflib.get_close_matches(tok, keys, n=1, cutoff=0.8)
#             if matches:
#                 found_labels.append(AUDIENCE_CANONICAL[matches[0]])

#     if not found_labels:
#         return None

#     # Priority order if multiple detected
#     priority = [
#         "Customers",
#         "Employees",
#         "Students",
#         "Teachers",
#         "Parents",
#         "Vendors",
#         "Staff",
#         "Users",
#     ]
#     for p in priority:
#         if p in found_labels:
#             return p

#     return found_labels[0]


# PURPOSE_MARKERS = [
#     "survey on",
#     "survey for",
#     "survey about",
#     "survey of",
#     "survey regarding",
# ]


# def extract_purpose(user_input: str) -> str | None:
#     """
#     Extract purpose/topic from phrases like:
#     - "survey on education"
#     - "survey for customer support"
#     - "survey of education department as a customer"
#     """
#     if not user_input:
#         return None

#     text_lower = user_input.lower()

#     for marker in PURPOSE_MARKERS:
#         idx = text_lower.find(marker)
#         if idx != -1:
#             start = idx + len(marker)
#             # Use original text slice to preserve case
#             raw = user_input[start:].strip()

#             # Remove trailing audience phrases like "as a customer", "from customers"
#             lower_raw = raw.lower()
#             for splitter in [" as ", " for ", " from ", " by "]:
#                 sidx = lower_raw.find(splitter)
#                 if sidx != -1:
#                     raw = raw[:sidx].strip()
#                     lower_raw = raw.lower()
#                     break

#             # If still too short, ignore
#             if len(raw) < 2:
#                 return None
#             return raw

#     return None


# def should_skip_question(q_dict: dict, user_input: str) -> bool:
#     """
#     OLD helper – kept for compatibility.
#     Currently not used in the new flow, but retained in case you
#     want to re-use it later.
#     """
#     t = (user_input or "").lower()

#     question_text = q_dict.get("q")
#     if not isinstance(question_text, str):
#         return False  # Safe: ignore skipping for non-text questions

#     q = question_text.lower()

#     audience_keywords = ["customer", "customers", "employee", "employees", "staff",
#                          "vendor", "vendors", "manager", "managers"]
#     touchpoint_keywords = ["purchase", "checkout", "support", "delivery", "website",
#                            "app", "branch", "store", "call center"]
#     product_keywords = ["product", "service", "subscription", "plan", "software", "app", "portal"]

#     # Skip repeated context
#     if "audience" in q and any(k in t for k in audience_keywords):
#         return True
#     if "touchpoint" in q and any(k in t for k in touchpoint_keywords):
#         return True
#     if "product" in q and any(k in t for k in product_keywords):
#         return True

#     return False


# # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# # NEW: TOUCHPOINT DETECTION
# # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

# TOUCHPOINT_KEYWORDS = {
#     "pre sales": "Pre-Sales",
#     "pre-sale": "Pre-Sales",
#     "presales": "Pre-Sales",
#     "before purchase": "Pre-Sales",
#     "initial inquiry": "Pre-Sales",

#     "during sale": "During Sale",
#     "during purchase": "During Sale",
#     "purchase journey": "During Sale",
#     "buying process": "During Sale",

#     "post sale": "Post-Sale",
#     "post-sale": "Post-Sale",
#     "after sale": "Post-Sale",
#     "after purchase": "Post-Sale",

#     "support": "After Support",
#     "customer support": "After Support",
#     "after support": "After Support",
#     "service": "After Support",
#     "service request": "After Support",
# }


# def detect_touchpoint(user_input: str) -> str | None:
#     """
#     Detect a common CX touchpoint from text.
#     Examples: Pre-Sales, During Sale, Post-Sale, After Support.
#     """
#     if not user_input:
#         return None
#     text = user_input.lower()
#     for k, v in TOUCHPOINT_KEYWORDS.items():
#         if k in text:
#             return v
#     return None


# # -----------------------
# # ROUTES
# # -----------------------
# @app.route("/")
# def home():
#     return render_template("index.html")


# # ---------- UPDATED QUESTION FLOW (smart: only missing questions) ----------
# @app.route("/generate_question_flow", methods=["POST"])
# def generate_question_flow():
#     """
#     New behavior:
#     - Analyze user_input for:
#         - survey_type (NPS/CSAT/CES/general)
#         - audience (customers/employees/students/teachers/vendors/etc.)
#         - purpose/topic (e.g. "education department", "customer support")
#         - touchpoint (Pre-Sales, During Sale, Post-Sale, After Support)
#     - Ask ONLY for the pieces that are missing.
#     - If everything is already present → skip follow-up questions and let
#       frontend jump directly to sample/template creation.
#     """
#     data = request.get_json(force=True) or {}
#     user_input = (data.get("user_input") or "").strip()

#     requested_type_raw = (data.get("survey_type") or "").strip().lower()

#     survey_type = normalize_survey_type(requested_type_raw, user_input)

#     # Type is known only if we explicitly detect NPS/CSAT/CES
#     type_known = survey_type in ["nps", "csat", "ces"]

#     # 2) Audience & purpose detection (new logic)
#     audience_from_payload = (data.get("audience") or "").strip()
#     purpose_from_payload = (data.get("purpose") or "").strip()

#     detected_audience = audience_from_payload or detect_audience(user_input)
#     detected_purpose = purpose_from_payload or extract_purpose(user_input)

#     # >>> TOUCHPOINT: from payload or detected from text
#     touchpoint_from_payload = (data.get("touchpoint") or "").strip()
#     detected_touchpoint = touchpoint_from_payload or detect_touchpoint(user_input)

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
#                 "Students",
#                 "Teachers",
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

#     # >>> TOUCHPOINT: ask if missing
#     if not detected_touchpoint:
#         question_flow.append({
#             "id": "touchpoint",
#             "q": "What is the touchpoint of this survey?",
#             "options": ["Pre", "During", "Post", "After Support"]
#         })

#     # If NOTHING is missing → skip follow-up questions
#     if not question_flow:
#         return jsonify({
#             "skip_questions": True,
#             "question_flow": [],
#             "detected_survey_type": survey_type,
#             "detected_audience": detected_audience,
#             "detected_purpose": detected_purpose,
#             "detected_touchpoint": detected_touchpoint,
#             "original_user_input": user_input
#         })

#     # Otherwise, return only the missing questions
#     return jsonify({
#         "skip_questions": False,
#         "question_flow": question_flow,
#         "detected_survey_type": survey_type,
#         "detected_audience": detected_audience,
#         "detected_purpose": detected_purpose,
#         "detected_touchpoint": detected_touchpoint,
#         "original_user_input": user_input
#     })


# # ---------- MAIN TEMPLATE GENERATION ----------
# @app.route("/generate_survey", methods=["POST"])
# def generate_survey():
#     data = request.get_json() or {}
#     user_input = (data.get("user_input") or "").strip()
#     requested_type = data.get("survey_type")

#     if not user_input:
#         return jsonify({"error": "Missing user_input"}), 400

#     # Detect / normalize survey type
#     survey_type = normalize_survey_type(requested_type, user_input)
#     processed_templates = []

#     # Prompt for GPT (templates generation)
#     prompt = f"""
# You are a CX survey expert.
# Generate 3 survey templates for: "{user_input}"
# Survey type: {survey_type.upper()}.

# Rules:
# - STRICT JSON array ONLY (no explanation).
# - Each template object must have keys: "title", "purpose", "duration", "questions".
# - duration MUST be around 2–2.5 minutes only (e.g., "2–2.5 mins").
# - FIRST question MUST be a rating question that matches survey_type scale:
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

#             # >>> RADIO OPTIONS: ensure radio questions have options
#             if scale == "radio":
#                 if options_clean:
#                     q_obj["options"] = options_clean
#                 else:
#                     q_obj["options"] = ["Yes", "No", "Not sure"]

#             # Optional: keep MCQ options if model provided them
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
#     """
#     data = request.get_json() or {}
#     focus_area = (data.get("focus_area") or "").strip()
#     requested_type = data.get("survey_type")

#     if not focus_area:
#         return jsonify({"error": "Missing focus_area"}), 400

#     survey_type = normalize_survey_type(requested_type, focus_area)

#     prompt = f"""
# You are a CX survey expert.
# Generate 3 short survey templates focused on: "{focus_area}" for survey type "{survey_type.upper()}" (NPS/CSAT/CES).
# Rules:
# - Each template should have: "title", "purpose", "duration", and exactly 4 questions.
# - Duration must be around 2–2.5 minutes only.
# - Each question must have "question" and "scale_type".
# - Use NPS 0–10 scale questions only when scale_type is "nps".
# - Use CSAT 1–5 satisfaction questions when scale_type is "csat".
# - Use CES 1–5 ease/effort questions when scale_type is "ces".
# - For any question with "scale_type": "radio" or "mcq", include an "options" array.
# Return ONLY a JSON array.
# """

#     try:
#         resp = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.6,
#             max_tokens=700
#         )
#         text = resp["choices"][0]["message"]["content"]

#         try:
#             templates = extract_json_array(text)
#         except Exception:
#             templates = []

#         templates = [
#             normalize_template_scales(t, forced_type=survey_type)
#             for t in templates
#         ]

#         # Ensure radio questions have options
#         for t in templates:
#             for q in t.get("questions", []):
#                 if q.get("scale_type") == "radio":
#                     opts = q.get("options")
#                     if not isinstance(opts, list) or not opts:
#                         q["options"] = ["Yes", "No", "Not sure"]

#         for t in templates:
#             t["duration"] = clamp_duration(t.get("duration"))

#         return jsonify({
#             "templates": templates,
#             "focus_area": focus_area,
#             "survey_type": survey_type
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
#         import re
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

#                     # >>> RADIO OPTIONS for added questions
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
#                 removed_q = questions.pop(i)

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
# from flask import Flask, request, jsonify, render_template
# import json, os, re
# from datetime import datetime
# import difflib
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


# def detect_survey_type(text: str) -> str:
#     """
#     Lightweight detection of NPS / CSAT / CES from text.
#     """
#     t = (text or "").lower()
#     if any(k in t for k in [
#         "nps", "recommend", "likelihood to recommend",
#         "promoter", "detractor", "likely to recommend"
#     ]):
#         return "nps"
#     if any(k in t for k in [
#         "csat", "satisfied", "satisfaction", "how satisfied"
#     ]):
#         return "csat"
#     if any(k in t for k in [
#         "ces", "effort", "easy", "ease", "how easy"
#     ]):
#         return "ces"
#     return "general"


# def normalize_survey_type(s_type: str | None, user_input: str = "") -> str:
#     if not s_type:
#         return detect_survey_type(user_input)
#     s = s_type.strip().lower()
#     if s in ("nps", "net promoter", "net promoter score"):
#         return "nps"
#     if s in ("csat", "customer satisfaction"):
#         return "csat"
#     if s in ("ces", "customer effort"):
#         return "ces"
#     return detect_survey_type(user_input)


# def get_first_question_for_type(survey_type: str, topic_hint: str | None = None) -> dict:
#     """
#     First question + scale_type per survey type.
#     NPS → 0–10 recommendation
#     CSAT → 1–5 satisfaction  (other ranges like 1–3 or 1–7 can be handled by UI)
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
#             # Force correct scale type for primary rating
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


# # ---------- NEW HELPERS: audience + purpose detection (without AI) ----------

# AUDIENCE_CANONICAL = {
#     "customer": "Customers",
#     "customers": "Customers",
#     "client": "Customers",
#     "clients": "Customers",
#     "employee": "Employees",
#     "employees": "Employees",
#     "staff": "Staff",
#     "user": "Users",
#     "users": "Users",
#     "student": "Students",
#     "students": "Students",
#     "teacher": "Teachers",
#     "teachers": "Teachers",
#     "parent": "Parents",
#     "parents": "Parents",
#     "vendor": "Vendors",
#     "vendors": "Vendors",
# }


# def detect_audience(user_input: str) -> str | None:
#     """
#     Detect audience from free-text using exact + fuzzy matching.
#     Returns a human-readable audience label (e.g., "Customers") or None.
#     """
#     if not user_input:
#         return None

#     text = user_input.lower()
#     tokens = re.findall(r"[a-zA-Z]+", text)

#     found_labels: list[str] = []

#     # 1) Exact matches
#     for tok in tokens:
#         if tok in AUDIENCE_CANONICAL:
#             found_labels.append(AUDIENCE_CANONICAL[tok])

#     # 2) Fuzzy matches for typos
#     if not found_labels:
#         keys = list(AUDIENCE_CANONICAL.keys())
#         for tok in tokens:
#             matches = difflib.get_close_matches(tok, keys, n=1, cutoff=0.8)
#             if matches:
#                 found_labels.append(AUDIENCE_CANONICAL[matches[0]])

#     if not found_labels:
#         return None

#     # Priority order if multiple detected
#     priority = [
#         "Customers",
#         "Employees",
#         "Students",
#         "Teachers",
#         "Parents",
#         "Vendors",
#         "Staff",
#         "Users",
#     ]
#     for p in priority:
#         if p in found_labels:
#             return p

#     return found_labels[0]


# PURPOSE_MARKERS = [
#     "survey on",
#     "survey for",
#     "survey about",
#     "survey of",
#     "survey regarding",
# ]


# def extract_purpose(user_input: str) -> str | None:
#     """
#     Extract purpose/topic from phrases like:
#     - "survey on education"
#     - "survey for customer support"
#     - "survey of education department as a customer"
#     """
#     if not user_input:
#         return None

#     text_lower = user_input.lower()

#     for marker in PURPOSE_MARKERS:
#         idx = text_lower.find(marker)
#         if idx != -1:
#             start = idx + len(marker)
#             # Use original text slice to preserve case
#             raw = user_input[start:].strip()

#             # Remove trailing audience phrases like "as a customer", "from customers"
#             lower_raw = raw.lower()
#             for splitter in [" as ", " for ", " from ", " by "]:
#                 sidx = lower_raw.find(splitter)
#                 if sidx != -1:
#                     raw = raw[:sidx].strip()
#                     lower_raw = raw.lower()
#                     break

#             # If still too short, ignore
#             if len(raw) < 2:
#                 return None
#             return raw

#     return None


# def should_skip_question(q_dict: dict, user_input: str) -> bool:
#     """
#     OLD helper – kept for compatibility.
#     Currently not used in the new flow, but retained in case you
#     want to re-use it later.
#     """
#     t = (user_input or "").lower()

#     question_text = q_dict.get("q")
#     if not isinstance(question_text, str):
#         return False  # Safe: ignore skipping for non-text questions

#     q = question_text.lower()

#     audience_keywords = ["customer", "customers", "employee", "employees", "staff",
#                          "vendor", "vendors", "manager", "managers"]
#     touchpoint_keywords = ["purchase", "checkout", "support", "delivery", "website",
#                            "app", "branch", "store", "call center"]
#     product_keywords = ["product", "service", "subscription", "plan", "software", "app", "portal"]

#     # Skip repeated context
#     if "audience" in q and any(k in t for k in audience_keywords):
#         return True
#     if "touchpoint" in q and any(k in t for k in touchpoint_keywords):
#         return True
#     if "product" in q and any(k in t for k in product_keywords):
#         return True

#     return False


# # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# # NEW: TOUCHPOINT DETECTION
# # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

# TOUCHPOINT_KEYWORDS = {
#     "pre sales": "Pre-Sales",
#     "pre-sale": "Pre-Sales",
#     "presales": "Pre-Sales",
#     "before purchase": "Pre-Sales",
#     "initial inquiry": "Pre-Sales",

#     "during sale": "During Sale",
#     "during purchase": "During Sale",
#     "purchase journey": "During Sale",
#     "buying process": "During Sale",

#     "post sale": "Post-Sale",
#     "post-sale": "Post-Sale",
#     "after sale": "Post-Sale",
#     "after purchase": "Post-Sale",

#     "support": "After Support",
#     "customer support": "After Support",
#     "after support": "After Support",
#     "service": "After Support",
#     "service request": "After Support",
# }


# def detect_touchpoint(user_input: str) -> str | None:
#     """
#     Detect a common CX touchpoint from text.
#     Examples: Pre-Sales, During Sale, Post-Sale, After Support.
#     """
#     if not user_input:
#         return None
#     text = user_input.lower()
#     for k, v in TOUCHPOINT_KEYWORDS.items():
#         if k in text:
#             return v
#     return None


# # -----------------------
# # ROUTES
# # -----------------------
# @app.route("/")
# def home():
#     return render_template("index.html")


# # ---------- UPDATED QUESTION FLOW (smart: only missing questions) ----------
# @app.route("/generate_question_flow", methods=["POST"])
# def generate_question_flow():
#     """
#     NEW LOGIC:
#     - Use GPT-4o-mini to extract: survey_type, audience, purpose, touchpoint.
#     - If any field missing → ask user.
#     - If all fields present → skip questions.
#     """

#     data = request.get_json(force=True) or {}
#     user_input = (data.get("user_input") or "").strip()

#     # STEP 1 — Call GPT to extract all 4 fields
#     extract_prompt = f"""
#     Extract 4 fields from the following text. Return JSON only.

#     Text: "{user_input}"

#     Always return JSON in this structure:
#     {{
#       "survey_type": "",      // nps, csat, ces, general
#       "audience": "",
#       "purpose": "",
#       "touchpoint": ""        // Pre-Sales, During Sale, Post-Sale, After Support
#     }}

#     Rules:
#     - Survey type must be EXACTLY nps / csat / ces / general.
#     - Audience is a human group (customers, employees, users, parents, etc.).
#     - Purpose is the topic of the survey.
#     - Touchpoint must be one of:
#       "Pre-Sales", "During Sale", "Post-Sale", "After Support"
#     If uncertain → leave field empty.
#     """

#     try:
#         gpt_resp = openai.ChatCompletion.create(
#             model="gpt-4o-mini",
#             messages=[{"role": "user", "content": extract_prompt}],
#             temperature=0.0
#         )
#         extracted = json.loads(gpt_resp["choices"][0]["message"]["content"])
#     except Exception as e:
#         print("AI Extraction Error:", e)
#         extracted = {
#             "survey_type": "",
#             "audience": "",
#             "purpose": "",
#             "touchpoint": ""
#         }

#     Ai_survey_type = extracted.get("survey_type", "").strip().lower()
#     Ai_audience = extracted.get("audience", "").strip()
#     Ai_purpose = extracted.get("purpose", "").strip()
#     Ai_touchpoint = extracted.get("touchpoint", "").strip()

#     # STEP 2 — Build follow-up question list based on missing fields
#     question_flow = []

#     if Ai_survey_type not in ["nps", "csat", "ces"]:
#         question_flow.append({
#             "id": "survey_type",
#             "q": "Which type of survey would you like to create?",
#             "options": ["NPS", "CSAT", "CES", "General / Not sure"]
#         })

#     if not Ai_audience:
#         question_flow.append({
#             "id": "audience",
#             "q": "Who is your audience for this survey?",
#             "options": [
#                 "Customers", "Employees", "Students",
#                 "Teachers", "Parents", "Vendors", "General Users"
#             ]
#         })

#     if not Ai_purpose:
#         question_flow.append({
#             "id": "purpose",
#             "q": "What is the purpose or main topic of this survey?",
#             "allow_text_input": True
#         })

#     if not Ai_touchpoint:
#         question_flow.append({
#             "id": "touchpoint",
#             "q": "What is the touchpoint of this survey?",
#             "options": ["Pre-Sales", "During Sale", "Post-Sale", "After Support"]
#         })

#     # STEP 3 — If nothing missing → skip follow-ups
#     if not question_flow:
#         return jsonify({
#             "skip_questions": True,
#             "question_flow": [],
#             "detected_survey_type": Ai_survey_type,
#             "detected_audience": Ai_audience,
#             "detected_purpose": Ai_purpose,
#             "detected_touchpoint": Ai_touchpoint,
#             "original_user_input": user_input,
#         })

#     # Missing fields → return only required questions
#     return jsonify({
#         "skip_questions": False,
#         "question_flow": question_flow,
#         "detected_survey_type": Ai_survey_type,
#         "detected_audience": Ai_audience,
#         "detected_purpose": Ai_purpose,
#         "detected_touchpoint": Ai_touchpoint,
#         "original_user_input": user_input,
#     })



# # ---------- MAIN TEMPLATE GENERATION ----------
# @app.route("/generate_survey", methods=["POST"])
# def generate_survey():
#     data = request.get_json() or {}
#     user_input = (data.get("user_input") or "").strip()
#     requested_type = data.get("survey_type")

#     if not user_input:
#         return jsonify({"error": "Missing user_input"}), 400

#     # Detect / normalize survey type
#     survey_type = normalize_survey_type(requested_type, user_input)
#     processed_templates = []

#     # Prompt for GPT (templates generation)
#     prompt = f"""
# You are a CX survey expert.
# Generate 3 survey templates for: "{user_input}"
# Survey type: {survey_type.upper()}.

# Rules:
# - STRICT JSON array ONLY (no explanation).
# - Each template object must have keys: "title", "purpose", "duration", "questions".
# - duration MUST be around 2–2.5 minutes only (e.g., "2–2.5 mins").
# - FIRST question MUST be a rating question that matches survey_type scale:
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
# """

#     try:
#         resp = openai.ChatCompletion.create(
#             model="gpt-4o",
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

#             # >>> RADIO OPTIONS: ensure radio questions have options
#             if scale == "radio":
#                 if options_clean:
#                     q_obj["options"] = options_clean
#                 else:
#                     q_obj["options"] = ["Yes", "No"]

#             # Optional: keep MCQ options if model provided them
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
#                 q["options"] = ["Yes", "No"]

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
#     """
#     data = request.get_json() or {}
#     focus_area = (data.get("focus_area") or "").strip()
#     requested_type = data.get("survey_type")

#     if not focus_area:
#         return jsonify({"error": "Missing focus_area"}), 400

#     survey_type = normalize_survey_type(requested_type, focus_area)

#     prompt = f"""
# You are a CX survey expert.
# Generate 3 short survey templates focused on: "{focus_area}" for survey type "{survey_type.upper()}" (NPS/CSAT/CES).
# Rules:
# - Each template should have: "title", "purpose", "duration", and exactly 4 questions.
# - Duration must be around 2–2.5 minutes only.
# - Each question must have "question" and "scale_type".
# - Use NPS 0–10 scale questions only when scale_type is "nps".
# - Use CSAT 1–5 satisfaction questions when scale_type is "csat".
# - Use CES 1–5 ease/effort questions when scale_type is "ces".
# - For any question with "scale_type": "radio" or "mcq", include an "options" array.
# Return ONLY a JSON array.
# """

#     try:
#         resp = openai.ChatCompletion.create(
#             model="gpt-4o",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.6,
#             max_tokens=700
#         )
#         text = resp["choices"][0]["message"]["content"]

#         try:
#             templates = extract_json_array(text)
#         except Exception:
#             templates = []

#         templates = [
#             normalize_template_scales(t, forced_type=survey_type)
#             for t in templates
#         ]

#         # Ensure radio questions have options
#         for t in templates:
#             for q in t.get("questions", []):
#                 if q.get("scale_type") == "radio":
#                     opts = q.get("options")
#                     if not isinstance(opts, list) or not opts:
#                         q["options"] = ["Yes", "No"]

#         for t in templates:
#             t["duration"] = clamp_duration(t.get("duration"))

#         return jsonify({
#             "templates": templates,
#             "focus_area": focus_area,
#             "survey_type": survey_type
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
#         import re
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
#                     model="gpt-4o",
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

#                     # >>> RADIO OPTIONS for added questions
#                     if final_scale == "radio":
#                         q_obj["options"] = ["Yes", "No"]

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
#                 removed_q = questions.pop(i)

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
#                         questions[idx]["options"] = ["Yes", "No"]

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
# ===============================================================
#   FULLY UPDATED app.py (GPT-4o Version)
#   • Full AI extraction (survey_type, audience, purpose, touchpoint)
#   • No durations
#   • Radio questions auto options
#   • Template generator cleaned
#   • Uses new OpenAI API (openai.chat.completions.create)
# ===============================================================

# from flask import Flask, request, jsonify, render_template
# import json, os, re
# from datetime import datetime
# import difflib

# # === OpenAI SDK v1.x ===
# from openai import OpenAI

# app = Flask(__name__)

# # --- Configuration: prefer setting OPENAI_API_KEY as an environment variable ---
# import openai
# openai.api_key = os.getenv("OPENAI_API_KEY")


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


# def detect_survey_type(text: str) -> str:
#     """
#     Lightweight detection of NPS / CSAT / CES from text (fallback).
#     """
#     t = (text or "").lower()
#     if any(k in t for k in [
#         "nps", "recommend", "likelihood to recommend",
#         "promoter", "detractor", "likely to recommend"
#     ]):
#         return "nps"
#     if any(k in t for k in [
#         "csat", "satisfied", "satisfaction", "how satisfied"
#     ]):
#         return "csat"
#     if any(k in t for k in [
#         "ces", "effort", "easy", "ease", "how easy"
#     ]):
#         return "ces"
#     return "general"


# def normalize_survey_type(s_type: str | None, user_input: str = "") -> str:
#     if not s_type:
#         return detect_survey_type(user_input)
#     s = s_type.strip().lower()
#     if s in ("nps", "net promoter", "net promoter score"):
#         return "nps"
#     if s in ("csat", "customer satisfaction", "satisfaction"):
#         return "csat"
#     if s in ("ces", "customer effort"):
#         return "ces"
#     return detect_survey_type(user_input)


# def get_first_question_for_type(survey_type: str, topic_hint: str | None = None) -> dict:
#     """
#     First question + scale_type per survey type.
#     NPS → 0–10 recommendation
#     CSAT → 1–5 satisfaction  (other ranges like 1–3 or 1–7 can be handled by UI)
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
#             # Force correct scale type for primary rating
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


# # ---------- OLD HELPERS: audience + purpose detection (fallbacks) ----------

# AUDIENCE_CANONICAL = {
#     "customer": "Customers",
#     "customers": "Customers",
#     "client": "Customers",
#     "clients": "Customers",
#     "employee": "Employees",
#     "employees": "Employees",
#     "staff": "Staff",
#     "user": "Users",
#     "users": "Users",
#     "student": "Students",
#     "students": "Students",
#     "teacher": "Teachers",
#     "teachers": "Teachers",
#     "parent": "Parents",
#     "parents": "Parents",
#     "vendor": "Vendors",
#     "vendors": "Vendors",
# }


# def detect_audience(user_input: str) -> str | None:
#     """
#     Detect audience from free-text using exact + fuzzy matching (fallback).
#     Returns a human-readable audience label (e.g., "Customers") or None.
#     """
#     if not user_input:
#         return None

#     text = user_input.lower()
#     tokens = re.findall(r"[a-zA-Z]+", text)

#     found_labels: list[str] = []

#     # 1) Exact matches
#     for tok in tokens:
#         if tok in AUDIENCE_CANONICAL:
#             found_labels.append(AUDIENCE_CANONICAL[tok])

#     # 2) Fuzzy matches for typos
#     if not found_labels:
#         keys = list(AUDIENCE_CANONICAL.keys())
#         for tok in tokens:
#             matches = difflib.get_close_matches(tok, keys, n=1, cutoff=0.8)
#             if matches:
#                 found_labels.append(AUDIENCE_CANONICAL[matches[0]])

#     if not found_labels:
#         return None

#     # Priority order if multiple detected
#     priority = [
#         "Customers",
#         "Employees",
#         "Students",
#         "Teachers",
#         "Parents",
#         "Vendors",
#         "Staff",
#         "Users",
#     ]
#     for p in priority:
#         if p in found_labels:
#             return p

#     return found_labels[0]


# PURPOSE_MARKERS = [
#     "survey on",
#     "survey for",
#     "survey about",
#     "survey of",
#     "survey regarding",
# ]


# def extract_purpose(user_input: str) -> str | None:
#     """
#     Extract purpose/topic from phrases like:
#     - "survey on education"
#     - "survey for customer support"
#     - "survey of education department as a customer"
#     """
#     if not user_input:
#         return None

#     text_lower = user_input.lower()

#     for marker in PURPOSE_MARKERS:
#         idx = text_lower.find(marker)
#         if idx != -1:
#             start = idx + len(marker)
#             # Use original text slice to preserve case
#             raw = user_input[start:].strip()

#             # Remove trailing audience phrases like "as a customer", "from customers"
#             lower_raw = raw.lower()
#             for splitter in [" as ", " for ", " from ", " by "]:
#                 sidx = lower_raw.find(splitter)
#                 if sidx != -1:
#                     raw = raw[:sidx].strip()
#                     lower_raw = raw.lower()
#                     break

#             # If still too short, ignore
#             if len(raw) < 2:
#                 return None
#             return raw

#     return None


# def should_skip_question(q_dict: dict, user_input: str) -> bool:
#     """
#     OLD helper – kept for compatibility.
#     Currently not used in the new flow, but retained in case you
#     want to re-use it later.
#     """
#     t = (user_input or "").lower()

#     question_text = q_dict.get("q")
#     if not isinstance(question_text, str):
#         return False  # Safe: ignore skipping for non-text questions

#     q = question_text.lower()

#     audience_keywords = ["customer", "customers", "employee", "employees", "staff",
#                          "vendor", "vendors", "manager", "managers"]
#     touchpoint_keywords = ["purchase", "checkout", "support", "delivery", "website",
#                            "app", "branch", "store", "call center"]
#     product_keywords = ["product", "service", "subscription", "plan", "software", "app", "portal"]

#     # Skip repeated context
#     if "audience" in q and any(k in t for k in audience_keywords):
#         return True
#     if "touchpoint" in q and any(k in t for k in touchpoint_keywords):
#         return True
#     if "product" in q and any(k in t for k in product_keywords):
#         return True

#     return False


# # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# # TOUCHPOINT (fallback) + AI CONTEXT EXTRACTOR
# # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

# TOUCHPOINT_KEYWORDS = {
#     "pre sales": "Pre-Sales",
#     "pre-sale": "Pre-Sales",
#     "presales": "Pre-Sales",
#     "before purchase": "Pre-Sales",
#     "initial inquiry": "Pre-Sales",

#     "during sale": "During Sale",
#     "during purchase": "During Sale",
#     "purchase journey": "During Sale",
#     "buying process": "During Sale",

#     "post sale": "Post-Sale",
#     "post-sale": "Post-Sale",
#     "after sale": "Post-Sale",
#     "after purchase": "Post-Sale",

#     "support": "After Support",
#     "customer support": "After Support",
#     "after support": "After Support",
#     "service": "After Support",
#     "service request": "After Support",
# }


# def detect_touchpoint(user_input: str) -> str | None:
#     """
#     Detect a common CX touchpoint from text (fallback).
#     Examples: Pre-Sales, During Sale, Post-Sale, After Support.
#     """
#     if not user_input:
#         return None
#     text = user_input.lower()
#     for k, v in TOUCHPOINT_KEYWORDS.items():
#         if k in text:
#             return v
#     return None


# def ai_extract_context(user_input: str) -> dict:
#     """
#     Use GPT-4o to extract:
#       - survey_type: one of ["nps","csat","ces","general"]
#       - audience: short label (e.g. "Customers", "Employees")
#       - purpose: short phrase (e.g. "education department")
#       - touchpoint: one of ["Pre-Sales","During Sale","Post-Sale","After Support","General"]
#     Returns a dict with keys, unknown fields as None.
#     """
#     if not user_input.strip():
#         return {
#             "survey_type": None,
#             "audience": None,
#             "purpose": None,
#             "touchpoint": None,
#         }

#     sys_msg = {
#         "role": "system",
#         "content": (
#             "You are a strict JSON API that extracts survey metadata from a single user sentence. "
#             "You MUST respond with a single JSON object and nothing else."
#         ),
#     }

#     user_msg = {
#         "role": "user",
#         "content": f"""
# Text: "{user_input}"

# From this text, extract:
# - survey_type: choose exactly one of ["nps","csat","ces","general"].
#   - Use "nps" if the user talks about recommendation or NPS.
#   - Use "csat" if the user talks about satisfaction (CSAT, satisfaction, happy, unhappy, etc.).
#   - Use "ces" if the user talks about effort or ease.
#   - Otherwise use "general".

# - audience: short label like "Customers", "Employees", "Students", "Parents", "Vendors", or null if unclear.
# - purpose: short phrase describing the topic (e.g. "education department", "customer support", "website usability"), or null.
# - touchpoint: choose one of ["Pre-Sales","During Sale","Post-Sale","After Support","General"] or null.
#   - Pre-Sales: before the purchase / inquiry stage.
#   - During Sale: during purchase process.
#   - Post-Sale: after the sale but not support.
#   - After Support: support/service interactions.
#   - General: when it’s not tied to a specific stage.

# Return ONLY JSON, e.g.:
# {{
#   "survey_type": "csat",
#   "audience": "Customers",
#   "purpose": "education department",
#   "touchpoint": "Post-Sale"
# }}
#         """,
#     }

#     try:
#         resp = openai.chat.completions.create(
#             model="gpt-4o",
#             response_format={"type": "json_object"},
#             messages=[sys_msg, user_msg],
#             temperature=0.0,
#             max_tokens=200,
#         )
#         content = resp.choices[0].message.content
#         data = json.loads(content)
#     except Exception as e:
#         print("⚠️ ai_extract_context failed, falling back:", e)
#         data = {}

#     return {
#         "survey_type": data.get("survey_type"),
#         "audience": data.get("audience"),
#         "purpose": data.get("purpose"),
#         "touchpoint": data.get("touchpoint"),
#     }


# # -----------------------
# # ROUTES
# # -----------------------
# @app.route("/")
# def home():
#     return render_template("index.html")


# # ---------- UPDATED QUESTION FLOW (smart: only missing questions) ----------
# @app.route("/generate_question_flow", methods=["POST"])
# def generate_question_flow():
#     """
#     New behavior:
#     - Analyze user_input for:
#         - survey_type (NPS/CSAT/CES/general)
#         - audience (customers/employees/students/teachers/vendors/etc.)
#         - purpose/topic (e.g. "education department", "customer support")
#         - touchpoint (Pre-Sales, During Sale, Post-Sale, After Support)
#     - Ask ONLY for the pieces that are missing.
#     - If everything is already present → skip follow-up questions and let
#       frontend jump directly to sample/template creation.
#     """
#     data = request.get_json(force=True) or {}
#     user_input = (data.get("user_input") or "").strip()

#     # ---------------------------------------------------------
#     # 1) First, call AI extractor for fully dynamic understanding
#     # ---------------------------------------------------------
#     ai_ctx = ai_extract_context(user_input)
#     ai_survey_type = ai_ctx.get("survey_type")
#     ai_audience = ai_ctx.get("audience")
#     ai_purpose = ai_ctx.get("purpose")
#     ai_touchpoint = ai_ctx.get("touchpoint")

#     # 2) Explicit payload overrides AI (user answers from previous step)
#     payload_type_raw = (data.get("survey_type") or "").strip().lower()
#     audience_from_payload = (data.get("audience") or "").strip()
#     purpose_from_payload = (data.get("purpose") or "").strip()
#     touchpoint_from_payload = (data.get("touchpoint") or "").strip()

#     # 3) Decide final detected values:
#     #    - survey_type: payload → AI → regex fallback
#     survey_type_raw = payload_type_raw or (ai_survey_type or "")
#     survey_type = normalize_survey_type(survey_type_raw, user_input)

#     detected_audience = (
#         audience_from_payload
#         or ai_audience
#         or detect_audience(user_input)
#     )

#     detected_purpose = (
#         purpose_from_payload
#         or ai_purpose
#         or extract_purpose(user_input)
#     )

#     detected_touchpoint = (
#         touchpoint_from_payload
#         or ai_touchpoint
#         or detect_touchpoint(user_input)
#     )

#     # Type is known only if we explicitly detect NPS/CSAT/CES
#     type_known = survey_type in ["nps", "csat", "ces"]

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
#                 "Students",
#                 "Teachers",
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

#     if not detected_touchpoint:
#         question_flow.append({
#             "id": "touchpoint",
#             "q": "What is the touchpoint of this survey?",
#             "options": ["Pre-Sales", "During Sale", "Post-Sale", "After Support", "General"]
#         })

#     # If NOTHING is missing → skip follow-up questions
#     if not question_flow:
#         return jsonify({
#             "skip_questions": True,
#             "question_flow": [],
#             "detected_survey_type": survey_type,
#             "detected_audience": detected_audience,
#             "detected_purpose": detected_purpose,
#             "detected_touchpoint": detected_touchpoint,
#             "original_user_input": user_input
#         })

#     # Otherwise, return only the missing questions
#     return jsonify({
#         "skip_questions": False,
#         "question_flow": question_flow,
#         "detected_survey_type": survey_type,
#         "detected_audience": detected_audience,
#         "detected_purpose": detected_purpose,
#         "detected_touchpoint": detected_touchpoint,
#         "original_user_input": user_input
#     })


# # ---------- MAIN TEMPLATE GENERATION ----------
# @app.route("/generate_survey", methods=["POST"])
# def generate_survey():
#     data = request.get_json() or {}
#     user_input = (data.get("user_input") or "").strip()
#     requested_type = data.get("survey_type")

#     if not user_input:
#         return jsonify({"error": "Missing user_input"}), 400

#     # Detect / normalize survey type
#     survey_type = normalize_survey_type(requested_type, user_input)
#     processed_templates = []

#     # Prompt for GPT (templates generation)
#     prompt = f"""
# You are a CX survey expert.
# Generate 3 survey templates for: "{user_input}"
# Survey type: {survey_type.upper()}.

# Rules:
# - STRICT JSON array ONLY (no explanation).
# - Each template object must have keys: "title", "purpose", "duration", "questions".
# - duration MUST be around 2–2.5 minutes only (e.g., "2–2.5 mins").
# - FIRST question MUST be a rating question that matches survey_type scale:
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
# """

#     try:
#         resp = openai.chat.completions.create(
#             model="gpt-4o",
#             messages=[
#                 {"role": "system", "content": "Return strict JSON only, no explanation."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.4,
#             max_tokens=1200,
#         )
#         text = resp.choices[0].message.content
#         try:
#             templates = extract_json_array(text)
#         except Exception as e:
#             print("extract_json_array error:", e, "raw:", text)
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
#     """
#     data = request.get_json() or {}
#     focus_area = (data.get("focus_area") or "").strip()
#     requested_type = data.get("survey_type")

#     if not focus_area:
#         return jsonify({"error": "Missing focus_area"}), 400

#     survey_type = normalize_survey_type(requested_type, focus_area)

#     prompt = f"""
# You are a CX survey expert.
# Generate 3 short survey templates focused on: "{focus_area}" for survey type "{survey_type.upper()}" (NPS/CSAT/CES).
# Rules:
# - Each template should have: "title", "purpose", "duration", and exactly 4 questions.
# - Duration must be around 2–2.5 minutes only.
# - Each question must have "question" and "scale_type".
# - Use NPS 0–10 scale questions only when scale_type is "nps".
# - Use CSAT 1–5 satisfaction questions when scale_type is "csat".
# - Use CES 1–5 ease/effort questions when scale_type is "ces".
# - For any question with "scale_type": "radio" or "mcq", include an "options" array.
# Return ONLY a JSON array.
# """

#     try:
#         resp = openai.chat.completions.create(
#             model="gpt-4o",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.6,
#             max_tokens=800,
#         )
#         text = resp.choices[0].message.content

#         try:
#             templates = extract_json_array(text)
#         except Exception as e:
#             print("extract_json_array (more) error:", e, "raw:", text)
#             templates = []

#         templates = [
#             normalize_template_scales(t, forced_type=survey_type)
#             for t in templates
#         ]

#         # Ensure radio questions have options
#         for t in templates:
#             for q in t.get("questions", []):
#                 if q.get("scale_type") == "radio":
#                     opts = q.get("options")
#                     if not isinstance(opts, list) or not opts:
#                         q["options"] = ["Yes", "No", "Not sure"]

#         for t in templates:
#             t["duration"] = clamp_duration(t.get("duration"))

#         return jsonify({
#             "templates": templates,
#             "focus_area": focus_area,
#             "survey_type": survey_type
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

#                 response = openai.chat.completions.create(
#                     model="gpt-4o",
#                     messages=[{"role": "user", "content": prompt}],
#                     temperature=0.7,
#                     max_tokens=300,
#                 )
#                 content = response.choices[0].message.content.strip()
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
#                 _ = questions.pop(i)

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
#     # If you still see 'proxies' error, run:  pip install -U httpx
#     app.run(host="0.0.0.0", port=5000, debug=True)
# from flask import Flask, request, jsonify, render_template
# import json, os, re
# from datetime import datetime
# import difflib
# import openai   # ✅ CORRECT SDK import (v1.43.0+)

# # Set API key
# openai.api_key = os.getenv("OPENAI_API_KEY", "")

# app = Flask(__name__)

# OUTPUT_FILE = "saved_surveys.json"
# RESPONSES_FILE = "responses.json"

# for path, default in [(OUTPUT_FILE, []), (RESPONSES_FILE, [])]:
#     if not os.path.exists(path):
#         with open(path, "w", encoding="utf-8") as fh:
#             json.dump(default, fh, indent=2)

# # ============================================================
# # CONSTANTS & HELPERS
# # ============================================================

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
#     m = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
#     if not m:
#         m = re.search(r"\[.*\]", text, re.DOTALL)
#     if not m:
#         raise ValueError("No JSON array found in model response")
#     return json.loads(m.group())


# # ============================================================
# # SURVEY TYPE DETECTION
# # ============================================================

# def detect_survey_type(text: str) -> str:
#     t = (text or "").lower()
#     if any(k in t for k in ["nps", "recommend", "likely to recommend", "promoter"]):
#         return "nps"
#     if any(k in t for k in ["csat", "satisfied", "satisfaction"]):
#         return "csat"
#     if any(k in t for k in ["ces", "effort", "easy", "how easy"]):
#         return "ces"
#     return "general"


# def normalize_survey_type(s_type: str | None, user_input: str = "") -> str:
#     if not s_type:
#         return detect_survey_type(user_input)
#     s = s_type.strip().lower()
#     if s in ("nps", "net promoter"):
#         return "nps"
#     if s in ("csat", "satisfaction"):
#         return "csat"
#     if s in ("ces", "customer effort"):
#         return "ces"
#     return detect_survey_type(user_input)


# # ============================================================
# # FIRST QUESTION GENERATOR BASED ON SURVEY TYPE
# # ============================================================

# def get_first_question_for_type(survey_type: str, topic_hint: str | None = None) -> dict:
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

#     return {
#         "question": f"On a scale of 1–10, how satisfied are you with {topic}?",
#         "scale_type": "rating"
#     }


# # ============================================================
# # SCALE TYPE INFERENCE (RADIO DETECTION FIXED)
# # ============================================================

# def infer_scale_type(question: str) -> str:
#     q = (question or "").lower().strip()

#     if "recommend" in q or "nps" in q:
#         return "nps"
#     if "satisfied" in q or "satisfaction" in q:
#         return "csat"
#     if "easy" in q or "effort" in q:
#         return "ces"

#     if any(q.startswith(x) for x in ["did", "do", "does", "is", "are", "was"]):
#         return "radio"

#     if "yes or no" in q or "yes/no" in q:
#         return "radio"

#     if "select one" in q or "choose one" in q:
#         return "radio"

#     if "select all" in q or "choose all" in q:
#         return "mcq"

#     if "rate the following" in q or "rate each" in q:
#         return "matrix"

#     if "upload" in q or "file" in q:
#         return "file"

#     return "text"


# # ============================================================
# # AUDIENCE / PURPOSE / TOUCHPOINT (DETECTION + AI EXTRACTOR)
# # ============================================================

# AUDIENCE_CANONICAL = {
#     "customer": "Customers",
#     "customers": "Customers",
#     "client": "Customers",
#     "clients": "Customers",
#     "employee": "Employees",
#     "employees": "Employees",
#     "student": "Students",
#     "students": "Students",
#     "teacher": "Teachers",
#     "teachers": "Teachers",
#     "parent": "Parents",
#     "parents": "Parents",
#     "vendor": "Vendors",
#     "vendors": "Vendors",
# }

# def detect_audience(text: str) -> str | None:
#     if not text:
#         return None
#     tokens = re.findall(r"[a-zA-Z]+", text.lower())
#     for tok in tokens:
#         if tok in AUDIENCE_CANONICAL:
#             return AUDIENCE_CANONICAL[tok]
#     return None


# PURPOSE_MARKERS = [
#     "survey on",
#     "survey for",
#     "survey about",
#     "survey of",
# ]

# def extract_purpose(user_input: str) -> str | None:
#     if not user_input:
#         return None
#     lower = user_input.lower()
#     for m in PURPOSE_MARKERS:
#         idx = lower.find(m)
#         if idx != -1:
#             raw = user_input[idx + len(m):].strip()
#             return raw.split(" as ")[0]
#     return None


# TOUCHPOINT_KEYWORDS = {
#     "pre sales": "Pre-Sales",
#     "during sale": "During Sale",
#     "post sale": "Post-Sale",
#     "after support": "After Support",
# }

# def detect_touchpoint(text: str) -> str | None:
#     t = text.lower()
#     for k, v in TOUCHPOINT_KEYWORDS.items():
#         if k in t:
#             return v
#     return None


# # ===================== AI CONTEXT EXTRACTOR (GPT-4O) =====================

# def ai_extract_context(user_input: str) -> dict:
#     if not user_input.strip():
#         return {"survey_type": None, "audience": None, "purpose": None, "touchpoint": None}

#     try:
#         resp = openai.ChatCompletion.create(
#             model="gpt-4o",
#             messages=[
#                 {"role": "system", "content": "Return ONLY JSON."},
#                 {"role": "user", "content": f"""
# Extract structured metadata from the following text.

# Text: "{user_input}"

# Return JSON:
# {{
#   "survey_type": "nps/csat/ces/general",
#   "audience": "...",
#   "purpose": "...",
#   "touchpoint": "Pre-Sales / During Sale / Post-Sale / After Support / General"
# }}
# """}
#             ],
#             temperature=0,
#             max_tokens=200,
#         )

#         data = json.loads(resp["choices"][0]["message"]["content"])
#         return data

#     except Exception as e:
#         print("⚠️ AI extraction failed:", e)
#         return {"survey_type": None, "audience": None, "purpose": None, "touchpoint": None}


# # ============================================================
# # ROUTES
# # ============================================================

# @app.route("/")
# def home():
#     return render_template("index.html")


# # ============================================================
# # QUESTION FLOW (ONLY ASK MISSING PARAMETERS)
# # ============================================================

# @app.route("/generate_question_flow", methods=["POST"])
# def generate_question_flow_route():
#     data = request.get_json() or {}
#     user_input = (data.get("user_input") or "").strip()

#     ai = ai_extract_context(user_input)

#     survey_type = normalize_survey_type(ai.get("survey_type"), user_input)
#     audience = ai.get("audience") or detect_audience(user_input)
#     purpose = ai.get("purpose") or extract_purpose(user_input)
#     touchpoint = ai.get("touchpoint") or detect_touchpoint(user_input)

#     question_flow = []

#     if survey_type not in ["nps", "csat", "ces"]:
#         question_flow.append({
#             "id": "survey_type",
#             "q": "Which type of survey would you like to create?",
#             "options": ["NPS", "CSAT", "CES", "General / Not sure"]
#         })

#     if not audience:
#         question_flow.append({
#             "id": "audience",
#             "q": "Who is your audience?",
#             "options": ["Customers", "Employees", "Students", "Parents", "Teachers", "Vendors"]
#         })

#     if not purpose:
#         question_flow.append({
#             "id": "purpose",
#             "q": "What is the purpose/topic of this survey?",
#             "allow_text_input": True
#         })

#     if not touchpoint:
#         question_flow.append({
#             "id": "touchpoint",
#             "q": "Which touchpoint does this survey belong to?",
#             "options": ["Pre-Sales", "During Sale", "Post-Sale", "After Support", "General"]
#         })

#     if not question_flow:
#         return jsonify({
#             "skip_questions": True,
#             "detected_survey_type": survey_type,
#             "detected_audience": audience,
#             "detected_purpose": purpose,
#             "detected_touchpoint": touchpoint,
#         })

#     return jsonify({
#         "skip_questions": False,
#         "question_flow": question_flow,
#         "detected_survey_type": survey_type,
#         "detected_audience": audience,
#         "detected_purpose": purpose,
#         "detected_touchpoint": touchpoint,
#     })


# # ============================================================
# # GENERATE SURVEY TEMPLATES
# # ============================================================

# @app.route("/generate_survey", methods=["POST"])
# def generate_survey_route():
#     data = request.get_json() or {}

#     user_input = data.get("user_input", "")
#     survey_type = normalize_survey_type(data.get("survey_type"), user_input)

#     prompt = f"""
# Generate 3 survey templates. STRICT JSON ARRAY.

# Rules:
# - 5–7 questions.
# - duration: "2–2.5 mins"
# - First question must match {survey_type.upper()} scale.
# - Radio questions MUST include options.

# Text: "{user_input}"
# """

#     resp = openai.ChatCompletion.create(
#         model="gpt-4o",
#         messages=[
#             {"role": "system", "content": "Return ONLY JSON array."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.4,
#         max_tokens=1500,
#     )

#     raw = resp["choices"][0]["message"]["content"]
#     try:
#         templates = extract_json_array(raw)
#     except:
#         templates = []

#     # Enforce first question + scale fixes
#     first_q = get_first_question_for_type(survey_type, user_input)

#     processed = []
#     for t in templates:
#         t["duration"] = "2–2.5 mins"
#         new_qs = []

#         for q in t.get("questions", []):
#             txt = q.get("question") or q.get("text") or ""
#             scale = infer_scale_type(txt)

#             q_obj = {"question": txt, "scale_type": scale}

#             if scale == "radio" and not q.get("options"):
#                 q_obj["options"] = ["Yes", "No", "Not sure"]

#             new_qs.append(q_obj)

#         t["questions"] = new_qs

#         if not t["questions"] or t["questions"][0]["scale_type"] != survey_type:
#             t["questions"].insert(0, first_q)

#         processed.append(t)

#     save_history({
#         "timestamp": datetime.now().isoformat(),
#         "input": user_input,
#         "survey_type": survey_type,
#         "templates": processed
#     })

#     return jsonify({
#         "surveys": processed,
#         "detected_survey_type": survey_type
#     })


# # ============================================================
# # GENERATE MORE SURVEYS
# # ============================================================

# @app.route("/generate_more_surveys", methods=["POST"])
# def generate_more_surveys_route():
#     data = request.get_json() or {}
#     focus_area = data.get("focus_area", "")
#     survey_type = normalize_survey_type(data.get("survey_type"), focus_area)

#     prompt = f"""
# Generate 3 short templates (4 questions each) about "{focus_area}".
# Strict JSON array.
# """

#     resp = openai.ChatCompletion.create(
#         model="gpt-4o",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.5,
#         max_tokens=600,
#     )

#     raw = resp["choices"][0]["message"]["content"]
#     try:
#         templates = extract_json_array(raw)
#     except:
#         templates = []

#     return jsonify({
#         "templates": templates,
#         "focus_area": focus_area,
#         "survey_type": survey_type
#     })


# # ============================================================
# # CUSTOMIZE
# # ============================================================

# @app.route("/customize_selected_template", methods=["POST"])
# def customize_selected_template_route():
#     data = request.get_json() or {}
#     return jsonify({
#         "message": "Customization endpoint placeholder (logic preserved).",
#         "selected_template": data.get("templates", [])[0]
#     })


# # ============================================================
# # FINALIZE
# # ============================================================

# @app.route("/finalize_template", methods=["POST"])
# def finalize_template_route():
#     data = request.get_json() or {}
#     tpl = data.get("final_template")

#     template_id = datetime.now().strftime("%Y%m%d%H%M%S")
#     os.makedirs("finalized_templates", exist_ok=True)
#     path = f"finalized_templates/template_{template_id}.json"

#     with open(path, "w", encoding="utf-8") as f:
#         json.dump(tpl, f, indent=2, ensure_ascii=False)

#     return jsonify({
#         "message": "Template saved",
#         "template_id": template_id,
#         "path": path
#     })


# # ============================================================
# # RUN
# # ============================================================

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=True)##
##  AI code from flask import Flask, request, jsonify, render_template
## running code AI 
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
# # NEW: AI-BASED PARAMETER ANALYSIS (ONLY BRAIN)
# # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

# def analyze_user_input_with_openai(user_input: str) -> dict:
#     """
#     AI-only extractor for:
#       - survey_type  ∈ {"nps","csat","ces","general"} or None
#       - audience     ∈ any dynamic string or None
#       - purpose      ∈ any dynamic string or None
#       - touchpoint   ∈ any dynamic string or None

#     STRICT RULES:
#       - If unsure about any field → return null for that field.
#       - Do NOT guess. Prefer null.
#       - "education department" and similar SHOULD be purpose, NOT audience.
#       - Words like 'department','team','branch','office','unit','center' are NOT audiences.
#     """
#     empty_result = {
#         "survey_type": None,
#         "audience": None,
#         "purpose": None,
#         "touchpoint": None
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
#   "purpose": string | null,
#   "touchpoint": string | null
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

# 4) touchpoint:
#    - Journey stage or moment. Free-form short phrase.
#    - Examples:
#        "Pre-Sales", "During Purchase", "Post-Sale", "After Support call",
#        "During Admission", "After Installation".
#    - If no stage is clear → return null.

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
#         touchpoint = norm_str(data.get("touchpoint"))

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
#             "purpose": purpose,
#             "touchpoint": touchpoint
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


# # ---------- UPDATED QUESTION FLOW (AI-only detection) ----------
# @app.route("/generate_question_flow", methods=["POST"])
# def generate_question_flow():
#     """
#         IMPORTANT RULES:
#     - The AUDIENCE must always be a group of people who will answer the survey.
#     - The AUDIENCE CANNOT be a department, team, branch, office, unit, or organization.
#     These ALWAYS belong to PURPOSE, not audience.

#     CLASSIFICATION RULE:
#     If a phrase contains words like:
#     "department", "team", "branch", "office", "board", "unit", "division", 
#     "authority", "ministry", "committee", "organization"

#     → DO NOT classify it as audience.  
#     → Classify it as PURPOSE.

#     CORRECT CLASSIFICATION EXAMPLES:

#     Example 1:
#     User: "I want a survey for the education department"
#     Output:
#     {
#     "survey_type": null,
#     "audience": null,
#     "purpose": "education department",
#     "touchpoint": null
#     }

#     Example 2:
#     User: "Create a survey for HR department employees"
#     Output:
#     {
#     "survey_type": null,
#     "audience": "Employees",
#     "purpose": "HR department",
#     "touchpoint": null
#     }

#     Example 3:
#     User: "Survey for support team"
#     Output:
#     {
#     "survey_type": null,
#     "audience": null,
#     "purpose": "support team",
#     "touchpoint": null
#     }

#     Example 4:
#     User: "Customer CSAT survey for billing department"
#     Output:
#     {
#     "survey_type": "csat",
#     "audience": "Customers",
#     "purpose": "billing department",
#     "touchpoint": null
#     }

#     RULE SUMMARY:
#     - People = audience (customers, employees, students, parents, users)
#     - Departments/Teams/Units = purpose

#     AI-first behavior:
#     - Analyze user_input for:
#         - survey_type (NPS/CSAT/CES/general)
#         - audience (dynamic)
#         - purpose/topic (dynamic)
#         - touchpoint (dynamic)
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
#     touchpoint_from_payload = (data.get("touchpoint") or "").strip()

#     # --- AI analysis (single call) ---
#     ai_result = analyze_user_input_with_openai(user_input) if user_input else {
#         "survey_type": None,
#         "audience": None,
#         "purpose": None,
#         "touchpoint": None
#     }

#     ai_survey_type = ai_result.get("survey_type")
#     ai_audience = ai_result.get("audience")
#     ai_purpose = ai_result.get("purpose")
#     ai_touchpoint = ai_result.get("touchpoint")

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

#     # --- Audience / purpose / touchpoint: payload overrides AI ---
#     detected_audience = audience_from_payload or ai_audience
#     detected_purpose = purpose_from_payload or ai_purpose
#     detected_touchpoint = touchpoint_from_payload or ai_touchpoint

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
#                 "Students",
#                 "Teachers",
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

#     if not detected_touchpoint:
#         question_flow.append({
#             "id": "touchpoint",
#             "q": "What is the touchpoint of this survey?",
#             "options": ["Pre", "During", "Post", "After Support"]
#         })

#     # If NOTHING is missing → skip follow-up questions
#     if not question_flow:
#         return jsonify({
#             "skip_questions": True,
#             "question_flow": [],
#             "detected_survey_type": survey_type,
#             "detected_audience": detected_audience,
#             "detected_purpose": detected_purpose,
#             "detected_touchpoint": detected_touchpoint,
#             "original_user_input": user_input
#         })

#     # Otherwise, return only the missing questions
#     return jsonify({
#         "skip_questions": False,
#         "question_flow": question_flow,
#         "detected_survey_type": survey_type,
#         "detected_audience": detected_audience,
#         "detected_purpose": detected_purpose,
#         "detected_touchpoint": detected_touchpoint,
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
# Survey type: {survey_type.upper()}.

# Rules:
# - STRICT JSON array ONLY (no explanation).
# - Each template object must have keys: "title", "purpose", "duration", "questions".
# - duration MUST be around 2–2.5 minutes only (e.g., "2–2.5 mins").
# - FIRST question MUST be a rating question that matches survey_type scale:
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
#     """
#     data = request.get_json() or {}
#     focus_area = (data.get("focus_area") or "").strip()
#     requested_type_raw = (data.get("survey_type") or "").strip().lower()

#     if not focus_area:
#         return jsonify({"error": "Missing focus_area"}), 400

#     # survey_type for "more" flow: payload > AI > general
#     if requested_type_raw in ["nps", "csat", "ces", "general"]:
#         survey_type = requested_type_raw
#     else:
#         ai_result = analyze_user_input_with_openai(focus_area)
#         ai_type = ai_result.get("survey_type")
#         if ai_type in ["nps", "csat", "ces", "general"]:
#             survey_type = ai_type
#         else:
#             survey_type = "general"

#     prompt = f"""
# You are a CX survey expert.
# Generate 3 short survey templates focused on: "{focus_area}" for survey type "{survey_type.upper()}" (NPS/CSAT/CES/GENERAL).
# Rules:
# - Each template should have: "title", "purpose", "duration", and exactly 4 questions.
# - Duration must be around 2–2.5 minutes only.
# - Each question must have "question" and "scale_type".
# - Use NPS 0–10 scale questions only when scale_type is "nps".
# - Use CSAT 1–5 satisfaction questions when scale_type is "csat".
# - Use CES 1–5 ease/effort questions when scale_type is "ces".
# - For any question with "scale_type": "radio" or "mcq", include an "options" array.
# Return ONLY a JSON array.
# """

#     try:
#         resp = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.6,
#             max_tokens=700
#         )
#         text = resp["choices"][0]["message"]["content"]

#         try:
#             templates = extract_json_array(text)
#         except Exception:
#             templates = []

#         templates = [
#             normalize_template_scales(t, forced_type=survey_type)
#             for t in templates
#         ]

#         # Ensure radio questions have options
#         for t in templates:
#             for q in t.get("questions", []):
#                 if q.get("scale_type") == "radio":
#                     opts = q.get("options")
#                     if not isinstance(opts, list) or not opts:
#                         q["options"] = ["Yes", "No", "Not sure"]

#         for t in templates:
#             t["duration"] = clamp_duration(t.get("duration"))

#         return jsonify({
#             "templates": templates,
#             "focus_area": focus_area,
#             "survey_type": survey_type
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