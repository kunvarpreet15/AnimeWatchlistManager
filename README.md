## Anime Watchlist Manager

A Flask + MySQL web app to manage anime watchlists with **full MyAnimeList (MAL) API integration**. All anime content is fetched dynamically from MAL API - no local anime database needed.

### Requirements
- Python 3.10+
- MySQL 8+ (only for user data and watchlist - no anime data stored)
- MyAnimeList API Client ID

### Setup
1. Create a MySQL database and run `schema.sql` (only creates USER, WATCHLIST, and REVIEW tables).
2. Get a MyAnimeList API Client ID:
   - Visit https://myanimelist.net/apiconfig
   - Create a new app and copy your Client ID
3. Create a `.env` file in the project root:
```
FLASK_SECRET_KEY=dev-change-me
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=anime_watchlist
MYSQL_USER=root
MYSQL_PASSWORD=your_password
FLASK_ENV=development
MAL_CLIENT_ID=your-mal-client-id-here
```
4. Create venv and install dependencies:
```
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```
5. Run the app:
```
python app.py
```

### Features
- **Full MAL API Integration**: All anime content (home page, search, details) fetched from MAL API
- **Dynamic Home Page**: 
  - Hero section with top-ranked anime
  - Trending section with currently airing anime
  - Genre-based sections (Action, Comedy, Drama, Fantasy)
- **Dynamic Watchlist**: Anime details are fetched live from MAL API, keeping data up-to-date
- **Caching**: API responses are cached for 5 minutes to reduce API calls
- **User Reviews**: Both MAL reviews (top 3) and local user reviews are displayed
- **Watchlist Management**: Track anime status (watching, completed, planned, dropped) and episodes watched
- **Error Handling**: Graceful fallback messages when MAL API is unavailable

### Architecture
- **No Local Anime Database**: The MySQL database only stores:
  - User accounts (USERS table)
  - Watchlist entries (WATCHLIST table - only `user_id` and `anime_id`)
  - User reviews (REVIEW table - references MAL `anime_id`)
- **All Anime Data from MAL**: Titles, posters, synopsis, ratings, genres, studios, etc. are fetched live from MAL API
- **Caching Layer**: Simple in-memory cache with 5-minute TTL to optimize API usage

### Notes
- Tailwind via CDN for styling.
- Session-based authentication; passwords hashed with bcrypt.
- Watchlist stores only MAL anime_id and user_id; all anime details are fetched dynamically from MAL API.
- Update `.env` for your environment.
- MAL API requires a Client ID (free to obtain from https://myanimelist.net/apiconfig).
- The `/browse` route redirects to `/search` since all content is from MAL API.



