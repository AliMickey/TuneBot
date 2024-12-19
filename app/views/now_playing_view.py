import discord
import asyncio
import random
import time
from datetime import datetime
import math
from utils.format import format_duration
import logging
logger = logging.getLogger('now_playing.view')

class NowPlayingView:
    def __init__(self, ctx, bot, track_info):
        self.ctx = ctx
        self.bot = bot
        self.track_info = track_info
        self.message = None
        self.is_updating = True
        self.start_time = time.time()
        
        # Progress bar settings
        self.bar_length = 24
        self.bar_empty = "─"
        self.bar_filled = "━"
        self.slider_chars = ["⬤", "◉", "○", "◉"]
        self.slider_index = 0
        
        # Update intervals (in seconds)
        self.update_intervals = [4, 6, 8]
        
        # Visualizer frames (fixed characters)
        self.visualizer_frames = [
            "▁▂▃▄▅▆▇█▇▆▅▄▃▂▁",
            "▂▃▄▅▆▇█▇▆▅▄▃▂▁▁",
            "▃▄▅▆▇█▇▆▅▄▃▂▁▁▂",
            "▄▅▆▇█▇▆▅▄▃▂▁▁▂▃",
            "▅▆▇█▇▆▅▄▃▂▁▁▂▃▄",
            "▆▇█▇▆▅▄▃▂▁▁▂▃▄▅",
            "▇█▇▆▅▄▃▂▁▁▂▃▄▅▆",
            "█▇▆▅▄▃▂▁▁▂▃▄▅▆▇",
            "▇▆▅▄▃▂▁▁▂▃▄▅▆▇█",
            "▆▅▄▃▂▁▁▂▃▄▅▆▇█▇",
            "▅▄▃▂▁▁▂▃▄▅▆▇█▇▆",
            "▄▃▂▁▁▂▃▄▅▆▇█▇▆▅",
            "▃▂▁▁▂▃▄▅▆▇█▇▆▅▄",
            "▂▁▁▂▃▄▅▆▇█▇▆▅▄▃"
        ]
        self.frame_index = 0
        self.current_position = 0

        # Store previous view to cleanup
        self.previous_view = getattr(bot, 'current_np_view', None)
        bot.current_np_view = self

    def create_progress_bar(self, position, duration):
        """Create an animated progress bar."""
        percentage = position / duration if duration > 0 else 0
        filled_length = math.floor(self.bar_length * percentage)
        
        # Create filled and empty sections
        filled = self.bar_filled * filled_length
        empty = self.bar_empty * (self.bar_length - filled_length - 1)
        
        # Add animated slider
        slider = self.slider_chars[self.slider_index]
        self.slider_index = (self.slider_index + 1) % len(self.slider_chars)
        
        return f"{filled}{slider}{empty}"

    def get_visualizer(self):
        """Get current visualizer frame with wave effect."""
        base_frame = self.visualizer_frames[self.frame_index]
        self.frame_index = (self.frame_index + 1) % len(self.visualizer_frames)
        
        # Add stereo effect
        left_wave = base_frame
        right_wave = base_frame[::-1]  # Reverse for stereo effect
        
        return f"{left_wave} ♪ {right_wave}"

    def get_requester_mention(self):
        """Get clickable mention for requester."""
        requester = self.track_info.get('requester')
        if isinstance(requester, (discord.Member, discord.User)):
            return requester.mention
        return str(requester)

    def get_next_track_info(self):
        """Get formatted info about the next track."""
        try:
            if self.ctx.guild.id in self.bot.music_queues:
                queue = self.bot.music_queues[self.ctx.guild.id]
                if queue and queue.queue:
                    next_track = queue.queue[0]
                    
                    # Get track info based on type
                    if isinstance(next_track, dict):
                        title = next_track.get('title', 'Unknown')
                        duration = next_track.get('duration', 0)
                        requester = next_track.get('requester', 'Unknown')
                        url = next_track.get('url', '')
                    else:
                        title = getattr(next_track, 'title', 'Unknown')
                        duration = getattr(next_track, 'duration', 0)
                        requester = getattr(next_track, 'requester', 'Unknown')
                        url = getattr(next_track, 'url', '')

                    # Format requester mention
                    if isinstance(requester, (discord.Member, discord.User)):
                        requester = requester.mention
                    else:
                        requester = str(requester)

                    return {
                        'title': title,
                        'duration': duration,
                        'requester': requester,
                        'url': url
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting next track info: {e}")
            return None

    def get_embed(self):
        """Create the Now Playing embed."""
        try:
            duration = self.track_info.get('duration', 0)
            title = self.track_info.get('title', 'Unknown')
            url = self.track_info.get('url', '')
            thumbnail = self.track_info.get('thumbnail', '')
            uploader = self.track_info.get('uploader', 'Unknown')
            view_count = self.track_info.get('view_count', 0)
            like_count = self.track_info.get('like_count', 0)
            
            # Get visualizer with stereo effect
            visualizer = self.get_visualizer()

            # Create embed with single title
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**[{title}]({url})**\n```ansi\n{visualizer}\n```",
                color=discord.Color.blue()
            )

            # Calculate time values
            elapsed = self.current_position
            remaining = max(0, duration - elapsed)
            percentage = (elapsed / duration * 100) if duration > 0 else 0

            # Progress bar
            progress_bar = self.create_progress_bar(elapsed, duration)
            timestamp = f"`{format_duration(elapsed)} / {format_duration(duration)}`"
            
            embed.add_field(
                name="Progress",
                value=f"{progress_bar}\n{timestamp} ({percentage:.0f}%)",
                inline=False
            )

            # Track info section
            info = [
                f"👤 **Requested by:** {self.get_requester_mention()}",
                f"📺 **Uploader:** [{uploader}]({self.track_info.get('channel_url', '')})",
                f"👁️ **Views:** {view_count:,}",
                f"👍 **Likes:** {like_count:,}",
                f"⏱️ **Duration:** {format_duration(duration)}",
                f"⌛ **Remaining:** {format_duration(remaining)}",
                f"🎼 **Position:** {format_duration(elapsed)}"
            ]
            embed.add_field(name="Track Info", value="\n".join(info), inline=True)

            # Add divider
            embed.add_field(name="\u200b", value="\u200b", inline=False)

            # Queue info
            if self.ctx.guild.id in self.bot.music_queues:
                queue = self.bot.music_queues[self.ctx.guild.id]
                if queue:
                    embed.add_field(
                        name="Queue Status",
                        value=f"📝 **In Queue:** {len(queue.queue)} tracks",
                        inline=False
                    )

            # Next track section
            next_track = self.get_next_track_info()
            if next_track:
                # Next track info
                next_title = f"**[{next_track['title']}]({next_track['url']})**" if next_track['url'] else f"**{next_track['title']}**"
                next_info = [
                    "⏭️ **Playing Next:**",
                    next_title,
                    f"⏱️ `{format_duration(next_track['duration'])}`",
                    f"👤 {next_track['requester']}"
                ]
            else:
                # No more tracks in queue
                next_info = [
                    "🎵 **Queue Status:**",
                    "📪 End of queue reached",
                    "",
                    "*Use ..play to add more tracks*"
                ]

            embed.add_field(
                name="Next Track",
                value="\n".join(next_info),
                inline=False
            )

            if thumbnail:
                embed.set_thumbnail(url=thumbnail)

            embed.timestamp = datetime.utcnow()
            return embed

        except Exception as e:
            logger.error(f"Error creating embed: {e}")
            return None

    async def update_position(self):
        """Update the current position."""
        try:
            if not self.ctx.voice_client or not self.ctx.voice_client.is_playing():
                return False

            source = self.ctx.voice_client.source
            if not source:
                return False

            # Calculate elapsed time
            if hasattr(source, 'start_time'):
                elapsed = time.time() - source.start_time
                self.current_position = int(elapsed)
            elif hasattr(source, '_player') and hasattr(source._player, 'time'):
                self.current_position = int(source._player.time / 1000)  # Convert ms to seconds
            else:
                # Fallback to manual tracking
                elapsed = time.time() - self.start_time
                self.current_position = int(elapsed)

            # Ensure position doesn't exceed duration
            duration = self.track_info.get('duration', 0)
            if duration > 0:
                self.current_position = min(self.current_position, duration)

            return True

        except Exception as e:
            logger.error(f"Error updating position: {e}")
            return False

    async def start(self):
        """Start the Now Playing view with updates."""
        try:
            # Stop and delete previous view if exists
            if self.previous_view:
                self.previous_view.stop()
                if hasattr(self.previous_view, 'message') and self.previous_view.message:
                    try:
                        await self.previous_view.message.delete()
                    except discord.NotFound:
                        pass

            # Initialize position and start time
            self.current_position = 0
            self.start_time = time.time()
            
            # Create and send initial embed
            initial_embed = self.get_embed()
            if not initial_embed:
                raise ValueError("Failed to create initial embed")

            self.message = await self.ctx.send(embed=initial_embed)
            
            # Update loop
            while self.is_updating:
                try:
                    if not await self.update_position():
                        break

                    embed = self.get_embed()
                    if embed:
                        await self.message.edit(embed=embed)
                    
                    # Update every second
                    await asyncio.sleep(1)

                except discord.NotFound:
                    break  # Message was deleted
                except discord.HTTPException:
                    await asyncio.sleep(4)  # Rate limit
                except Exception as e:
                    logger.error(f"Error updating now playing view: {e}")
                    break

        except Exception as e:
            logger.error(f"Failed to start now playing view: {e}")
            await self.ctx.send("❌ Failed to display now playing view")
            self.stop()

    def stop(self):
        """Stop updating the Now Playing view."""
        self.is_updating = False
        if hasattr(self, 'message') and self.message:
            try:
                asyncio.create_task(self.message.delete())
            except:
                pass
        if hasattr(self.bot, 'current_np_view') and self.bot.current_np_view == self:
            self.bot.current_np_view = None