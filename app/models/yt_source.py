import discord
import yt_dlp
import asyncio
import time
from async_timeout import timeout
import logging
from utils.highlights import HighlightHandler
from utils.sponsorblock import SponsorBlockHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('YTDLSource')

# Define FFMPEG_OPTIONS globally
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -loglevel error'
}

class YTDLSource(discord.PCMVolumeTransformer):
    """Enhanced YouTube downloader with error handling and metadata."""
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'extract_flat': False,
        'force_generic_extractor': False
    }

    @classmethod
    async def create_source(cls, search: str, *, loop=None):
        """Creates a source from a YouTube URL or search term."""
        loop = loop or asyncio.get_event_loop()
        
        try:
            with yt_dlp.YoutubeDL(cls.YTDL_OPTIONS) as ydl:
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(search, download=False))
                
                if not data:
                    raise ValueError(f"Could not find any matches for: {search}")
                    
                if 'entries' in data:
                    data = data['entries'][0]

                # Create source instance
                audio = discord.FFmpegPCMAudio(data['url'], **FFMPEG_OPTIONS)
                source = cls(audio, data=data, volume=0.5)
                
                # Get segments to skip
                if 'webpage_url' in data:
                    source.sponsorblock = SponsorBlockHandler()
                    source.skip_segments = await source.sponsorblock.get_skip_segments(data['webpage_url'])
                    
                    if source.skip_segments:
                        logger.info(f"Found {len(source.skip_segments)} segments to skip")
                
                # Store metadata
                source.data = {
                    'title': data.get('title', 'Unknown'),
                    'duration': data.get('duration', 0),
                    'url': data.get('webpage_url', ''),
                    'thumbnail': data.get('thumbnail', ''),
                    'uploader': data.get('uploader', 'Unknown'),
                    'description': data.get('description', ''),
                    'view_count': data.get('view_count', 0),
                    'like_count': data.get('like_count', 0),
                    'upload_date': data.get('upload_date', ''),
                    'channel_url': data.get('channel_url', ''),
                    'tags': data.get('tags', []),
                    'stream_url': data['url']
                }

                return source

        except Exception as e:
            logger.error(f"Error creating source: {e}")
            raise

    def __init__(self, source, *, data=None, volume=0.5):
        super().__init__(source, volume)
        self.data = data or {}
        self.title = self.data.get('title', 'Unknown')
        self.url = self.data.get('url', '')
        self.duration = self.data.get('duration', 0)
        self.stream_url = self.data.get('url', '')
        self.skip_segments = []
        self.sponsorblock = SponsorBlockHandler()
