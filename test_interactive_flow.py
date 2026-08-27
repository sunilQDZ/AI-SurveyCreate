import unittest
import json
from app import app

class TestInteractiveChatInputFlow(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_step_by_step_user_chat_flow(self):
        print("\n" + "="*70)
        print("SIMULATING STEP-BY-STEP USER CHAT FLOW (EXACT USER SCREENSHOT SCENARIO)")
        print("="*70)

        # Step 1: User types "i want to create survey" in chat box
        user_input_1 = "i want to create survey"
        print(f"\n[STEP 1] User Prompt: '{user_input_1}'")
        res1 = self.app.post("/generate_question_flow", data=json.dumps({"user_input": user_input_1}), content_type="application/json")
        data1 = res1.get_json()

        question_flow = data1.get("question_flow", [])
        print(f"-> Backend generated {len(question_flow)} setup questions:")
        for idx, q in enumerate(question_flow):
            print(f"   Q{idx+1} [{q['id']}]: {q['q']}")

        # State tracking in frontend
        survey_context = {
            "survey_type": None,
            "audience": None,
            "purpose": None,
            "touchpoint": None
        }
        collected_answers = {}

        # Simulated user answers typed in bottom chat box sequentially
        user_answers = [
            ("survey_type", "nps"),
            ("audience", "users"),
            ("purpose", "employee feedback"),
            ("touchpoint", "website")
        ]

        print("\n[SIMULATING USER TYPING ANSWERS IN CHAT BOX]")
        for q_idx, q_item in enumerate(question_flow):
            param_id = q_item["id"]
            param_question = q_item["q"]
            user_typed = user_answers[q_idx][1]

            print(f"\n Assistant Question Q{q_idx+1}: '{param_question}'")
            print(f" User Types in Main Input Box: '{user_typed}'")

            # Update frontend state (simulating script.js handleAnswer)
            collected_answers[param_id] = user_typed
            if param_id == "survey_type":
                survey_context["survey_type"] = "nps" if "nps" in user_typed.lower() else "general"
            else:
                survey_context[param_id] = user_typed

            print(f" [OK] Saved State -> {param_id}: '{survey_context[param_id]}'")

        # Step 5: Final Survey Generation Call
        print("\n[STEP 5] All 4 questions answered. Triggering /generate_survey ...")
        gen_res = self.app.post("/generate_survey", data=json.dumps({
            "user_input": user_input_1,
            "survey_type": survey_context["survey_type"],
            "answers": collected_answers
        }), content_type="application/json")

        gen_data = gen_res.get_json()
        surveys = gen_data.get("surveys", [])

        print(f"\nTemplates Generated Successfully: {len(surveys)} templates returned!")
        print(f"   Template 1 Title: {surveys[0]['title']}")
        print(f"   Template 1 Q1 (NPS): {surveys[0]['questions'][0]['question']}")
        print(f"   Template 1 Q5 (Text): {surveys[0]['questions'][-1]['question']}")

        self.assertEqual(len(surveys), 3)
        self.assertEqual(survey_context["survey_type"], "nps")
        self.assertEqual(survey_context["audience"], "users")
        self.assertEqual(survey_context["purpose"], "employee feedback")
        self.assertEqual(survey_context["touchpoint"], "website")

if __name__ == "__main__":
    unittest.main()
