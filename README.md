## Anime Watchlist Manager

A Flask + MySQL web app to manage anime watchlists with reviews, genres, studios, and user profiles.

### Requirements
- Python 3.10+
- MySQL 8+

### Setup
1. Create a MySQL database and run `schema.sql`.
2. Create a `.env` file in the project root:
```
FLASK_SECRET_KEY=dev-change-me
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=anime_watchlist
MYSQL_USER=root
MYSQL_PASSWORD=your_password
FLASK_ENV=development
```
3. Create venv and install dependencies:
```
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```
4. Run the app:
```
python app.py
```

### Notes
- Tailwind via CDN for styling.
- Session-based authentication; passwords hashed with bcrypt.
- Update `.env` for your environment.



