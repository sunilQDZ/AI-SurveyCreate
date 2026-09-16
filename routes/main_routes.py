from flask import Blueprint, render_template, jsonify

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    return render_template("index.html")


@main_bp.app_errorhandler(400)
def bad_request_error(e):
    return jsonify({"error": "Bad Request", "message": "⚠️ Please provide valid survey details so we can create your template."}), 400


@main_bp.app_errorhandler(404)
def not_found_error(e):
    return jsonify({"error": "Not Found", "message": "⚠️ The requested survey feature was not found."}), 404


@main_bp.app_errorhandler(405)
def method_not_allowed_error(e):
    return jsonify({"error": "Method Not Allowed", "message": "⚠️ Invalid request method."}), 405


@main_bp.app_errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": "Internal Server Error", "message": "⚠️ Something went wrong while generating your survey. Please try again."}), 500
