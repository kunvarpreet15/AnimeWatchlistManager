import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import bcrypt

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-change-me")

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "database": os.getenv("MYSQL_DATABASE", "anime_watchlist"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
}

ALLOWED_STATUSES = {"watching", "completed", "planned", "dropped"}


def get_db():
    return mysql.connector.connect(**MYSQL_CONFIG)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_user():
    return {"current_user": session.get("username")}


@app.route("/")
def home():
    try:
        with get_db() as conn:
            with conn.cursor(dictionary=True) as cur:
                # Spotlight: latest by release_year
                cur.execute(
                    """
                    SELECT * FROM ANIME
                    ORDER BY release_year DESC, anime_id DESC
                    LIMIT 1
                    """
                )
                spotlight = cur.fetchone()

                # Trending: top 10 by recent release year
                cur.execute(
                    """
                    SELECT a.anime_id, a.title, a.poster_url, a.type, a.release_year
                    FROM ANIME a
                    ORDER BY a.release_year DESC, a.anime_id DESC
                    LIMIT 10
                    """
                )
                trending = cur.fetchall()

                # Top 4 genres by count
                cur.execute(
                    """
                    SELECT g.genre_name, COUNT(*) AS cnt
                    FROM ANIME_GENRE ag
                    JOIN GENRE g ON g.genre_id = ag.genre_id
                    GROUP BY g.genre_id, g.genre_name
                    ORDER BY cnt DESC, g.genre_name ASC
                    LIMIT 4
                    """
                )
                top_genres = [row["genre_name"] for row in cur.fetchall()]

                genre_sections = {}
                for gname in top_genres:
                    cur.execute(
                        """
                        SELECT a.anime_id, a.title, a.poster_url
                        FROM ANIME a
                        JOIN ANIME_GENRE ag ON a.anime_id = ag.anime_id
                        JOIN GENRE g ON g.genre_id = ag.genre_id
                        WHERE g.genre_name = %s
                        ORDER BY a.release_year DESC, a.anime_id DESC
                        LIMIT 10
                        """,
                        (gname,),
                    )
                    genre_sections[gname] = cur.fetchall()

        return render_template(
            "home.html",
            spotlight=spotlight,
            trending=trending,
            genre_sections=genre_sections,
        )
    except Error:
        return render_template("home.html", spotlight=None, trending=[], genre_sections={})


@app.route("/register", methods=["GET", "POST"]) 
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))
        if len(username) > 50 or len(email) > 100:
            flash("Username or email too long.", "danger")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        try:
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO USERS (username, email, password_hash) VALUES (%s, %s, %s)",
                        (username, email, password_hash),
                    )
                    conn.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        except Error as e:
            msg = str(e)
            if "Duplicate" in msg or "duplicate" in msg:
                flash("Username or email already exists.", "danger")
            else:
                flash("Registration failed.", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"]) 
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Enter username and password.", "danger")
            return redirect(url_for("login"))
        try:
            with get_db() as conn:
                with conn.cursor(dictionary=True) as cur:
                    cur.execute("SELECT * FROM USERS WHERE username=%s", (username,))
                    user = cur.fetchone()
            if not user:
                flash("Invalid credentials.", "danger")
                return redirect(url_for("login"))
            if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
                flash("Invalid credentials.", "danger")
                return redirect(url_for("login"))
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            flash("Logged in successfully.", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("home"))
        except Error:
            flash("Login error.", "danger")
            return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout", methods=["POST"]) 
@login_required
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("home"))


@app.route("/browse")
def browse():
    q = request.args.get("q", "").strip()
    try:
        with get_db() as conn:
            with conn.cursor(dictionary=True) as cur:
                if q:
                    query = (
                        """
                        SELECT DISTINCT a.anime_id, a.title, a.poster_url, a.type, a.release_year
                        FROM ANIME a
                        LEFT JOIN ANIME_GENRE ag ON ag.anime_id = a.anime_id
                        LEFT JOIN GENRE g ON g.genre_id = ag.genre_id
                        LEFT JOIN ANIME_STUDIO ast ON ast.anime_id = a.anime_id
                        LEFT JOIN STUDIO s ON s.studio_id = ast.studio_id
                        WHERE a.title LIKE %s OR g.genre_name LIKE %s OR s.studio_name LIKE %s
                        ORDER BY a.title ASC
                        """
                    )
                    like = f"%{q}%"
                    cur.execute(query, (like, like, like))
                else:
                    cur.execute(
                        "SELECT a.anime_id, a.title, a.poster_url, a.type, a.release_year FROM ANIME a ORDER BY a.title ASC"
                    )
                items = cur.fetchall()
        return render_template("browse.html", items=items, q=q)
    except Error as e:
        print("DB ERROR:", e)
        return render_template("browse.html", items=[], q=q)


@app.route("/anime/<int:anime_id>")
def anime_detail(anime_id: int):
    try:
        with get_db() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT * FROM ANIME WHERE anime_id=%s", (anime_id,))
                anime = cur.fetchone()
                if not anime:
                    abort(404)
                cur.execute(
                    """
                    SELECT g.genre_name FROM ANIME_GENRE ag
                    JOIN GENRE g ON g.genre_id = ag.genre_id
                    WHERE ag.anime_id=%s
                    ORDER BY g.genre_name
                    """,
                    (anime_id,),
                )
                genres = [row["genre_name"] for row in cur.fetchall()]
                cur.execute(
                    """
                    SELECT s.studio_name FROM ANIME_STUDIO ast
                    JOIN STUDIO s ON s.studio_id = ast.studio_id
                    WHERE ast.anime_id=%s
                    ORDER BY s.studio_name
                    """,
                    (anime_id,),
                )
                studios = [row["studio_name"] for row in cur.fetchall()]
                cur.execute(
                    """
                    SELECT r.review_id, r.rating, r.review_text, r.review_date, u.username
                    FROM REVIEW r
                    JOIN USERS u ON u.user_id = r.user_id
                    WHERE r.anime_id=%s
                    ORDER BY r.review_date DESC
                    """,
                    (anime_id,),
                )
                reviews = cur.fetchall()

                user_watch = None
                if "user_id" in session:
                    cur.execute(
                        "SELECT * FROM WATCHLIST WHERE user_id=%s AND anime_id=%s",
                        (session["user_id"], anime_id),
                    )
                    user_watch = cur.fetchone()

        return render_template(
            "anime_detail.html",
            anime=anime,
            genres=genres,
            studios=studios,
            reviews=reviews,
            user_watch=user_watch,
            statuses=sorted(ALLOWED_STATUSES),
        )
    except Error:
        abort(500)


@app.route("/watchlist", methods=["GET"]) 
@login_required
def watchlist():
    try:
        with get_db() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """
                    SELECT w.watchlist_id, w.status, w.episodes_watched, w.last_updated,
                           a.anime_id, a.title, a.total_episodes, a.poster_url, a.type, a.release_year
                    FROM WATCHLIST w
                    JOIN ANIME a ON a.anime_id = w.anime_id
                    WHERE w.user_id=%s
                    ORDER BY w.last_updated DESC
                    """,
                    (session["user_id"],),
                )
                items = cur.fetchall()
        return render_template("watchlist.html", items=items, statuses=sorted(ALLOWED_STATUSES))
    except Error:
        return render_template("watchlist.html", items=[], statuses=sorted(ALLOWED_STATUSES))


@app.route("/watchlist/add", methods=["POST"]) 
@login_required
def watchlist_add():
    anime_id = request.form.get("anime_id")
    status = request.form.get("status", "").strip().lower()
    episodes = request.form.get("episodes_watched", "0").strip()

    if not anime_id or status not in ALLOWED_STATUSES:
        flash("Invalid input.", "danger")
        return redirect(request.referrer or url_for("browse"))
    try:
        episodes_val = max(0, int(episodes or 0))
    except ValueError:
        episodes_val = 0

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM WATCHLIST WHERE user_id=%s AND anime_id=%s",
                    (session["user_id"], anime_id),
                )
                exists = cur.fetchone()
                if exists:
                    cur.execute(
                        """
                        UPDATE WATCHLIST
                        SET status=%s, episodes_watched=%s
                        WHERE user_id=%s AND anime_id=%s
                        """,
                        (status, episodes_val, session["user_id"], anime_id),
                    )
                else:
                    cur.execute(
                        "INSERT INTO WATCHLIST (user_id, anime_id, status, episodes_watched) VALUES (%s, %s, %s, %s)",
                        (session["user_id"], anime_id, status, episodes_val),
                    )
                conn.commit()
        flash("Watchlist updated.", "success")
    except Error:
        flash("Failed to update watchlist.", "danger")
    return redirect(request.referrer or url_for("watchlist"))


@app.route("/watchlist/update/<int:watchlist_id>", methods=["POST"]) 
@login_required
def watchlist_update(watchlist_id: int):
    status = request.form.get("status", "").strip().lower()
    episodes = request.form.get("episodes_watched", "0").strip()
    if status not in ALLOWED_STATUSES:
        flash("Invalid status.", "danger")
        return redirect(url_for("watchlist"))
    try:
        episodes_val = max(0, int(episodes or 0))
    except ValueError:
        episodes_val = 0
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE WATCHLIST SET status=%s, episodes_watched=%s WHERE watchlist_id=%s AND user_id=%s",
                    (status, episodes_val, watchlist_id, session["user_id"]),
                )
                conn.commit()
        flash("Watchlist entry updated.", "success")
    except Error:
        flash("Failed to update entry.", "danger")
    return redirect(url_for("watchlist"))


@app.route("/watchlist/delete/<int:watchlist_id>", methods=["POST"]) 
@login_required
def watchlist_delete(watchlist_id: int):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM WATCHLIST WHERE watchlist_id=%s AND user_id=%s",
                    (watchlist_id, session["user_id"]),
                )
                conn.commit()
        flash("Watchlist entry removed.", "info")
    except Error:
        flash("Failed to remove entry.", "danger")
    return redirect(url_for("watchlist"))


@app.route("/review/add/<int:anime_id>", methods=["POST"]) 
@login_required
def review_add(anime_id: int):
    rating = request.form.get("rating", "").strip()
    text = request.form.get("review_text", "").strip()
    try:
        rating_val = int(rating)
    except ValueError:
        rating_val = 0
    if rating_val < 1 or rating_val > 10:
        flash("Rating must be between 1 and 10.", "danger")
        return redirect(url_for("anime_detail", anime_id=anime_id))
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Upsert-like behavior: if a review by this user exists, update; else insert
                cur.execute(
                    "SELECT review_id FROM REVIEW WHERE user_id=%s AND anime_id=%s",
                    (session["user_id"], anime_id),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        "UPDATE REVIEW SET rating=%s, review_text=%s, review_date=%s WHERE review_id=%s",
                        (rating_val, text, datetime.utcnow(), existing[0]),
                    )
                else:
                    cur.execute(
                        "INSERT INTO REVIEW (user_id, anime_id, rating, review_text) VALUES (%s, %s, %s, %s)",
                        (session["user_id"], anime_id, rating_val, text),
                    )
                conn.commit()
        flash("Review saved.", "success")
    except Error:
        flash("Failed to save review.", "danger")
    return redirect(url_for("anime_detail", anime_id=anime_id))


@app.route("/review/delete/<int:review_id>", methods=["POST"]) 
@login_required
def review_delete(review_id: int):
    try:
        with get_db() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT anime_id FROM REVIEW WHERE review_id=%s AND user_id=%s", (review_id, session["user_id"]))
                row = cur.fetchone()
                if not row:
                    abort(403)
                anime_id = row["anime_id"]
            with conn.cursor() as cur2:
                cur2.execute("DELETE FROM REVIEW WHERE review_id=%s AND user_id=%s", (review_id, session["user_id"]))
                conn.commit()
        flash("Review deleted.", "info")
        return redirect(url_for("anime_detail", anime_id=anime_id))
    except Error:
        flash("Failed to delete review.", "danger")
        return redirect(request.referrer or url_for("home"))


@app.route("/profile/<username>")
@login_required
def profile(username: str):
    try:
        with get_db() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT user_id, username, email, created_at FROM USERS WHERE username=%s", (username,))
                user = cur.fetchone()
                if not user:
                    abort(404)
                cur.execute(
                    """
                    SELECT w.status, w.episodes_watched, a.title, a.anime_id, a.total_episodes, a.poster_url
                    FROM WATCHLIST w
                    JOIN ANIME a ON a.anime_id = w.anime_id
                    WHERE w.user_id=%s
                    ORDER BY w.last_updated DESC
                    """,
                    (user["user_id"],),
                )
                watchlist_items = cur.fetchall()
                cur.execute(
                    """
                    SELECT r.rating, r.review_text, r.review_date, a.title, a.anime_id
                    FROM REVIEW r
                    JOIN ANIME a ON a.anime_id = r.anime_id
                    WHERE r.user_id=%s
                    ORDER BY r.review_date DESC
                    """,
                    (user["user_id"],),
                )
                reviews = cur.fetchall()
        return render_template("profile.html", user=user, watchlist_items=watchlist_items, reviews=reviews)
    except Error:
        abort(500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_ENV") == "development")

