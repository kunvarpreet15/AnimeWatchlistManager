"""
MyAnimeList (MAL) API integration helper functions.
"""
import os
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv
import time

load_dotenv()

# MAL API Configuration
MAL_CLIENT_ID = os.getenv("MAL_CLIENT_ID")
MAL_API_BASE = "https://api.myanimelist.net/v2"
MAL_HEADERS = {"X-MAL-CLIENT-ID": MAL_CLIENT_ID} if MAL_CLIENT_ID else {}

# Simple in-memory cache with TTL (Time To Live)
_cache = {}
_cache_ttl = 300  # 5 minutes cache TTL

# MAL Genre ID mapping (common genres)
# Reference: https://myanimelist.net/anime/genre
GENRE_IDS = {
    "action": 1,
    "adventure": 2,
    "comedy": 4,
    "drama": 8,
    "fantasy": 10,
    "horror": 14,
    "romance": 22,
    "sci-fi": 24,
    "slice of life": 36,
    "sports": 30,
    "supernatural": 37,
    "mystery": 7,
    "psychological": 40,
    "thriller": 41,
    "music": 19,
    "ecchi": 9,
    "mecha": 18,
}


def _get_from_cache(key: str):
    """Get item from cache if it exists and hasn't expired."""
    if key in _cache:
        data, timestamp = _cache[key]
        if time.time() - timestamp < _cache_ttl:
            return data
        else:
            del _cache[key]
    return None


def _set_cache(key: str, value):
    """Store item in cache with current timestamp. Value can be Dict or List."""
    _cache[key] = (value, time.time())


def get_ranking(ranking_type: str = "all", limit: int = 5) -> List[Dict]:
    """
    Get top-ranked anime from MAL API.
    
    Args:
        ranking_type: Type of ranking ("all", "airing", "upcoming", "tv", "ova", "movie", "special", "bypopularity", "favorite")
        limit: Maximum number of results (default: 5)
    
    Returns:
        List of anime dictionaries
    """
    if not MAL_CLIENT_ID:
        return []
    
    cache_key = f"ranking:{ranking_type}:{limit}"
    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached
    
    try:
        url = f"{MAL_API_BASE}/anime/ranking"
        params = {
            "ranking_type": ranking_type,
            "limit": limit,
            "fields": "id,title,main_picture,mean,genres,synopsis"
        }
        response = requests.get(url, headers=MAL_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("data", []):
            anime = item.get("node", {})
            results.append(anime)
        
        _set_cache(cache_key, results)
        return results
    except requests.exceptions.RequestException as e:
        print(f"MAL API ranking error: {e}")
        return []


def get_trending(limit: int = 10) -> List[Dict]:
    """
    Get currently airing (trending) anime from MAL API.
    
    Args:
        limit: Maximum number of results (default: 10)
    
    Returns:
        List of anime dictionaries
    """
    return get_ranking(ranking_type="airing", limit=limit)


def get_anime_by_genre(genre_id: int, limit: int = 10) -> List[Dict]:
    """
    Get anime filtered by genre.
    MAL API doesn't support direct ?genres= filter, so fetch top popular anime
    and filter them locally based on their genre list.
    """
    if not MAL_CLIENT_ID:
        return []

    cache_key = f"genre_filtered:{genre_id}:{limit}"
    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached

    try:
        # Get a larger list of popular anime (limit 100)
        url = f"{MAL_API_BASE}/anime/ranking"
        params = {
            "ranking_type": "bypopularity",
            "limit": 100,
            "fields": "id,title,main_picture,mean,genres,synopsis"
        }

        response = requests.get(url, headers=MAL_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        all_anime = [item.get("node", {}) for item in data.get("data", [])]

        # Filter anime by genre_id locally
        filtered = [
            anime for anime in all_anime
            if any(g.get("id") == genre_id for g in anime.get("genres", []))
        ][:limit]

        _set_cache(cache_key, filtered)
        return filtered
    except requests.exceptions.RequestException as e:
        print(f"MAL API genre filter error for genre {genre_id}: {e}")
        return []


def get_genre_id(genre_name: str) -> Optional[int]:
    """
    Get MAL genre ID from genre name.
    
    Args:
        genre_name: Genre name (case-insensitive)
    
    Returns:
        Genre ID or None if not found
    """
    return GENRE_IDS.get(genre_name.lower())


def search_anime(query: str, limit: int = 12) -> List[Dict]:
    """
    Search for anime using MAL API.
    
    Args:
        query: Search query string
        limit: Maximum number of results (default: 12)
    
    Returns:
        List of anime dictionaries with basic info
    """
    if not MAL_CLIENT_ID:
        return []
    
    cache_key = f"search:{query}:{limit}"
    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached
    
    try:
        url = f"{MAL_API_BASE}/anime"
        params = {
            "q": query,
            "limit": limit,
            "fields": "id,title,main_picture,synopsis,mean,genres,start_date,popularity,media_type"
        }
        response = requests.get(url, headers=MAL_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("data", []):
            anime = item.get("node", {})
            results.append(anime)
        
        _set_cache(cache_key, results)
        return results
    except requests.exceptions.RequestException as e:
        print(f"MAL API search error: {e}")
        return []


def get_anime_details(anime_id: int) -> Optional[Dict]:
    """
    Get detailed anime information from MAL API.
    
    Args:
        anime_id: MAL anime ID
    
    Returns:
        Dictionary with anime details or None if error
    """
    if not MAL_CLIENT_ID:
        return None
    
    cache_key = f"anime:{anime_id}"
    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached
    
    try:
        url = f"{MAL_API_BASE}/anime/{anime_id}"
        params = {
            "fields": "id,title,main_picture,alternative_titles,start_date,end_date,synopsis,mean,rank,popularity,num_episodes,genres,studios,status,average_episode_duration,rating"
        }
        response = requests.get(url, headers=MAL_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        anime = response.json()
        
        _set_cache(cache_key, anime)
        return anime
    except requests.exceptions.RequestException as e:
        print(f"MAL API details error for anime {anime_id}: {e}")
        return None


def get_top_reviews(anime_id: int, limit: int = 3) -> List[Dict]:
    """
    Get top reviews for an anime from MAL API.
    
    Args:
        anime_id: MAL anime ID
        limit: Maximum number of reviews (default: 3)
    
    Returns:
        List of review dictionaries
    """
    if not MAL_CLIENT_ID:
        return []
    
    cache_key = f"reviews:{anime_id}:{limit}"
    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached
    
    try:
        url = f"{MAL_API_BASE}/anime/{anime_id}/reviews"
        params = {"limit": limit, "sort": "helpful"}
        response = requests.get(url, headers=MAL_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        reviews = []
        for item in data.get("data", []):
            review_node = item.get("node", {})
            # Extract relevant review information
            review = {
                "reviewer": review_node.get("user", {}).get("name", "Anonymous"),
                "rating": review_node.get("rating", "N/A"),
                "review": review_node.get("review", ""),
                "helpful_count": review_node.get("helpful_count", 0),
                "date": review_node.get("date", ""),
            }
            reviews.append(review)
        
        _set_cache(cache_key, reviews)
        return reviews
    except requests.exceptions.RequestException as e:
        # Reviews endpoint might not be available, fail gracefully
        print(f"MAL API reviews error for anime {anime_id}: {e}")
        return []


def format_anime_for_display(anime_data: Dict) -> Optional[Dict]:
    """
    Format MAL API anime data for template display.
    
    Args:
        anime_data: Raw anime data from MAL API
    
    Returns:
        Formatted dictionary with standardized field names, or None if invalid
    """
    if not anime_data or not isinstance(anime_data, dict):
        return None
    
    main_picture = anime_data.get("main_picture", {})
    picture_url = main_picture.get("medium") or main_picture.get("large") or ""
    
    # Extract year from start_date (format: YYYY-MM-DD or YYYY)
    start_date = anime_data.get("start_date", "")
    year = None
    if start_date:
        year = start_date.split("-")[0] if "-" in start_date else start_date
        try:
            year = int(year)
        except ValueError:
            year = None
    
    # Format genres
    genres = [g.get("name", "") for g in anime_data.get("genres", [])]
    
    # Format studios
    studios = [s.get("name", "") for s in anime_data.get("studios", [])]
    
    # Get alternative titles
    alt_titles = anime_data.get("alternative_titles", {})
    english_title = alt_titles.get("en", "")
    synonyms = alt_titles.get("synonyms", [])
    
    # Format synopsis (truncate if too long)
    synopsis = anime_data.get("synopsis", "")
    if synopsis and len(synopsis) > 500:
        synopsis = synopsis[:497] + "..."
    
    # Ensure mean is a float
    mean = anime_data.get("mean")
    if mean is not None:
        try:
            mean = float(mean)
        except (ValueError, TypeError):
            mean = None
    
    # Get media_type (media_type field from MAL API)
    media_type = anime_data.get("media_type", "")
    
    return {
        "id": anime_data.get("id"),
        "title": anime_data.get("title", "Unknown"),
        "english_title": english_title,
        "synonyms": synonyms,
        "poster_url": picture_url,
        "synopsis": synopsis,
        "full_synopsis": anime_data.get("synopsis", ""),
        "year": year,
        "start_date": start_date,
        "end_date": anime_data.get("end_date", ""),
        "num_episodes": anime_data.get("num_episodes"),
        "mean": mean,
        "rank": anime_data.get("rank"),
        "popularity": anime_data.get("popularity"),
        "genres": genres,
        "studios": studios,
        "status": anime_data.get("status", "").lower(),
        "rating": anime_data.get("rating", ""),
        "average_episode_duration": anime_data.get("average_episode_duration"),
        "media_type": media_type,
    }

