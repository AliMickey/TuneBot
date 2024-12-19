import discord
import asyncio
import logging
from models.yt_source import YTDLSource, FFMPEG_OPTIONS
from utils.format import format_duration
import time

logger = logging.getLogger('music.player')

class MusicPlayer:
    def __init__(self, bot):
        self.bot = bot
        self._current = None
        self._current_view = None
        self._current_source = None
        self._position = 0

    def _store_track_info(self, source):
        """Store current track information."""
        try:
            # Get metadata from source
            metadata = getattr(source, 'data', {})
            if not metadata and hasattr(source, 'original'):
                metadata = getattr(source.original, 'data', {})

            self._current = {
                'title': metadata.get('title', getattr(source, 'title', 'Unknown')),
                'duration': metadata.get('duration', getattr(source, 'duration', 0)),
                'url': metadata.get('url', ''),
                'thumbnail': metadata.get('thumbnail', ''),
                'requester': getattr(source, 'requester', 'Unknown'),
                'uploader': metadata.get('uploader', getattr(source, 'artist', 'Unknown')),
                'description': metadata.get('description', ''),
                'view_count': metadata.get('view_count', 0),
                'like_count': metadata.get('like_count', 0),
                'upload_date': metadata.get('upload_date', ''),
                'channel_url': metadata.get('channel_url', ''),
                'tags': metadata.get('tags', []),
                'position': 0
            }
            self._current_source = source
            self._position = 0
            
        except Exception as e:
            logger.error(f"Error storing track info: {e}")
            self._current = None

    def get_current_track(self):
        """Get current track info."""
        if not self._current:
            return None
        
        try:
            # Update position if available
            if self._current_source:
                if hasattr(self._current_source, '_player'):
                    self._position = getattr(self._current_source._player, 'pos', self._position)
                elif hasattr(self._current_source, 'original'):
                    self._position = getattr(self._current_source.original, 'pos', self._position)
            
            self._current['position'] = self._position
            return self._current
            
        except Exception as e:
            logger.error(f"Error getting current track: {e}")
            return self._current

    async def process_spotify_playlist(self, tracks, ctx):
        """Process tracks from Spotify playlist."""
        queue = self.bot.music_queues[ctx.guild.id]
        
        # Add all tracks to queue
        for track in tracks:
            track['requester'] = ctx.author
            queue.queue.append(track)
            
        # If nothing is playing, start the first track
        if not ctx.voice_client.is_playing():
            first_track = queue.queue.popleft()
            search_query = f"{first_track['title']} {first_track.get('artist', '')}"
            source = await YTDLSource.create_source(search_query, loop=self.bot.loop)
            source.requester = ctx.author
            await self.play_song(ctx, source)

    async def play_next(self, ctx, error=None):
        """Play the next song in queue."""
        if error:
            await ctx.send(f"❌ Error: {str(error)}")

        try:
            queue = self.bot.music_queues[ctx.guild.id]
            if not queue.queue:
                if queue.loop and self._current:
                    queue.queue.append(self._current)
                else:
                    return

            # Get next track
            next_track = queue.queue.popleft()
            self._current = next_track

            # Create source
            if isinstance(next_track, dict):
                # Spotify track
                search_query = f"{next_track['title']} {next_track.get('artist', '')}"
                source = await YTDLSource.create_source(search_query, loop=self.bot.loop)
                source.requester = next_track['requester']
                # Store additional metadata
                source.title = next_track['title']
                source.artist = next_track.get('artist', '')
                source.duration = next_track.get('duration', 0)
            else:
                # YouTube track
                source = next_track

            # Play the track
            await self.play_song(ctx, source)

        except Exception as e:
            logger.error(f"Error in play_next: {e}")
            await ctx.send("❌ Error playing next song")
            # Try next song
            if queue and queue.queue:
                await self.play_next(ctx)

    async def play_song(self, ctx, source):
        """Play a song and show now playing."""
        try:
            # Stop current view if exists
            if hasattr(self.bot, 'current_np_view') and self.bot.current_np_view:
                self.bot.current_np_view.stop()

            # Store track info before creating audio source
            self._store_track_info(source)
            self._position = 0

            # Create audio source with time tracking
            audio = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(source.stream_url, **FFMPEG_OPTIONS)
            )
            
            # Add tracking info
            audio.start_time = time.time()
            audio.original = source
            
            # Play the song
            if ctx.voice_client:
                ctx.voice_client.play(
                    audio, 
                    after=lambda e: self.bot.loop.create_task(self.play_next(ctx, e))
                )

                # Show now playing view
                if self._current:
                    from views.now_playing_view import NowPlayingView
                    view = NowPlayingView(ctx, self.bot, self._current)
                    self.bot.current_np_view = view
                    await view.start()

        except Exception as e:
            logger.error(f"Error in play_song: {e}")
            await ctx.send("❌ Error playing song")

    def get_current_source(self):
        """Get current source."""
        return self._current_source