import unittest
import json
from app import app

class TestHybridSurveyFlow(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_case_1_fully_detailed_prompt(self):
        """Test Case 1: Fully detailed prompt with all 4 parameters present."""
        payload = {
            "user_input": "I want an NPS survey for Employees about Employee Feedback on Website",
            "survey_type": ""
        }
        response = self.app.post("/generate_question_flow", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        print("\n--- Test 1: Fully Detailed Prompt ---")
        print(f"Detected Survey Type: {data.get('detected_survey_type')}")
        print(f"Detected Audience: {data.get('detected_audience')}")
        print(f"Detected Purpose: {data.get('detected_purpose')}")
        print(f"Detected Touchpoint: {data.get('detected_touchpoint')}")
        print(f"All Detected: {data.get('all_detected')}")

        self.assertIn(data.get("detected_survey_type"), ["nps", "csat", "ces", "general"])
        self.assertIsNotNone(data.get("detected_audience"))
        self.assertIsNotNone(data.get("detected_purpose"))
        self.assertIsNotNone(data.get("detected_touchpoint"))

    def test_case_2_partial_prompt(self):
        """Test Case 2: Partial prompt (e.g. Employee Feedback). Missing type & touchpoint."""
        payload = {
            "user_input": "Employee Feedback",
            "survey_type": ""
        }
        response = self.app.post("/generate_question_flow", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        print("\n--- Test 2: Partial Prompt (Employee Feedback) ---")
        print(f"Detected Audience: {data.get('detected_audience')}")
        print(f"Detected Purpose: {data.get('detected_purpose')}")
        print(f"Missing Question Count: {len(data.get('question_flow', []))}")
        
        # Audience & Purpose should be detected
        self.assertEqual(data.get("detected_audience"), "Employees")
        self.assertIsNotNone(data.get("detected_purpose"))
        # Should ask follow-up questions for missing fields
        self.assertTrue(len(data.get("question_flow", [])) > 0)

    def test_case_3_csat_store_repair(self):
        """Test Case 3: CSAT survey for laptop repair at store."""
        payload = {
            "user_input": "CSAT survey for Customers about laptop repair at store visit",
            "survey_type": ""
        }
        response = self.app.post("/generate_question_flow", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        print("\n--- Test 3: CSAT Store Repair ---")
        print(f"Detected Survey Type: {data.get('detected_survey_type')}")
        print(f"Detected Touchpoint: {data.get('detected_touchpoint')}")
        
        self.assertEqual(data.get("detected_survey_type"), "csat")
        self.assertEqual(data.get("detected_audience"), "Customers")

    def test_case_4_ces_online_checkout(self):
        """Test Case 4: CES survey for online checkout flow."""
        payload = {
            "user_input": "CES effort score survey for Users about online checkout flow on mobile app",
            "survey_type": ""
        }
        response = self.app.post("/generate_question_flow", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        print("\n--- Test 4: CES Mobile App Checkout ---")
        print(f"Detected Survey Type: {data.get('detected_survey_type')}")
        print(f"Detected Touchpoint: {data.get('detected_touchpoint')}")

        self.assertEqual(data.get("detected_survey_type"), "ces")

    def test_case_5_survey_generation(self):
        """Test Case 5: End-to-End Template Generation endpoint."""
        payload = {
            "user_input": "Customer Satisfaction for Mobile App Checkout",
            "survey_type": "csat"
        }
        response = self.app.post("/generate_survey", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        print("\n--- Test 5: Survey Template Generation ---")
        surveys = data.get("surveys", [])
        print(f"Generated Templates Count: {len(surveys)}")
        self.assertTrue(len(surveys) >= 1)
        # Check first question of first template is NPS
        q0 = surveys[0]["questions"][0]
        q_last = surveys[0]["questions"][-1]
        print(f"Q1 Scale Type: {q0.get('scale_type')}")
        print(f"Last Q Scale Type: {q_last.get('scale_type')}")
        self.assertEqual(q0.get("scale_type"), "nps")
        self.assertEqual(q_last.get("scale_type"), "text")

if __name__ == "__main__":
    unittest.main()
