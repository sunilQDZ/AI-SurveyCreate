import pandas as pd
import json

excel_path = r"D:\SurveyAI\CX_Survey_Questions (1).xlsx"
output_path = "industry_templates.json"

# Read all sheets
xls = pd.ExcelFile(excel_path)
industry_templates = {}

for sheet_name in xls.sheet_names:
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
    df = df.dropna(how="all").reset_index(drop=True)

    industry_data = {}
    current_type = None
    current_questions = []

    for i, row in df.iterrows():
        first_cell = str(row[0]).strip().lower()

        # Detect survey type headers (NPS, CSAT, CES)
        if any(keyword in first_cell for keyword in ["nps", "csat", "ces"]):
            # Save previous survey type if exists
            if current_type and current_questions:
                industry_data[current_type] = [{
                    "survey_title": f"{sheet_name} {current_type} Survey",
                    "duration": "2–3 min",
                    "questions": current_questions,
                    "user_recommendation_input": "Do you want to know purpose and duration for doing the above survey?"
                }]
            # Start new survey type
            current_type = row[0].strip()
            current_questions = []
            continue

        # Skip header rows (like "Question" column)
        if "question" in first_cell:
            continue

        # Process question row (expecting at least Question | Scale | Duration | Purpose)
        if current_type and len(row) >= 4:
            question_text = str(row[0]).strip()
            scale_text = str(row[1]).strip()
            duration_text = str(row[2]).strip()
            purpose_text = str(row[3]).strip()

            # Skip empty questions
            if question_text and question_text.lower() != "nan":
                question_data = {
                    "question": question_text,
                    "scale": scale_text if scale_text and scale_text.lower() != "nan" else "text",
                    "purpose": purpose_text if purpose_text and purpose_text.lower() != "nan" else None,
                    "duration": duration_text if duration_text and duration_text.lower() != "nan" else None
                }
                current_questions.append(question_data)

    # Save last survey type for sheet
    if current_type and current_questions:
        industry_data[current_type] = [{
            "survey_title": f"{sheet_name} {current_type} Survey",
            "duration": "2–3 min",
            "questions": current_questions,
            "user_recommendation_input": "Do you want to know purpose and duration for doing the above survey?"
        }]

    # Add industry to final dictionary
    if industry_data:
        industry_templates[sheet_name] = industry_data

# Save JSON
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(industry_templates, f, indent=2, ensure_ascii=False)

print(f"✅ JSON saved successfully: {output_path}")
