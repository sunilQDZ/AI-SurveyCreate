import json
import re
from config import client, OPENAI_MODEL


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
   - Short phrase about what the survey is evaluating.
   - Extract phrases like "customer feedback", "food quality", "service experience", "laptop repair",
     "survey for X", "survey on X", "survey about X", "survey regarding X".
   - Examples:
       "customer feedback nps survey" → purpose = "Customer Feedback", audience = "Customers", survey_type = "nps"
       "survey for education department" → purpose = "education department"
       "csat survey for laptop repair" → purpose = "laptop repair"
       "nps survey about our mobile app" → purpose = "our mobile app"
   - Keep purpose close to original user wording.
   - If no clear topic/purpose is given at all, return null.

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
            model=OPENAI_MODEL,
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

        if audience:
            lower_aud = audience.lower()
            dept_words = ["department", "team", "branch", "office", "unit", "center", "centre"]
            if any(w in lower_aud for w in dept_words):
                if not purpose:
                    purpose = audience
                audience = None

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
        print("[WARNING] OpenAI analysis failed:", e)
        return empty_result
