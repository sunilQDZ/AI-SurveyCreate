import unittest
import json
import os
from app import app

class TestFullBackendAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_api_1_home_dashboard(self):
        """API 1: GET / (Dashboard UI HTML endpoint)"""
        response = self.app.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Smart Survey Creator", response.data)
        print("\n[API TEST 1] GET / -> 200 OK")

    def test_api_2_generate_question_flow(self):
        """API 2: POST /generate_question_flow"""
        payload = {
            "user_input": "NPS survey for Employees about Employee Feedback on Website",
            "survey_type": ""
        }
        response = self.app.post("/generate_question_flow", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("all_detected"))
        self.assertEqual(data.get("detected_survey_type"), "nps")
        self.assertEqual(data.get("detected_audience"), "Employees")
        print("\n[API TEST 2] POST /generate_question_flow -> 200 OK")

    def test_api_3_generate_survey(self):
        """API 3: POST /generate_survey"""
        payload = {
            "user_input": "Customer Satisfaction for Mobile App Checkout",
            "survey_type": "csat"
        }
        response = self.app.post("/generate_survey", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        surveys = data.get("surveys", [])
        self.assertTrue(len(surveys) >= 1)
        self.assertEqual(surveys[0]["questions"][0]["scale_type"], "nps")
        self.assertEqual(surveys[0]["questions"][-1]["scale_type"], "text")
        print(f"\n[API TEST 3] POST /generate_survey -> 200 OK ({len(surveys)} templates generated)")

    def test_api_4_generate_more_surveys(self):
        """API 4: POST /generate_more_surveys"""
        payload = {
            "focus_area": "Payment Gateways",
            "survey_type": "csat",
            "context": {
                "original_user_input": "Customer Satisfaction for Mobile App Checkout",
                "detected_survey_type": "csat",
                "detected_audience": "Customers",
                "detected_purpose": "Mobile App Checkout",
                "detected_touchpoint": "Mobile app"
            }
        }
        response = self.app.post("/generate_more_surveys", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        templates = data.get("templates", [])
        self.assertTrue(len(templates) >= 1)
        print(f"\n[API TEST 4] POST /generate_more_surveys -> 200 OK ({len(templates)} refined templates generated)")

    def test_api_5_customize_selected_template(self):
        """API 5: POST /customize_selected_template"""
        mock_templates = [{
            "title": "CSAT Mobile App Survey",
            "purpose": "Evaluate checkout experience",
            "duration": "2–2.5 mins",
            "questions": [
                {"question": "How likely are you to recommend us?", "scale_type": "nps"},
                {"question": "How satisfied are you with the payment speed?", "scale_type": "csat"},
                {"question": "Was checkout easy?", "scale_type": "ces"},
                {"question": "Did you encounter errors?", "scale_type": "radio", "options": ["Yes", "No"]},
                {"question": "Any other feedback?", "scale_type": "text"}
            ]
        }]
        payload = {
            "templates": mock_templates,
            "choice": "Template 1",
            "action": "add",
            "focus_area": "Security",
            "complexity": "Moderate"
        }
        response = self.app.post("/customize_selected_template", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        customized = data.get("selected_template", {})
        self.assertTrue(len(customized.get("questions", [])) > len(mock_templates[0]["questions"]))
        print(f"\n[API TEST 5] POST /customize_selected_template -> 200 OK ({len(customized.get('questions', []))} questions in customized template)")

    def test_api_6_finalize_template(self):
        """API 6: POST /finalize_template"""
        mock_final_template = {
            "title": "Finalized CSAT Mobile App Survey",
            "purpose": "Final evaluation template",
            "duration": "2 mins",
            "questions": [
                {"question": "On a scale of 0-10, recommend us?", "scale_type": "nps"},
                {"question": "Please provide feedback.", "scale_type": "text"}
            ]
        }
        payload = {"final_template": mock_final_template}
        response = self.app.post("/finalize_template", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        template_id = data.get("template_id")
        file_path = data.get("path")
        self.assertIsNotNone(template_id)
        self.assertTrue(os.path.exists(file_path))
        print(f"\n[API TEST 6] POST /finalize_template -> 200 OK (Saved template ID: {template_id} at {file_path})")

if __name__ == "__main__":
    unittest.main()
