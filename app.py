import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import bcrypt
import mal_api

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
    """Home page with hero section, trending anime, and genre sections from MAL API."""
    # Hero section: Top-ranked anime
    hero_data = None
    try:
        top_ranked = mal_api.get_ranking(ranking_type="all", limit=1)
        if top_ranked:
            hero_data = mal_api.format_anime_for_display(top_ranked[0])
    except Exception as e:
        print(f"Error fetching hero section: {e}")
    
    # Trending section: Currently airing anime
    trending_items = []
    try:
        trending_raw = mal_api.get_trending(limit=10)
        for anime_data in trending_raw:
            formatted = mal_api.format_anime_for_display(anime_data)
            if formatted:
                trending_items.append(formatted)
    except Exception as e:
        print(f"Error fetching trending anime: {e}")
    
    # Genre sections: Popular genres
    genre_sections = {}
    popular_genres = ["action", "comedy", "drama", "fantasy"]  # Top 4 popular genres
    
    for genre_name in popular_genres:
        genre_id = mal_api.get_genre_id(genre_name)
        if genre_id:
            try:
                genre_anime_raw = mal_api.get_anime_by_genre(genre_id, limit=10)
                genre_items = []
                for anime_data in genre_anime_raw:
                    formatted = mal_api.format_anime_for_display(anime_data)
                    if formatted:
                        genre_items.append(formatted)
                if genre_items:
                    genre_sections[genre_name.capitalize()] = genre_items
            except Exception as e:
                print(f"Error fetching genre {genre_name}: {e}")
                genre_sections[genre_name.capitalize()] = []
    
    return render_template(
        "home.html",
        spotlight=hero_data,
        trending=trending_items,
        genre_sections=genre_sections,
    )


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
    """Redirect to search page - all anime content is now from MAL API."""
    # Redirect to search page with query if provided, otherwise just search page
    q = request.args.get("q", "").strip()
    if q:
        return redirect(url_for("search", q=q))
    return redirect(url_for("search"))


@app.route("/search")
def search():
    """Search anime using MAL API."""
    query = request.args.get("q", "").strip()
    if not query:
        return render_template("search.html", results=[], query="")
    
    # Search MAL API (limit=12 as specified)
    mal_results = mal_api.search_anime(query, limit=12)
    
    # Format results for display
    results = []
    for anime_data in mal_results:
        formatted = mal_api.format_anime_for_display(anime_data)
        if formatted:
            results.append(formatted)
    
    return render_template("search.html", results=results, query=query)


@app.route("/anime/<int:anime_id>")
def anime_detail(anime_id: int):
    """Display anime details from MAL API."""
    # Fetch anime details from MAL API
    anime_data = mal_api.get_anime_details(anime_id)
    if not anime_data:
        flash("Anime not found or error fetching data from MAL.", "danger")
        return redirect(url_for("search"))
    
    # Format anime data for display
    anime = mal_api.format_anime_for_display(anime_data)
    if not anime:
        flash("Error formatting anime data.", "danger")
        return redirect(url_for("search"))
    
    # Fetch MAL reviews
    mal_reviews = mal_api.get_top_reviews(anime_id, limit=3)
    
    # Get user's watchlist entry if logged in
    user_watch = None
    local_reviews = []
    if "user_id" in session:
        try:
            with get_db() as conn:
                with conn.cursor(dictionary=True) as cur:
                    cur.execute(
                        "SELECT * FROM WATCHLIST WHERE user_id=%s AND anime_id=%s",
                        (session["user_id"], anime_id),
                    )
                    user_watch = cur.fetchone()
                    # Try to fetch local reviews (if REVIEW table uses MAL anime_id)
                    try:
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
                        local_reviews = cur.fetchall()
                    except Error:
                        # REVIEW table might not support MAL anime_id, ignore
                        pass
        except Error:
            pass  # Ignore DB errors
    
    return render_template(
        "anime_detail.html",
        anime=anime,
        genres=anime.get("genres", []),
        studios=anime.get("studios", []),
        mal_reviews=mal_reviews,
        reviews=local_reviews,
        user_watch=user_watch,
        statuses=sorted(ALLOWED_STATUSES),
    )


@app.route("/watchlist", methods=["GET"]) 
@login_required
def watchlist():
    """Display user's watchlist with anime details fetched from MAL API."""
    try:
        with get_db() as conn:
            with conn.cursor(dictionary=True) as cur:
                # Get watchlist entries (only anime_id and user data)
                cur.execute(
                    """
                    SELECT w.watchlist_id, w.anime_id, w.status, w.episodes_watched, w.last_updated
                    FROM WATCHLIST w
                    WHERE w.user_id=%s
                    ORDER BY w.last_updated DESC
                    """,
                    (session["user_id"],),
                )
                watchlist_entries = cur.fetchall()
        
        # Fetch anime details from MAL API for each entry
        items = []
        for entry in watchlist_entries:
            anime_id = entry["anime_id"]
            anime_data = mal_api.get_anime_details(anime_id)
            
            if anime_data:
                formatted = mal_api.format_anime_for_display(anime_data)
                if formatted:
                    # Merge watchlist entry data with anime data
                    item = {
                        "watchlist_id": entry["watchlist_id"],
                        "anime_id": anime_id,
                        "status": entry["status"],
                        "episodes_watched": entry["episodes_watched"],
                        "last_updated": entry["last_updated"],
                        "title": formatted.get("title", "Unknown"),
                        "poster_url": formatted.get("poster_url", ""),
                        "num_episodes": formatted.get("num_episodes"),
                        "year": formatted.get("year"),
                        "mean": formatted.get("mean"),
                        "rank": formatted.get("rank"),
                    }
                    items.append(item)
            else:
                # If MAL API fails, still show the entry with minimal info
                item = {
                    "watchlist_id": entry["watchlist_id"],
                    "anime_id": anime_id,
                    "status": entry["status"],
                    "episodes_watched": entry["episodes_watched"],
                    "last_updated": entry["last_updated"],
                    "title": f"Anime ID: {anime_id}",
                    "poster_url": "",
                    "num_episodes": None,
                    "year": None,
                    "mean": None,
                    "rank": None,
                }
                items.append(item)
        
        return render_template("watchlist.html", items=items, statuses=sorted(ALLOWED_STATUSES))
    except Error as e:
        print(f"Watchlist DB error: {e}")
        return render_template("watchlist.html", items=[], statuses=sorted(ALLOWED_STATUSES))


@app.route("/watchlist/add", methods=["POST"]) 
@login_required
def watchlist_add():
    """Add anime to watchlist using MAL anime_id."""
    anime_id = request.form.get("anime_id")
    status = request.form.get("status", "").strip().lower()
    episodes = request.form.get("episodes_watched", "0").strip()

    if not anime_id or status not in ALLOWED_STATUSES:
        flash("Invalid input.", "danger")
        return redirect(request.referrer or url_for("search"))
    
    try:
        anime_id_int = int(anime_id)
    except ValueError:
        flash("Invalid anime ID.", "danger")
        return redirect(request.referrer or url_for("search"))
    
    # Verify anime exists in MAL API
    anime_data = mal_api.get_anime_details(anime_id_int)
    if not anime_data:
        flash("Anime not found in MAL.", "danger")
        return redirect(request.referrer or url_for("search"))
    
    try:
        episodes_val = max(0, int(episodes or 0))
    except ValueError:
        episodes_val = 0

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM WATCHLIST WHERE user_id=%s AND anime_id=%s",
                    (session["user_id"], anime_id_int),
                )
                exists = cur.fetchone()
                if exists:
                    cur.execute(
                        """
                        UPDATE WATCHLIST
                        SET status=%s, episodes_watched=%s
                        WHERE user_id=%s AND anime_id=%s
                        """,
                        (status, episodes_val, session["user_id"], anime_id_int),
                    )
                else:
                    cur.execute(
                        "INSERT INTO WATCHLIST (user_id, anime_id, status, episodes_watched) VALUES (%s, %s, %s, %s)",
                        (session["user_id"], anime_id_int, status, episodes_val),
                    )
                conn.commit()
        flash("Watchlist updated.", "success")
    except Error as e:
        print(f"Watchlist add error: {e}")
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
                # Get watchlist entries (using MAL anime_id)
                cur.execute(
                    """
                    SELECT w.status, w.episodes_watched, w.anime_id, w.last_updated
                    FROM WATCHLIST w
                    WHERE w.user_id=%s
                    ORDER BY w.last_updated DESC
                    """,
                    (user["user_id"],),
                )
                watchlist_entries = cur.fetchall()
                
                # Fetch anime details from MAL API for each watchlist entry
                watchlist_items = []
                for entry in watchlist_entries:
                    anime_id = entry["anime_id"]
                    anime_data = mal_api.get_anime_details(anime_id)
                    if anime_data:
                        formatted = mal_api.format_anime_for_display(anime_data)
                        if formatted:
                            item = {
                                "status": entry["status"],
                                "episodes_watched": entry["episodes_watched"],
                                "anime_id": anime_id,
                                "title": formatted.get("title", "Unknown"),
                                "num_episodes": formatted.get("num_episodes"),
                                "poster_url": formatted.get("poster_url", ""),
                            }
                            watchlist_items.append(item)
                
                # Get reviews (using MAL anime_id)
                cur.execute(
                    """
                    SELECT r.rating, r.review_text, r.review_date, r.anime_id
                    FROM REVIEW r
                    WHERE r.user_id=%s
                    ORDER BY r.review_date DESC
                    """,
                    (user["user_id"],),
                )
                review_entries = cur.fetchall()
                
                # Fetch anime details from MAL API for each review
                reviews = []
                for entry in review_entries:
                    anime_id = entry["anime_id"]
                    anime_data = mal_api.get_anime_details(anime_id)
                    if anime_data:
                        formatted = mal_api.format_anime_for_display(anime_data)
                        if formatted:
                            review = {
                                "rating": entry["rating"],
                                "review_text": entry["review_text"],
                                "review_date": entry["review_date"],
                                "anime_id": anime_id,
                                "title": formatted.get("title", "Unknown"),
                            }
                            reviews.append(review)
        
        return render_template("profile.html", user=user, watchlist_items=watchlist_items, reviews=reviews)
    except Error as e:
        print(f"Profile error: {e}")
        abort(500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_ENV") == "development")

