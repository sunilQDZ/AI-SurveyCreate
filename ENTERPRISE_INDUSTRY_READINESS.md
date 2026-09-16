# Enterprise AI Survey Creator - Production & Industry Readiness Guide

## Executive Overview
The **AI Survey Creator** is an enterprise-grade, multi-client RESTful API backend designed to automatically generate, validate, customize, and export professional surveys across any industry.

---

## 🏬 Supported Industry Vertical Models

Out of the box, the engine dynamically adapts questions, rating scales, and choice options for:

1. **E-Commerce & Retail**
   - Touchpoints: Website, Mobile App, Store Pickup (Click & Collect), Express Delivery, Returns & Refunds.
   - Question Types: Order satisfaction, delivery speed, product quality, return reasons.

2. **Healthcare & Hospital Services**
   - Touchpoints: In-Person Clinic, Telehealth / Video Consultation, Emergency Room, Pharmacy & Lab.
   - Question Types: Patient satisfaction, doctor consultation quality, nursing care, billing clarity.

3. **Banking & Financial Services**
   - Touchpoints: Mobile Banking App, Web Portal, ATM, Branch Visit, Call Center Support.
   - Question Types: Transaction ease, payment speed, loan application experience, support resolution.

4. **Food, Dining & Hospitality**
   - Touchpoints: Dine-in, Takeaway / Pickup, Home Delivery, Drive-Thru, Hotel Booking.
   - Question Types: Food taste & hygiene, delivery speed, packaging quality, booking ease.

5. **SaaS & Technology**
   - Touchpoints: Web App, Mobile App (iOS/Android), Onboarding Flow, Helpdesk / Support Ticket.
   - Question Types: Platform ease of use, feature satisfaction, system reliability, bug reporting.

6. **Education & E-Learning**
   - Touchpoints: Online Classes, Classroom Sessions, Learning Portal, Student Services.
   - Question Types: Course material quality, instructor effectiveness, platform usability.

7. **HR & Employee Experience**
   - Touchpoints: Onboarding, Annual Review, Team Engagement, Workplace Facilities.
   - Question Types: Employee Net Promoter Score (eNPS), team culture, manager support.

8. **B2B & Client Services**
   - Touchpoints: Project Delivery, Quarterly Business Review (QBR), Vendor Evaluation.
   - Question Types: Client satisfaction, deliverable quality, SLA adherence.

---

## 📊 Supported Question Scale & Field Types

| Scale Type | Description | Industry Use Case |
| :--- | :--- | :--- |
| **`nps`** | Net Promoter Score (0–10 recommendation scale) | Mandatory Q1 in all templates for benchmark loyalty tracking |
| **`csat`** | Customer Satisfaction Score (1–5 rating) | Overall satisfaction with service, product, or interaction |
| **`ces`** | Customer Effort Score (1–5 ease scale) | Evaluating how easy it was to complete a task or transaction |
| **`rating`** | 1–5 Star or Numeric Rating | Quality, speed, cleanliness, communication ratings |
| **`radio`** | Single Choice Radio Selection | Single-choice selection with dynamic industry options |
| **`mcq`** | Multiple Choice Checkboxes | Selecting key drivers, features used, or areas of improvement |
| **`matrix`** | Multi-Attribute Grid Rating | Comparing multiple attributes (e.g. Price, Quality, Speed) |
| **`text`** | Open-Ended Feedback Text | Mandatory final question for qualitative suggestions |
| **`file`** | Attachment Upload | Document, receipt, or screenshot uploads |

---

## ⚙️ Core API Endpoints

### 1. `/validate_input` (GET / POST)
Validates input text in real-time. Distinguishes valid survey topics from greetings, keyboard smashes, and off-topic questions.
- **Parameters**: `text`, `question_id`, `field_type` (supports aliases `user_input`, `prompt`, `topic`, `answer`)
- **Response**: `is_valid` boolean, sanitized `input`, backend error `message`, `options` array.

### 2. `/generate_question_flow` (GET / POST)
Analyzes user requirements and drives conversational onboarding setup questions.
- **Parameters**: `user_input`
- **Response**: Extracted metadata (`survey_type`, `audience`, `purpose`, `touchpoint`) and remaining setup `question_flow`.

### 3. `/generate_survey` (GET / POST)
Generates 3 distinct, domain-specific survey templates adhering to enterprise CX pattern constraints.
- **Parameters**: `user_input`, `survey_type`, `answers`
- **Response**: Array of 3 template objects with title, purpose, duration, and question list.

### 4. `/generate_more_surveys` (GET / POST)
Generates new template variations focused on a specific refinement area.
- **Parameters**: `focus_area`, `survey_type`, `context`
- **Response**: Refined survey templates matching the new focus area.

### 5. `/customize_selected_template` (GET / POST)
Edits selected templates by adding AI questions, removing questions, changing scale types, or updating title/purpose.
- **Parameters**: `choice` (e.g. `"Template 1"` or `"1"`), `templates`, `action` (`"add"`/`"remove"`), `focus_area`, `complexity`, `scale_action`, `scale_changes`
- **Response**: Updated template object and customization questions.

### 6. `/finalize_template` (GET / POST)
Exports and persists finalized templates directly to storage (`finalized_templates/`).
- **Parameters**: `final_template` (dict or JSON string)
- **Response**: `template_id`, persisted file `path`.


---

## 🚀 Production Deployment Guidelines

1. **Production Server (`Waitress`)**:
   - Run via Waitress multi-threaded WSGI server:
     ```bash
     python app.py
     ```
   - Automatically runs on port `5005` with `8` worker threads in production mode.

2. **Environment Configuration (`.env`)**:
   - Configure `OPENAI_API_KEY`, `OPENAI_MODEL` (`gpt-4o-mini` or `gpt-4o`), `FLASK_ENV=production`.

3. **CORS & Multi-Client Access**:
   - `flask-cors` is configured globally across all blueprints to allow seamless integration from any web dashboard, mobile app, or client portal.

4. **Zero-Downtime Fallback**:
   - Built-in production fallback engine (`build_fallback_templates`) ensures continuous operation even if OpenAI API is temporarily unreachable.
