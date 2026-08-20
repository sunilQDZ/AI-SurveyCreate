# 🚀 AI-SurveyCreate

An intelligent, AI-powered Survey Template Generator & Customization Platform built with **Flask**, **OpenAI API**, and **Vanilla JS**.

`AI-SurveyCreate` dynamically analyzes user requests, asks smart follow-up questions to understand missing context (Survey Type, Audience, Purpose, Touchpoint), and generates multi-question survey templates tailored for customer experience (CX), product feedback, education, healthcare, and enterprise teams.

---

## ✨ Features

- 🧠 **AI Parameter Detection & Smart Setup**: Analyzes user prompts in real-time to detect survey requirements. If missing details are detected, it prompts the user with guided options.
- 📊 **Multi-Type Survey Support**:
  - **NPS** (Net Promoter Score: 0–10 scale)
  - **CSAT** (Customer Satisfaction: 1–5 or 1–7 scale)
  - **CES** (Customer Effort Score: 1–5 scale)
  - **General / Custom Feedback** (Text, Radio, MCQ, Rating, Matrix, File Upload)
- 🎨 **Interactive Customization Engine**: Easily add AI-generated questions, remove existing questions, adjust scale types, or modify question complexity (Simple, Moderate, Detailed).
- 🛡️ **Production Fallback Engine**: Built-in fallback template generator guarantees uninterrupted operation even during API limits or network outages.
- ⚡ **Production Ready**: Pre-configured with **Waitress** WSGI multi-threaded server for live deployment.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, Flask, Flask-CORS, Waitress, Python-Dotenv
- **AI / LLM Integration**: OpenAI API (`gpt-4o-mini` / `gpt-3.5-turbo`)
- **Frontend**: HTML5, Vanilla CSS3 (Custom Dark/Glassmorphism theme), ES6 JavaScript

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/sunilQDZ/AI-SurveyCreate.git
cd AI-SurveyCreate
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
OPENAI_API_KEY="your-openai-api-key-here"

# Set to "production" for Waitress WSGI server or "development" for Flask debug server
FLASK_ENV="development"
```

### 5. Run the Application
```bash
python app.py
```
Open your browser and navigate to `http://localhost:5000`.

---

## 🔌 API Endpoints Overview

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/` | `GET` | Main web UI dashboard |
| `/generate_question_flow` | `POST` | Analyzes initial user prompt and returns missing parameter questions |
| `/generate_survey` | `POST` | Generates 3 initial survey templates via OpenAI (or Fallback Engine) |
| `/generate_more_surveys` | `POST` | Generates 3 additional survey templates refined by focus area |
| `/customize_selected_template` | `POST` | Dynamically adds AI questions, removes target questions, or changes scales |
| `/finalize_template` | `POST` | Finalizes the survey and saves JSON template output |

---

## 📄 License
This project is open source and available under the [MIT License](LICENSE).
