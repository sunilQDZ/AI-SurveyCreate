import json
import unittest
from app import app


class TestAllAPIsAndEdgeCases(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    # ==========================================
    # 1. /validate_input ENDPOINT & EDGE CASES
    # ==========================================
    def test_validate_input_success_aliases(self):
        """Test /validate_input with all dynamic input parameter aliases (text, user_input, user_prompt, answer, prompt, topic, input)."""
        aliases = ["text", "user_input", "user_prompt", "answer", "prompt", "topic", "input"]
        for alias in aliases:
            res = self.client.post("/validate_input", json={alias: "Customer Satisfaction"})
            self.assertEqual(res.status_code, 200, f"Failed for alias: {alias}")
            data = res.get_json()
            self.assertTrue(data["is_valid"])
            self.assertEqual(data["input"], "Customer Satisfaction")

    def test_validate_input_query_and_form(self):
        """Test GET query params and form data for /validate_input."""
        # Query Param
        res = self.client.get("/validate_input?text=Laptop%20Repair%20Feedback")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["is_valid"])

        # Form Data
        res = self.client.post("/validate_input", data={"text": "E-commerce Shopping Experience"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["is_valid"])

    def test_validate_input_edge_cases(self):
        """Test null, empty, invalid types, gibberish, off-topic, and greetings on /validate_input."""
        # Empty string -> 400
        res = self.client.post("/validate_input", json={"text": ""})
        self.assertEqual(res.status_code, 400)

        # None -> 400
        res = self.client.post("/validate_input", json={"text": None})
        self.assertEqual(res.status_code, 400)

        # Pure numbers -> 200, invalid
        res = self.client.post("/validate_input", json={"text": 123456})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.get_json()["is_valid"])

        # List datatype -> 400
        res = self.client.post("/validate_input", json={"text": ["invalid"]})
        self.assertEqual(res.status_code, 400)

        # Greetings -> 200, invalid
        res = self.client.post("/validate_input", json={"text": "hello"})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.get_json()["is_valid"])

        # Long Gibberish -> 200, invalid with truncated display message
        long_gibberish = "asdfghjklqwertyuiopzxcvbnm1234567890asdfghjkl"
        res = self.client.post("/validate_input", json={"text": long_gibberish})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["is_valid"])
        self.assertIn("...", data["message"])
        self.assertNotIn(long_gibberish, data["message"])

        # Off-topic -> 200, invalid
        res = self.client.post("/validate_input", json={"text": "What is the capital of France?"})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.get_json()["is_valid"])


    def test_validate_input_question_id_field_types(self):
        """Test question_id specific validation branches (survey_type, audience, purpose, touchpoint)."""
        # Valid survey_type
        res = self.client.post("/validate_input", json={"question_id": "survey_type", "text": "NPS"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["is_valid"])

        # Invalid survey_type
        res = self.client.post("/validate_input", json={"question_id": "survey_type", "text": "hello"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["is_valid"])
        self.assertIn("options", data)

        # Audience invalid
        res = self.client.post("/validate_input", json={"question_id": "audience", "text": "asdfghjkl"})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.get_json()["is_valid"])

    # ==================================================
    # 2. /generate_question_flow ENDPOINT & EDGE CASES
    # ==================================================
    def test_generate_question_flow_valid_and_greeting(self):
        """Test /generate_question_flow for valid input, greetings, and query params."""
        # Greeting
        res = self.client.post("/generate_question_flow", json={"user_input": "hi"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("is_greeting"))
        self.assertIn("question_flow", data)

        # Valid input via GET
        res = self.client.get("/generate_question_flow?user_input=Hospital%20Feedback")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["original_user_input"], "Hospital Feedback")

    def test_generate_question_flow_invalid(self):
        """Test /generate_question_flow for gibberish and off-topic questions."""
        res = self.client.post("/generate_question_flow", json={"user_input": "asdfghjkl"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("is_invalid"))

    # ==========================================
    # 3. /generate_survey ENDPOINT & EDGE CASES
    # ==========================================
    def test_generate_survey_valid_and_pattern_rules(self):
        """Test /generate_survey template generation and pattern rules (Q0 = NPS, Q_last = Text)."""
        res = self.client.post("/generate_survey", json={"user_input": "Food Delivery Feedback"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("templates", data)
        templates = data["templates"]
        self.assertGreaterEqual(len(templates), 1)

        for t in templates:
            qs = t["questions"]
            self.assertEqual(qs[0]["scale_type"], "nps")
            self.assertEqual(qs[-1]["scale_type"], "text")

    def test_generate_survey_edge_cases(self):
        """Test missing input, stringified answers payload, and invalid input on /generate_survey."""
        # Missing input -> 400
        res = self.client.post("/generate_survey", json={})
        self.assertEqual(res.status_code, 400)

        # Stringified JSON answers parameter
        answers_str = json.dumps({"purpose": "Laptop Repair", "audience": "Customers"})
        res = self.client.post("/generate_survey", json={"user_input": "hi", "answers": answers_str})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("templates", data)

    # ===============================================
    # 4. /generate_more_surveys ENDPOINT & EDGE CASES
    # ===============================================
    def test_generate_more_surveys_valid_and_edge_cases(self):
        """Test /generate_more_surveys for focus area generation and stringified context."""
        # Missing focus area -> 400
        res = self.client.post("/generate_more_surveys", json={})
        self.assertEqual(res.status_code, 400)

        # Invalid focus area -> 400
        res = self.client.post("/generate_more_surveys", json={"focus_area": "asdfghjkl"})
        self.assertEqual(res.status_code, 400)

        # Valid focus area with stringified context payload
        context_str = json.dumps({"original_user_input": "Food Delivery", "detected_survey_type": "csat"})
        res = self.client.post("/generate_more_surveys", json={"focus_area": "Packaging", "context": context_str})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("surveys", data)

    # =======================================================
    # 5. /customize_selected_template ENDPOINT & EDGE CASES
    # =======================================================
    def test_customize_selected_template_edge_cases(self):
        """Test /customize_selected_template for missing parameters, out of bounds index, scale updates, and stringified payloads."""
        # Missing parameters -> 400
        res = self.client.post("/customize_selected_template", json={})
        self.assertEqual(res.status_code, 400)

        # Choice out of bounds -> 400
        mock_template = {
            "title": "CSAT Survey",
            "purpose": "Test",
            "duration": "2 mins",
            "questions": [
                {"question": "How likely are you to recommend us?", "scale_type": "nps"},
                {"question": "How satisfied are you with our service?", "scale_type": "csat"},
                {"question": "Any other feedback?", "scale_type": "text"}
            ]
        }
        res = self.client.post("/customize_selected_template", json={
            "choice": "Template 99",
            "templates": [mock_template]
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("out of bounds", res.get_json()["message"])

        # Focus area greeting check -> 400
        res = self.client.post("/customize_selected_template", json={
            "choice": "Template 1",
            "focus_area": "hello",
            "templates": [mock_template]
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("greeting", res.get_json()["message"].lower())

        # Focus area gibberish check -> 400
        res = self.client.post("/customize_selected_template", json={
            "choice": "Template 1",
            "focus_area": "asdfghjkl",
            "templates": [mock_template]
        })
        self.assertEqual(res.status_code, 400)

        # Valid customization with scale changes and title update
        res = self.client.post("/customize_selected_template", json={
            "choice": "Template 1",
            "title": "Customized CSAT Survey",
            "scale_action": "yes",
            "scale_changes": json.dumps({"q2": "radio"}),
            "templates": [mock_template]
        })

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["selected_template"]["title"], "Customized CSAT Survey")
        self.assertEqual(data["selected_template"]["questions"][1]["scale_type"], "radio")

    # ============================================
    # 6. /finalize_template ENDPOINT & EDGE CASES
    # ============================================
    def test_finalize_template_valid_and_edge_cases(self):
        """Test /finalize_template for missing final_template, dict payload, and stringified JSON payload."""
        # Missing payload -> 400
        res = self.client.post("/finalize_template", json={})
        self.assertEqual(res.status_code, 400)

        # Dict payload -> 200
        mock_template = {
            "title": "Finalized Survey",
            "purpose": "Test Finalization",
            "questions": [{"question": "On a scale of 0-10, recommend us?", "scale_type": "nps"}]
        }
        res = self.client.post("/finalize_template", json={"final_template": mock_template})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["message"], "Template finalized successfully.")
        self.assertIn("template_id", data)

        # Stringified JSON payload -> 200
        res = self.client.get(f"/finalize_template?final_template={json.dumps(mock_template)}")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["message"], "Template finalized successfully.")


if __name__ == "__main__":
    unittest.main()
