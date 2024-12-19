import yt_dlp
import logging
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger('highlights')

class HighlightHandler:
    def __init__(self):
        self.ytdl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True
        }

    def extract_video_id(self, url):
        """Extract video ID from YouTube URL."""
        try:
            parsed = urlparse(url)
            if parsed.hostname == 'youtu.be':
                return parsed.path[1:]
            if parsed.hostname in ('www.youtube.com', 'youtube.com'):
                if parsed.path == '/watch':
                    return parse_qs(parsed.query)['v'][0]
                if parsed.path[:7] == '/embed/':
                    return parsed.path.split('/')[2]
                if parsed.path[:3] == '/v/':
                    return parsed.path.split('/')[2]
        except Exception as e:
            logger.error(f"Error extracting video ID: {e}")
        return None

    async def get_chapters(self, url):
        """Get video chapters if available."""
        try:
            with yt_dlp.YoutubeDL(self.ytdl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                chapters = info.get('chapters', [])
                
                if chapters:
                    logger.info(f"Found {len(chapters)} chapters")
                    for chapter in chapters:
                        logger.info(f"Chapter: {chapter.get('title')} at {chapter.get('start_time')}")
                
                return chapters
        except Exception as e:
            logger.error(f"Error getting chapters: {e}")
            return []

    def get_current_chapter(self, chapters, current_time):
        """Get current chapter based on time."""
        for chapter in chapters:
            start = chapter.get('start_time', 0)
            end = chapter.get('end_time', float('inf'))
            if start <= current_time < end:
                return chapter
        return None 