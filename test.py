from flask import Flask, request, jsonify, render_template
import json, os, re
from datetime import datetime
import openai


app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY", "")

OUTPUT_FILE = "saved_surveys.json"
RESPONSES_FILE = "responses.json"

for path, default in [(OUTPUT_FILE, []), (RESPONSES_FILE, [])]:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(default, fh, indent=2)

# -----------------------
# HELPERS
# -----------------------
def ensure_first_rating(survey, topic_hint=None):
    base = f"On a scale of 1–10, how satisfied are you with {topic_hint or 'this'}?"
    qlist = survey.get("questions", [])
    if not qlist or "how satisfied" not in qlist[0].lower():
        qlist.insert(0, base)
    survey["questions"] = qlist
    return survey

def save_history(entry):
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    data.append(entry)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

ALLOWED_SCALE_TYPES = [
    "nps", "csat", "ces", "rating", 
    "text", "radio", "mcq", "matrix", "file"
]
def detect_survey_type(text: str) -> str:
    t = (text or "").lower()

    if any(k in t for k in [
        "nps", "recommend", "likelihood to recommend",
        "promoter", "detractor", "likely to recommend"
    ]):
        return "nps"

    if any(k in t for k in [
        "csat", "satisfied", "satisfaction", "how satisfied"
    ]):
        return "csat"

    if any(k in t for k in [
        "ces", "effort", "easy", "ease"
    ]):
        return "ces"

    return "general"
# -----------------------
# ROUTES
# -----------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate_question_flow", methods=["POST"])
def generate_question_flow():
    data = request.get_json(force=True) or {}
    user_input = (data.get("user_input") or "").strip()
    survey_type = detect_survey_type(user_input)

    # Ask survey type first if not detected
    if survey_type == "general":
        flow = [
            {"q": "Which type of survey would you like to create?", "options": ["NPS", "CSAT", "CES", "Other"], "allow_text_input": True},
            {"q": "Who is your audience?", "options": ["Customers", "Employees", "Vendors", "Other"], "allow_text_input": True},
            {"q": "What is the main purpose of your survey?", "options": ["Feedback", "Satisfaction", "Retention", "Other"], "allow_text_input": True},
            {"q": "Would you like to include purpose and duration in your templates?", "options": ["Yes", "No"], "allow_text_input": False}
        ]
        return jsonify({"question_flow": flow, "detected_survey_type": survey_type, "original_user_input": user_input})

    # If survey type auto‑detected → contextual flow
    base = [
        {"q": "Who is your audience?", "options": ["Customers", "Employees", "Vendors", "Other"], "allow_text_input": True},
        {"q": "What is the main purpose of your survey?", "options": ["Feedback", "Satisfaction", "Retention", "Other"], "allow_text_input": True},
    ]

    if survey_type == "nps":
        follow = [
            {"q": "Which product/service are you measuring loyalty for?", "allow_text_input": True},
            {"q": "Which customer segment?", "options": ["New", "Returning", "Loyal", "Other"], "allow_text_input": True},
        ]
    elif survey_type == "csat":
        follow = [
            {"q": "Which touchpoint are you evaluating?", "options": ["Purchase", "Support", "Delivery", "Website", "Other"], "allow_text_input": True},
        ]
    elif survey_type == "ces":
        follow = [
            {"q": "Which task or workflow are you measuring effort for?", "allow_text_input": True},
        ]
    else:
        follow = []

    flow = base + follow
    flow.append({"q": "Would you like to include purpose and duration in your templates?", "options": ["Yes", "No"], "allow_text_input": False})
    return jsonify({
        "question_flow": flow,
        "detected_survey_type": survey_type,
        "original_user_input": user_input
    })


    # If type detected → continue with contextual flow
    base = [
        {"q": "Who is your audience?", "options": ["Customers", "Employees", "Vendors", "Other"], "allow_text_input": True},
        {"q": "What is the main purpose of your survey?", "options": ["Feedback", "Satisfaction", "Retention", "Other"], "allow_text_input": True},
    ]

    if survey_type == "nps":
        follow = [
            {"q": "Which product/service are you measuring loyalty for?", "allow_text_input": True},
            {"q": "Which customer segment?", "options": ["New", "Returning", "Loyal", "Other"], "allow_text_input": True},
        ]
    elif survey_type == "csat":
        follow = [
            {"q": "Which touchpoint are you evaluating?", "options": ["Purchase", "Support", "Delivery", "Website", "Other"], "allow_text_input": True},
        ]
    elif survey_type == "ces":
        follow = [
            {"q": "Which task or workflow are you measuring effort for?", "allow_text_input": True},
        ]

    flow = base + follow
    return jsonify({"question_flow": flow, "detected_survey_type": survey_type})


@app.route("/generate_survey", methods=["POST"])
def generate_survey():
    data = request.get_json() or {}
    user_input = (data.get("user_input") or "").strip()
    if not user_input:
        return jsonify({"error": "Missing user_input"}), 400

    prompt = f"""
    You are a professional survey builder.
    Create 4–5 professional survey templates for "{user_input}".
    Each template must include:
    - title
    - purpose (1–2 lines summary of survey intent)
    - duration (e.g., "3–5 mins", "Under 10 mins")
    - 4–5 short questions
    - each question must include its appropriate scale_type from:
      ["nps", "csat", "ces", "rating", "text", "radio", "mcq", "matrix", "file"]
    The FIRST question must always start with:
      "On a scale of 1–10, how satisfied are you..."
    Return a valid JSON array only like:
    [
      {{
        "title": "Template Title",
        "purpose": "Purpose text",
        "duration": "Duration text",
        "questions": [
          {{"question": "Q1 text", "scale_type": "number"}},
          {{"question": "Q2 text", "scale_type": "yesno"}},
          ...
        ]
      }}
    ]
    """

    try:
        # Old OpenAI syntax (ChatCompletion)
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800
        )

        text = response["choices"][0]["message"]["content"]

        # Extract JSON safely
        json_match = re.search(r"\[.*\]", text, re.DOTALL)
        if json_match:
            surveys = json.loads(json_match.group())
        else:
            surveys = []

        # Validation & fallback cleanup
        for s in surveys:
            s.setdefault("purpose", f"Understand customer opinions on {user_input}")
            s.setdefault("duration", "5–7 mins")
            s.setdefault("questions", [])
            if not s["questions"]:
                s["questions"].append({
                    "question": f"On a scale of 1–10, how satisfied are you with {user_input}?",
                    "scale_type": "number"
                })
            else:
                first_q = s["questions"][0]
                if "how satisfied" not in first_q.get("question", "").lower():
                    s["questions"].insert(0, {
                        "question": f"On a scale of 1–10, how satisfied are you with {user_input}?",
                        "scale_type": "number"
                    })

    except Exception as e:
        print("AI survey generation error:", e)
        surveys = []

    # Log or store in local history if needed
    save_history({
        "timestamp": datetime.now().isoformat(),
        "input": user_input,
        "surveys": surveys
    })

    return jsonify({
        "surveys": surveys,
        "follow_up": "Would you like to generate more templates or select one? (Generate More / Select Template)"
    })





# -----------------------
# NEW LOGIC 1 — Handle 'Generate More'
# -----------------------
@app.route("/ask_focus_area", methods=["POST"])
def ask_focus_area():
    """Ask which aspect user wants more templates for."""
    return jsonify({
        "message": "Which specific aspect would you like to focus on for the new templates?"
    })


@app.route("/generate_more_surveys", methods=["POST"])
def generate_more_surveys():
    data = request.get_json()
    focus_area = data.get("focus_area", "")
    survey_type = data.get("survey_type", "")

    if not focus_area:
        return jsonify({"error": "Missing focus area"}), 400

    # Example AI prompt
    prompt = f"""
    You are a professional survey designer.
    Generate 3 new survey templates focused on "{focus_area}" related to "{survey_type}".
    Each template should include:
    - Title
    - Purpose
    - Duration
    - 5 Questions (with scale type: "nps", "csat", "ces", "rating", "text", "radio", "mcq", "matrix", "file")
    Return strictly JSON in the format:
    [
      {{
        "title": "Template Title",
        "purpose": "Purpose text",
        "duration": "Time estimate",
        "questions": [
          {{"question": "text", "scale_type": "number"}}
        ]
      }}
    ]
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a CX survey generation expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )
        ai_text = response.choices[0].message["content"]
        json_like = re.search(r"\[.*\]", ai_text, re.DOTALL)
        templates = json.loads(json_like.group()) if json_like else []
        return jsonify({"templates": templates})
    except Exception as e:
        print("Error generating more surveys:", e)
        return jsonify({"error": str(e)}), 500
    

# -----------------------
# NEW LOGIC 2 — Handle 'Select Template'
# -----------------------
@app.route("/select_template", methods=["POST"])
def select_template():
    """Ask which template user wants to choose."""
    data = request.get_json() or {}
    templates = data.get("templates", [])
    template_numbers = [f"Template {i+1}: {t['title']}" for i, t in enumerate(templates)]

    return jsonify({
        "message": "Please specify which template number you want to customize (e.g., Template 3).",
        "available_templates": template_numbers,
        "templates": templates
    })

@app.route("/customize_selected_template", methods=["POST"])
def customize_selected_template():
    """
    Unified endpoint for survey customization.
    - Handles Add / Remove actions
    - Adds AI-generated questions based on focus/complexity
    - Updates scale types
    - Returns next-step customization prompts
    """
    import re
    import openai
    from flask import request, jsonify

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

    # ---------------------- STEP 1: ADD OR REMOVE QUESTIONS ----------------------
    ai_questions_added = False  # Track if AI-generated questions were added

    if action in ["add", "remove"]:
        if action == "add":
            topic = focus_area or title
            try:
                # Determine tone based on complexity
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
                """
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=250
                )
                content = response["choices"][0]["message"]["content"].strip()
                ai_questions = [
                    re.sub(r"^\s*(\d+[\.\)]|[-•])\s*", "", q.strip())
                    for q in content.split("\n") if q.strip()
                ]

                # Infer scale type
                def infer_scale_type(question: str) -> str:
                    q = question.lower()

                    if "nps" in q or "recommend" in q or "likely" in q:
                        return "nps"
                    if "satisfied" in q or "csat" in q:
                        return "csat"
                    if "ease" in q or "ces" in q:
                        return "ces"
                    if "rate" in q or "rating" in q or "score" in q:
                        return "rating"
                    if any(x in q for x in ["why", "describe", "explain", "feedback", "suggest"]):
                        return "text"
                    if any(x in q for x in ["choose", "select", "pick one"]):
                        return "radio"
                    if any(x in q for x in ["multiple", "select all", "choose all"]):
                        return "mcq"
                    if "matrix" in q or "compare" in q:
                        return "matrix"
                    if "upload" in q or "file" in q:
                        return "file"

                    # Default fallback
                    return "rating"


                new_qs = [{"question": q, "scale_type": infer_scale_type(q)} for q in ai_questions[:4]]
                questions.extend(new_qs)
                ai_questions_added = True
                print(f"✅ Added {len(new_qs)} AI-generated questions for focus '{topic}' ({tone}).")

            except Exception as e:
                print(f"⚠️ AI question generation failed (add): {e}")
                return jsonify({"error": f"AI customization failed: {str(e)}"}), 500

        elif action == "remove":
            if not remove_input:
                return jsonify({"message": "Specify which question to remove (e.g., Q2 or keyword)."}), 400

            # Support multiple comma-separated removals
            remove_targets = [r.strip().lower() for r in remove_input.split(",") if r.strip()]

            to_remove = []
            for i, q in enumerate(questions):
                for target in remove_targets:
                    if target == f"q{i+1}".lower() or target in q["question"].lower():
                        to_remove.append(i)
                        break

            if not to_remove:
                return jsonify({"message": f"No question found matching '{remove_input}'."}), 404

            for i in sorted(set(to_remove), reverse=True):
                removed_q = questions.pop(i)
                print(f"🗑️ Removed: {removed_q['question']}")

            # ✅ After removal, ask if user wants to add questions
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
        updated = 0
        for key, new_scale in scale_changes.items():
            if key.startswith("q") and key[1:].isdigit():
                idx = int(key[1:]) - 1
                if 0 <= idx < len(questions):
                    questions[idx]["scale_type"] = new_scale
                    updated += 1
            else:
                for q in questions:
                    if key.lower() in q["question"].lower():
                        q["scale_type"] = new_scale
                        updated += 1
        print(f"🔧 Updated {updated} scale types.")

    # Save updated questions
    selected["questions"] = questions

    # ---------------------- STEP 3: NEXT CUSTOMIZATION QUESTIONS ----------------------
    customization_qs = []

    # ✅ If AI questions were added, next ask about scale types
    if ai_questions_added:
        customization_qs = [{
            "question": "Would you like to adjust individual scale_types for specific questions?",
            "options": ["Yes", "No"]
        }]
    else:
        # Default flow when no new AI questions were added
        customization_qs = [
            {
                "question": "Would you like to add or remove any questions from this template?",
                "options": ["Add", "Remove", "No Changes"]
            },
            {
                "question": "Would you like to add questions related to any specific focus area? (e.g., Website design, Product quality, Service experience)",
                "allow_text_input": True
            },
            {
                "question": "What complexity level of questions do you prefer in this survey?",
                "options": ["Simple", "Moderate", "Detailed"]
            }
        ]

    print("✅ Customization process completed successfully.")
    return jsonify({
        "message": "✅ Template customization completed successfully.",
        "selected_template": selected,
        "customization_questions": customization_qs
    })


@app.route("/finalize_template", methods=["POST"])
def finalize_template():
    data = request.get_json() or {}
    final_template = data.get("final_template")

    if not final_template:
        return jsonify({"error": "Missing final_template"}), 400

    # Generate unique filename or ID
    template_id = datetime.now().strftime("%Y%m%d%H%M%S")
    file_path = os.path.join("finalized_templates", f"template_{template_id}.json")

    os.makedirs("finalized_templates", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(final_template, f, ensure_ascii=False, indent=2)

    print(f"✅ Final template saved: {file_path}")
    return jsonify({
        "message": "Template finalized successfully.",
        "template_id": template_id,
        "path": file_path
    })
# -----------------------
# RUN
# -----------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)