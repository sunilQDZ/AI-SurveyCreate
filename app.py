import os
from flask import Flask
from flask_cors import CORS

from config import OPENAI_API_KEY, OPENAI_MODEL
from routes.main_routes import main_bp
from routes.survey_routes import survey_bp

app = Flask(__name__)
CORS(app)

# Register Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(survey_bp)

if __name__ == "__main__":
    env = os.getenv("FLASK_ENV", "development")
    port = int(os.getenv("PORT", 5005))
    if env == "production":
        from waitress import serve
        print(f"[INFO] Starting production server on http://localhost:{port} (http://127.0.0.1:{port}) ...")
        serve(app, host="0.0.0.0", port=port, threads=8)
    else:
        print(f"[INFO] Starting development server on http://localhost:{port} (http://127.0.0.1:{port}) ...")
        app.run(host="0.0.0.0", port=port, debug=True)
