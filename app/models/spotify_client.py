import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class SpotifyClient:
    """Handles Spotify API interactions."""
    def __init__(self):
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.spotify = None
        if not self._initialize():
            logger.error("Failed to initialize Spotify client")

    def _initialize(self):
        """Initialize the Spotify client."""
        if not self.client_id or not self.client_secret:
            logger.error("Missing Spotify credentials")
            return False
            
        try:
            credentials_manager = SpotifyClientCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            self.spotify = spotipy.Spotify(client_credentials_manager=credentials_manager)
            # Test the connection
            self.spotify.user('spotify')  # Simple API call to verify connection
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Spotify client: {e}")
            self.spotify = None
            return False

    def check_connection(self):
        """Check if Spotify client is properly initialized."""
        try:
            if self.spotify:
                self.spotify.user('spotify')  # Test the connection
                return True
            return False
        except:
            return False

    def is_spotify_url(self, url: str) -> bool:
        """Check if the URL is a Spotify URL."""
        try:
            parsed = urlparse(url)
            return parsed.hostname in ['open.spotify.com', 'play.spotify.com']
        except:
            return False

    def get_track_info(self, url: str) -> dict:
        """Get info for a single track."""
        track = self.spotify.track(url)
        return {
            'title': track['name'],
            'artist': track['artists'][0]['name'],
            'duration': track['duration_ms'] / 1000,
            'thumbnail': track['album']['images'][0]['url'] if track['album']['images'] else None
        }

    def get_playlist_tracks(self, url: str) -> tuple:
        """Get all tracks from a Spotify playlist."""
        playlist = self.spotify.playlist(url)
        tracks = []
        
        playlist_info = {
            'name': playlist['name'],
            'owner': playlist['owner']['display_name'],
            'total_tracks': playlist['tracks']['total']
        }
        
        results = playlist['tracks']
        while results:
            for item in results['items']:
                track = item['track']
                if track:
                    tracks.append({
                        'title': track['name'],
                        'artist': track['artists'][0]['name'],
                        'duration': track['duration_ms'] / 1000,
                        'thumbnail': track['album']['images'][0]['url'] if track['album']['images'] else None
                    })
            
            if results['next']:
                results = self.spotify.next(results)
            else:
                break
                
        return tracks, playlist_info

    def get_album_tracks(self, url: str) -> list:
        results = self.spotify.album_tracks(url)
        tracks = []
        
        while results:
            for track in results['items']:
                tracks.append({
                    'title': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'] if 'album' in track else None
                })
            
            if results['next']:
                results = self.spotify.next(results)
            else:
                break
                
        return tracks

    # ... (rest of Spotify methods) 