from contextlib import contextmanager
import os
import secrets
import sqlite3
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

DB_FILE = Path(__file__).with_name("concert.db")
CITIES = ("mumbai", "kolkata", "bangalore")
PRICES = {"a": 50000, "b": 30000, "c": 16000}
SEAT_RANGES = {"a": range(1, 51), "b": range(51, 101), "c": range(101, 151)}


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db():
    with get_db_connection() as conn:
        for city in CITIES:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {city} (
                    uid_no INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    gender TEXT NOT NULL,
                    block TEXT NOT NULL,
                    seat_no INTEGER NOT NULL UNIQUE
                )
                """
            )


init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/book", methods=["GET", "POST"])
def book():
    if request.method == "POST":
        city = (request.form.get("city") or "").lower()
        block = (request.form.get("block") or "").lower()
        name = (request.form.get("name") or "").strip()
        gender = (request.form.get("gender") or "").strip()

        try:
            uid = int(request.form.get("uid", ""))
            age = int(request.form.get("age", ""))
            seat = int(request.form.get("seat", ""))
        except ValueError:
            flash("UID, age, and seat number must be valid numbers.", "error")
            return redirect(url_for("book"))

        if city not in CITIES:
            flash("Invalid location selected.", "error")
            return redirect(url_for("book"))
        if not 100 <= uid <= 9_999_999_999:
            flash("UID must be a positive 3-10 digit number.", "error")
            return redirect(url_for("book"))
        if not name or not gender or age < 1:
            flash("Enter a name, a valid age, and a gender.", "error")
            return redirect(url_for("book"))
        if block not in SEAT_RANGES or seat not in SEAT_RANGES[block]:
            flash("Choose a seat number within the selected block's range.", "error")
            return redirect(url_for("book"))

        try:
            with get_db_connection() as conn:
                conn.execute(
                    f"INSERT INTO {city} "
                    "(uid_no, name, age, gender, block, seat_no) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (uid, name, age, gender, block, seat),
                )
        except sqlite3.IntegrityError:
            flash("That UID or seat number is already taken in this city.", "error")
            return redirect(url_for("book"))

        total_price = PRICES[block]
        flash(
            f"Congratulations! Ticket booked successfully for {name}. "
            f"Total Amount: ₹{total_price}",
            "success",
        )
        return redirect(url_for("index"))

    selected_city = (request.args.get("city") or "mumbai").lower()
    if selected_city not in CITIES:
        selected_city = "mumbai"
    return render_template("book.html", selected_city=selected_city)


@app.route("/download", methods=["GET", "POST"])
def download():
    ticket = None
    city_name = None
    selected_city = "mumbai"
    if request.method == "POST":
        city = (request.form.get("city") or "").lower()
        try:
            uid = int(request.form.get("uid", ""))
        except ValueError:
            flash("Enter a valid UID number.", "error")
            return redirect(url_for("download"))

        if city not in CITIES:
            flash("Invalid location selected.", "error")
            return redirect(url_for("download"))
        selected_city = city

        with get_db_connection() as conn:
            ticket = conn.execute(
                f"SELECT * FROM {city} WHERE uid_no = ?", (uid,)
            ).fetchone()

        if not ticket:
            flash("No ticket found matching the given UID and City.", "error")
        else:
            city_name = city.capitalize()

    return render_template(
        "download.html",
        ticket=ticket,
        city=city_name,
        selected_city=selected_city,
    )


@app.route("/admin", methods=["GET", "POST"])
def admin():
    records = []
    selected_city = None
    if request.method == "POST":
        selected_city = (request.form.get("city") or "").lower()
        if selected_city not in CITIES:
            flash("Invalid location selected.", "error")
            return redirect(url_for("admin"))

        with get_db_connection() as conn:
            records = conn.execute(
                f"SELECT * FROM {selected_city} ORDER BY seat_no"
            ).fetchall()

    return render_template(
        "admin.html",
        records=records,
        city=selected_city.capitalize() if selected_city else None,
        selected_city=selected_city,
    )


if __name__ == "__main__":
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.run(debug=True)