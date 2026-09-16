import json
import unittest
from app import app


class TestDatatypeAndQueryValidation(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_empty_and_datatype_validation(self):
        """Test empty, integer, list, and None input datatypes on /validate_input."""
        # Empty string
        res = self.client.post("/validate_input", json={"text": ""})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["is_valid"])
        self.assertIn("Input cannot be empty", data["message"])

        # None datatype
        res = self.client.post("/validate_input", json={"text": None})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["is_valid"])

        # Integer datatype (safely handled without crash)
        res = self.client.post("/validate_input", json={"text": 123456})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["is_valid"])

        # List datatype (safely handled without crash)
        res = self.client.post("/validate_input", json={"text": ["invalid", "list"]})
        self.assertEqual(res.status_code, 400)

    def test_query_parameter_validation(self):
        """Test sending input via GET URL query parameters."""
        # Valid survey topic via query param
        res = self.client.get("/validate_input?text=Customer%20Satisfaction")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["is_valid"])
        self.assertEqual(data["input"], "Customer Satisfaction")

        # Greeting via query param
        res = self.client.get("/validate_input?text=hello")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["is_valid"])
        self.assertIn("greeting", data["message"].lower())

        # Question flow via GET query param
        res = self.client.get("/generate_question_flow?user_input=Food%20Quality")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["original_user_input"], "Food Quality")

    def test_form_data_validation(self):
        """Test sending input via form data (application/x-www-form-urlencoded)."""
        res = self.client.post("/validate_input", data={"text": "Laptop Repair Feedback"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["is_valid"])
        self.assertEqual(data["input"], "Laptop Repair Feedback")

    def test_gibberish_and_off_topic_backend_messages(self):
        """Test that backend API returns proper error/validation messages for gibberish and off-topic inputs."""
        # Gibberish keyboard smash
        res = self.client.post("/validate_input", json={"text": "asdfghjkl"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["is_valid"])
        self.assertIn("not a valid survey topic", data["message"])

        # Off-topic question
        res = self.client.post("/validate_input", json={"text": "What is the weather today?"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["is_valid"])
        self.assertIn("not a valid survey topic", data["message"])

    def test_customize_and_finalize_query_and_datatype(self):
        """Test customization and finalization endpoints with stringified & structured payloads."""
        # Missing parameters
        res = self.client.post("/customize_selected_template", json={})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("Please select a template first to customize", data["message"])

        # Stringified JSON payload in query parameter
        mock_template = {
            "title": "NPS Survey",
            "purpose": "Test",
            "duration": "2 mins",
            "questions": [
                {"question": "How likely are you to recommend us?", "scale_type": "nps"}
            ]
        }
        templates_str = json.dumps([mock_template])
        res = self.client.get(f"/customize_selected_template?choice=Template%201&templates={templates_str}")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("selected_template", data)
        self.assertEqual(data["selected_template"]["title"], "NPS Survey")

        # Finalize template with stringified JSON
        template_str = json.dumps(mock_template)
        res = self.client.get(f"/finalize_template?final_template={template_str}")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["message"], "Template finalized successfully.")
        self.assertIn("template_id", data)

    def test_radio_question_structure(self):
        """Test that radio scale_type questions contain valid non-empty options array."""
        mock_template = {
            "title": "Radio Test Survey",
            "purpose": "Verify radio options",
            "duration": "2 mins",
            "questions": [
                {"question": "On a scale of 0-10, recommend us?", "scale_type": "nps"},
                {"question": "Did you encounter any issue?", "scale_type": "rating"},
                {"question": "Any other feedback?", "scale_type": "text"}
            ]
        }
        # Change Q2 scale to radio
        res = self.client.post("/customize_selected_template", json={
            "choice": "Template 1",
            "scale_action": "yes",
            "scale_changes": {"q2": "radio"},
            "templates": [mock_template]
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        updated_template = data["selected_template"]
        q2 = updated_template["questions"][1]
        
        self.assertEqual(q2["scale_type"], "radio")
        self.assertIn("options", q2)
        self.assertTrue(isinstance(q2["options"], list))
        self.assertGreater(len(q2["options"]), 0)


if __name__ == "__main__":
    unittest.main()

