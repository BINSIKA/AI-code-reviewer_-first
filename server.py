import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from code_parser import validate_and_parse
from error_detector import analyze_code_errors
from ai_suggester import AISuggester

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route("/api/review", methods=["POST"])
def review_code():
    data = request.get_json()
    code = data.get("code", "")

    if not code:
        return jsonify({"error": "No code provided"}), 400

    final_report = {}

    parse_result = validate_and_parse(code)
    if parse_result["status"] == "error":
        return jsonify({
            "parse": parse_result,
            "static": {"suggestions": []},
            "ai": {"report": "Parsing failed. Fix syntax errors to get AI feedback."}
        })
    
    final_report["parse"] = {"status": "success", "message": parse_result["message"]}
    static_analysis = analyze_code_errors(parse_result["tree"])
    final_report["static"] = {"suggestions": static_analysis["suggestions"]}

    try:
        suggester = AISuggester()
        ai_feedback = suggester.get_suggestions(code, static_analysis["suggestions"])
        final_report["ai"] = {"report": ai_feedback}
    except Exception as e:
        final_report["ai"] = {"report": f"⚠️ AI Error: {str(e)}"}

    return jsonify(final_report)


if __name__ == "__main__":
    print("🚀 Backend running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)

