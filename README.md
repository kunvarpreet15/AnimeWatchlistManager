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
- **Advanced Search with Filtering & Sorting**:
  - Search by anime title with up to 100 results
  - **Filter by Genre**: Case-insensitive genre matching
  - **Filter by Release Year**: Search anime from specific years (1960-2025)
  - **Filter by Minimum Score**: Filter by MAL mean score (1-10)
  - **Filter by Media Type**: TV, Movie, OVA, ONA, Special
  - **Include Genres**: Require anime to have ALL selected genres
  - **Exclude Genres**: Exclude anime that contain ANY selected genres
  - **8 Sorting Options**:
    - Score (high → low, low → high)
    - Title (A → Z, Z → A)
    - Popularity (high → low, low → high)
    - Release Date (newest first, oldest first)
  - All filtering done locally in Python after fetching from MAL API
  - Clear Filters button to reset all filters
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

### Search & Filtering Details
- **Local Filtering**: Since MAL API doesn't support server-side genre/year/score queries, all filtering is performed locally in Python after fetching results
- **Search Limit**: Up to 100 results fetched from MAL API, then filtered locally
- **Filter Persistence**: Filter selections are preserved in the form when viewing results
- **Real-time Results**: Results count is displayed showing how many anime match the current filters

### Notes
- Tailwind via CDN for styling.
- Session-based authentication; passwords hashed with bcrypt.
- Watchlist stores only MAL anime_id and user_id; all anime details are fetched dynamically from MAL API.
- Update `.env` for your environment.
- MAL API requires a Client ID (free to obtain from https://myanimelist.net/apiconfig).
- The `/browse` route redirects to `/search` since all content is from MAL API.
- Search filtering and sorting happen client-side (in the Flask app) after fetching data from MAL API, as the MAL API doesn't support advanced server-side filtering.



