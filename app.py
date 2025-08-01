import re

from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@app.route("/")
def index():
    return redirect(url_for("login"))


def make_code(name: str, taken_codes: set) -> str:
    base = re.sub(r'[^a-z0-9]', '', name.lower())  # slug
    if not base:
        base = "user"
    code = f"{base}2025"
    i = 1
    while code in taken_codes:
        i += 1
        code = f"{base}2025{i}"
    return code


@app.route("/login", methods=["GET", "POST"])
def login():
    data = load_data()
    if request.method == "POST":
        new_name = request.form.get("name", "").strip()
        if new_name:
            lb = data.get("leaderboard", [])
            match = next((x for x in lb if x["name"].lower() == new_name.lower()), None)

            if match:
                # Use existing record
                data["user"]["name"] = match["name"]
                data["user"]["referralCode"] = match["referralCode"]
                data["user"]["totalRaised"] = match["totalRaised"]
            else:
                # 2) Create & persist a brand-new user
                taken = {x["referralCode"] for x in lb}
                new_code = make_code(new_name, taken)
                new_rec = {"name": new_name, "referralCode": new_code, "totalRaised": 0}
                lb.append(new_rec)

                # Update current user view
                data["user"]["name"] = new_name
                data["user"]["referralCode"] = new_code
                data["user"]["totalRaised"] = 0

                # Optional: keep leaderboard sorted (highest first)
                data["leaderboard"] = sorted(lb, key=lambda x: x["totalRaised"], reverse=True)

            save_data(data)
        return redirect(url_for("dashboard"))
    return render_template("login.html", name=data["user"]["name"])


@app.route("/dashboard")
def dashboard():
    data = load_data()
    return render_template("dashboard.html", user=data["user"])


@app.route("/leaderboard")
def leaderboard():
    data = load_data()
    # sort by totalRaised desc
    items = sorted(data["leaderboard"], key=lambda x: x["totalRaised"], reverse=True)
    return render_template("leaderboard.html", items=items)


# ==== API endpoints (dummy) ====

@app.route("/api/user")
def api_user():
    data = load_data()
    return jsonify(data["user"])


@app.route("/api/leaderboard")
def api_leaderboard():
    data = load_data()
    items = sorted(data["leaderboard"], key=lambda x: x["totalRaised"], reverse=True)
    return jsonify({"items": items})


if __name__ == "__main__":
    # Local dev server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
