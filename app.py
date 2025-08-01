from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from functools import wraps
import os, json, re

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

DATA_PATH = os.path.join(os.path.dirname(__file__), "data.json")


def make_code(name: str, taken_codes: set) -> str:
    base = re.sub(r'[^a-z0-9]', '', name.lower())
    if not base:
        base = "user"
    code = f"{base}2025"
    i = 1
    while code in taken_codes:
        i += 1
        code = f"{base}2025{i}"
    return code


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_name" not in session:
            flash("Please log in first.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    data = load_data()
    if request.method == "POST":
        new_name = request.form.get("name", "").strip()
        if new_name:
            lb = data.get("leaderboard", [])
            match = next((x for x in lb if x["name"].lower() == new_name.lower()), None)

            if match:
                data["user"].update(match)
            else:
                code = re.sub(r'[^a-z0-9]', '', new_name.lower()) or "user"
                code = f"{code}2025"
                new_rec = {"name": new_name, "referralCode": code, "totalRaised": 0}
                lb.append(new_rec)
                data["leaderboard"] = sorted(lb, key=lambda x: x["totalRaised"], reverse=True)
                data["user"].update(new_rec)

            save_data(data)
            # set session
            session["user_name"] = data["user"]["name"]
            flash(f"Welcome, {session['user_name']}!")
            return redirect(url_for("dashboard"))
        flash("Please enter a name.")
    return render_template("login.html", name=data["user"]["name"])


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    data = load_data()
    return render_template("dashboard.html", user=data["user"])


@app.route("/leaderboard")
def leaderboard():
    data = load_data()
    items = sorted(data["leaderboard"], key=lambda x: x["totalRaised"], reverse=True)
    return render_template("leaderboard.html", items=items)


@app.route("/api/user")
def api_user():
    data = load_data()
    return jsonify(data["user"])


@app.route("/api/leaderboard")
def api_leaderboard():
    data = load_data()
    items = sorted(data["leaderboard"], key=lambda x: x["totalRaised"], reverse=True)
    return jsonify({"items": items})


@app.route("/funds/add", methods=["POST"])
@login_required
def add_funds():
    data = load_data()
    try:
        amount = float(request.form.get("amount", "0"))
    except ValueError:
        amount = -1
    if amount <= 0:
        flash("Enter a valid positive amount.")
        return redirect(url_for("dashboard"))

    # Update current user
    data["user"]["totalRaised"] += amount

    # Update leaderboard entry (create if missing)
    lb = data.get("leaderboard", [])
    for x in lb:
        if x["referralCode"] == data["user"]["referralCode"]:
            x["totalRaised"] = data["user"]["totalRaised"]
            break
    else:
        lb.append({
            "name": data["user"]["name"],
            "referralCode": data["user"]["referralCode"],
            "totalRaised": data["user"]["totalRaised"],
        })
    data["leaderboard"] = sorted(lb, key=lambda x: x["totalRaised"], reverse=True)
    save_data(data)
    flash(f"Added ₹{int(amount) if amount.is_integer() else amount} to your total.")
    return redirect(url_for("dashboard"))


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    data = load_data()
    if request.method == "POST":
        name = request.form.get("name", "").strip() or data["user"]["name"]
        code = request.form.get("referralCode", "").strip() or data["user"]["referralCode"]

        # Update user
        old_code = data["user"]["referralCode"]
        data["user"]["name"] = name
        data["user"]["referralCode"] = code

        # Reflect in leaderboard
        lb = data.get("leaderboard", [])
        found = False
        for x in lb:
            if x["referralCode"] == old_code:
                x["name"] = name
                x["referralCode"] = code
                found = True
                break
        if not found:
            lb.append({
                "name": name,
                "referralCode": code,
                "totalRaised": data["user"]["totalRaised"],
            })
        save_data(data)
        flash("Profile updated.")
        return redirect(url_for("dashboard"))
    return render_template("edit_profile.html", user=data["user"])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
