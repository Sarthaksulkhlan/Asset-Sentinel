import json
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app)  # Allow requests from React / Lovable frontend on any origin

# File paths - both files must be in the same folder as app.py
ASSETS_FILE = Path("assets.json")
ALERTS_FILE = Path("alerts.json")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def read_json_file(file_path):
    """
    Read a JSON file and return its contents as a Python list.
    Returns an empty list if the file does not exist or is unreadable.
    """
    if not file_path.exists():
        return []
    try:
        content = file_path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARNING] Could not read {file_path.name}: {e}")
        return []


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.route("/api/assets", methods=["GET"])
def get_assets():
    """
    GET /api/assets
    Returns all hardware snapshots from assets.json.
    """
    assets = read_json_file(ASSETS_FILE)
    return jsonify(assets)


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """
    GET /api/alerts
    Returns all alert records from alerts.json.
    """
    alerts = read_json_file(ALERTS_FILE)
    return jsonify(alerts)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 50)
    print("  Asset Sentinel Backend")
    print("  Running on http://localhost:5000")
    print("  Endpoints:")
    print("    GET /api/assets")
    print("    GET /api/alerts")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)