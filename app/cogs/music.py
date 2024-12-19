import discord
from discord.ext import commands
import random
import logging
import os
from models.music_queue import MusicQueue
from models.yt_source import YTDLSource
from models.music_player import MusicPlayer
from views.queue_view import QueueView
from utils.format import format_duration
import asyncio
import time
from collections import deque

# Configure logging
logger = logging.getLogger('music.cog')
log_level = logging.DEBUG if os.getenv('VERBOSE_OUTPUT', 'false').lower() == 'true' else logging.INFO
logger.setLevel(log_level)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_queue_messages = {}
        self.invalid_command_counts = {}
        self.player = MusicPlayer(bot)
        
        # Define commands with their aliases
        self.command_list = {
            'play': ['p', 'pl'],
            'playnext': ['pn'],
            'playnum': ['ptn'],
            'queue': ['q'],
            'shuffle': ['sh'],
            'skip': ['s', 'sk'],
            'skipahead': ['sa'],
            'stop': ['pause', 'ps'],
            'clear': ['c'],
            'disconnect': ['dis', 'leave'],
            'repeat': ['r'],
            'remove': ['rm']
        }
        
        # Create valid_commands list from command_list
        self.valid_commands = []
        for cmd, aliases in self.command_list.items():
            self.valid_commands.extend([cmd] + aliases)

    async def cog_load(self):
        """Called when the cog is loaded."""
        pass  # Silent initialization

    async def handle_voice_error(self, ctx):
        """Handle common voice-related errors."""
        if not ctx.author.voice:
            await ctx.send("❌ You need to be in a voice channel!")
            return True
        elif ctx.voice_client and ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.send("❌ You need to be in the same voice channel as the bot!")
            return True
        return False

    async def cleanup_old_queue_message(self, guild_id):
        """Clean up old queue message."""
        if guild_id in self.active_queue_messages:
            try:
                await self.active_queue_messages[guild_id].delete()
            except (discord.NotFound, discord.HTTPException):
                pass
            del self.active_queue_messages[guild_id]

    async def get_queue(self, ctx):
        """Get the guild's music queue."""
        if ctx.guild.id not in self.bot.music_queues:
            self.bot.music_queues[ctx.guild.id] = MusicQueue()
        return self.bot.music_queues[ctx.guild.id]

    async def process_spotify_url(self, ctx, url):
        """Process Spotify URLs and add tracks to queue."""
        try:
            async with ctx.typing():
                if 'playlist' in url:
                    tracks, playlist_info = self.bot.spotify_client.get_playlist_tracks(url)
                    if not tracks:
                        return await ctx.send("�� No tracks found in playlist")
                    
                    # Create playlist info embed
                    embed = discord.Embed(
                        title="📝 Loading Playlist",
                        description=f"**{playlist_info['name']}**",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="Tracks",
                        value=f"Adding {len(tracks)} songs to queue...",
                        inline=False
                    )
                    
                    status_msg = await ctx.send(embed=embed)
                    queue = await self.get_queue(ctx)

                    # Add all tracks to queue first
                    for track in tracks:
                        track['requester'] = ctx.author
                        queue.queue.append(track)

                    # If nothing is playing, start the first track
                    if not ctx.voice_client or not ctx.voice_client.is_playing():
                        first_track = queue.queue.popleft()  # Remove first track from queue
                        search_query = f"{first_track['title']} {first_track['artist']}"
                        source = await YTDLSource.create_source(search_query, loop=self.bot.loop)
                        source.requester = ctx.author
                        await self.player.play_song(ctx, source)

                    # Final status update
                    final_embed = discord.Embed(
                        title="✅ Playlist Added",
                        description=f"**{playlist_info['name']}**",
                        color=discord.Color.green()
                    )
                    final_embed.add_field(
                        name="Status",
                        value=f"Successfully added {len(tracks)} tracks to queue",
                        inline=False
                    )
                    await status_msg.edit(embed=final_embed)
                    
                else:
                    # Single track processing...
                    # (rest of single track code remains the same)
                    track_info = self.bot.spotify_client.get_track_info(url)
                    tracks = [track_info]
                    
                    queue = await self.get_queue(ctx)
                    
                    # Process first track
                    first_track = tracks[0]
                    first_track['requester'] = ctx.author
                    
                    # If nothing is playing, process and play first track immediately
                    if not ctx.voice_client.is_playing():
                        try:
                            search_query = f"{first_track['title']} {first_track['artist']}"
                            await ctx.send(f"🎵 Now playing: **{first_track['title']}**")
                            source = await YTDLSource.create_source(search_query, loop=self.bot.loop)
                            source.requester = ctx.author
                            await self.player.play_song(ctx, source)
                        except Exception as e:
                            logger.error(f"Error processing first track: {e}")
                            await ctx.send("❌ Error processing first track")
                            return
                    else:
                        # If something is playing, add to queue
                        queue.queue.append(first_track)
                        await ctx.send(f"✅ Added **{first_track['title']}** to queue")
                    
                    # Add remaining tracks to queue
                    if len(tracks) > 1:
                        for track in tracks[1:]:
                            track['requester'] = ctx.author
                            queue.queue.append(track)
                        
                        await ctx.send(f"✅ Added {len(tracks)-1} more tracks to queue")
                    
        except Exception as e:
            logger.error(f"Error processing Spotify URL: {e}", exc_info=True)
            await ctx.send("❌ Error processing Spotify URL")

    @commands.command(name='play', aliases=['p'])
    async def play(self, ctx, *, query=None):
        """Play a song, add to queue, or resume playback"""
        if await self.handle_voice_error(ctx):
            return
            
        # Connect to voice if not connected
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
            
        # If no query is provided, handle play/resume
        if not query:
            if ctx.voice_client and ctx.voice_client.is_paused():
                ctx.voice_client.resume()
                return await ctx.send("▶️ Resuming playback!")
            elif ctx.voice_client and ctx.voice_client.is_playing():
                return await ctx.send("⏸️ Music is already playing!")
            else:
                return await ctx.send("❌ Nothing to resume! Use `..p <song>` to play something")

        try:
            # If query is provided, always try to add to queue or play
            if self.bot.spotify_client.is_spotify_url(query):
                await self.process_spotify_url(ctx, query)
                return

            async with ctx.typing():
                source = await YTDLSource.create_source(query, loop=self.bot.loop)
                source.requester = ctx.author
                queue = await self.get_queue(ctx)
                
                if ctx.voice_client and ctx.voice_client.is_playing():
                    # Add to queue if something is playing
                    queue.queue.append(source)
                    duration_str = format_duration(source.duration)
                    embed = discord.Embed(
                        title="Added to Queue",
                        description=f"**{source.title}**\nBy: {source.uploader}\nDuration: {duration_str}",
                        color=discord.Color.green()
                    )
                    embed.set_thumbnail(url=source.thumbnail)
                    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
                    await ctx.send(embed=embed)
                else:
                    # Start playing if nothing is playing
                    await self.player.play_song(ctx, source)
                    
        except Exception as e:
            logger.error(f"Error in play command: {str(e)}", exc_info=True)
            await ctx.send(f"❌ Failed to play: {type(e).__name__}")

    @commands.command(name='skip', aliases=['s'])
    async def skip(self, ctx):
        """Skip the current song."""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            return await ctx.send("❌ No song is currently playing!")
            
        queue = await self.get_queue(ctx)
        if not queue.queue:
            ctx.voice_client.stop()
            return await ctx.send("Queue is empty!")
            
        # Get next song info before stopping current
        next_song = queue.queue[0]
        next_song_name = next_song['title'] if isinstance(next_song, dict) else next_song.title
            
        # Stop current song (this will trigger play_next via the after callback)
        ctx.voice_client.stop()
        await ctx.send(f"⏭️ Skipping to **{next_song_name}**!")

    @commands.command(name='queue', aliases=['q'])
    async def queue(self, ctx):
        """Display the current queue."""
        queue = await self.get_queue(ctx)
        if not queue.queue:
            return await ctx.send("❌ Queue is empty!")
            
        view = QueueView(ctx, self.bot)
        await view.show()

    @commands.command(name='shuffle', aliases=['sh'])
    async def shuffle(self, ctx):
        """Shuffle the queue."""
        queue = await self.get_queue(ctx)
        
        if not queue.queue:
            return await ctx.send("��� Queue is empty!")
            
        try:
            queue_list = list(queue.queue)
            tracks_by_user = {}
            
            # Group tracks by requester
            for track in queue_list:
                if isinstance(track, dict):
                    requester = track.get('requester', ctx.author)
                else:
                    requester = getattr(track, 'requester', ctx.author)
                    
                requester_id = getattr(requester, 'id', 'unknown')
                if requester_id not in tracks_by_user:
                    tracks_by_user[requester_id] = []
                tracks_by_user[requester_id].append(track)
            
            # Shuffle each user's tracks
            for tracks in tracks_by_user.values():
                random.shuffle(tracks)
            
            # Interleave tracks
            shuffled_tracks = []
            max_tracks = max(len(tracks) for tracks in tracks_by_user.values())
            
            for i in range(max_tracks):
                for user_id in tracks_by_user:
                    if i < len(tracks_by_user[user_id]):
                        shuffled_tracks.append(tracks_by_user[user_id][i])
            
            # Update queue
            queue.queue.clear()
            queue.queue.extend(shuffled_tracks)
            queue.shuffle_count += 1
            
            await ctx.send(f"🔀 Successfully shuffled {len(shuffled_tracks)} tracks!")
            
        except Exception as e:
            logger.error(f"Error in shuffle command: {e}")
            await ctx.send("❌ An error occurred while shuffling the queue")

    @commands.command(name='stop', aliases=['pause', 'ps'])
    async def stop(self, ctx):
        """Pause the current song."""
        if await self.handle_voice_error(ctx):
            return
            
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸️ Playback paused!")
        else:
            await ctx.send("❌ Nothing is playing!")

    @commands.command(name='clear', aliases=['c'])
    async def clear(self, ctx):
        """Clear the queue."""
        queue = await self.get_queue(ctx)
        
        if not queue.queue:
            return await ctx.send("❌ Queue is already empty!")
            
        # Create confirmation message with reactions
        confirm_msg = await ctx.send("⚠️ Are you sure you want to clear the queue?")
        await confirm_msg.add_reaction('✅')
        await confirm_msg.add_reaction('❌')
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirm_msg.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == '✅':
                queue.queue.clear()
                await confirm_msg.delete()
                await ctx.send("🗑️ Queue has been cleared successfully!")
            else:
                await confirm_msg.delete()
                await ctx.send("🚫 Queue clear operation cancelled.")
                
        except asyncio.TimeoutError:
            await confirm_msg.delete()
            await ctx.send("⏱️ Queue clear operation timed out.")

    @commands.command(name='disconnect', aliases=['dis', 'leave'])
    async def disconnect(self, ctx):
        """Disconnect the bot from voice."""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("👋 Disconnected from voice channel!")
        else:
            await ctx.send("❌ Not connected to any voice channel!")

    @commands.command(name='repeat', aliases=['r'])
    async def repeat(self, ctx):
        """Toggle repeat mode for the queue."""
        queue = await self.get_queue(ctx)
        queue.loop = not queue.loop
        
        if queue.loop:
            await ctx.send("🔁 Repeat mode enabled - Queue will loop")
        else:
            await ctx.send("➡️ Repeat mode disabled")

    @commands.command(name='skipahead', aliases=['sa'])
    async def skipahead(self, ctx, seconds: int = 15):
        """Skip ahead in the current song."""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            return await ctx.send("❌ No song is currently playing!")

        try:
            source = ctx.voice_client.source
            if not hasattr(source, 'original') or not hasattr(source.original, 'url'):
                return await ctx.send("❌ Cannot skip ahead in current track!")
                
            # Ensure seconds is within reasonable bounds
            seconds = max(1, min(seconds, 300))  # Between 1 and 300 seconds
            
            # Create new source at new position
            new_source = await YTDLSource.create_source(
                source.original.url,  # Use the original webpage URL
                loop=self.bot.loop,
                start_time=seconds
            )
            
            # Stop current playback and start at new position
            ctx.voice_client.stop()
            await self.player.play_song(ctx, new_source)
            await ctx.send(f"⏩ Skipped ahead {seconds} seconds")
            
        except Exception as e:
            logger.error(f"Error in skipahead command: {e}")
            await ctx.send("❌ Failed to skip ahead")

    @commands.command(name='playnum', aliases=['ptn'])
    async def playnum(self, ctx, num: int):
        """Play a specific song from the queue."""
        if await self.handle_voice_error(ctx):
            return
            
        queue = await self.get_queue(ctx)
        if not queue.queue:
            return await ctx.send("❌ Queue is empty!")
            
        if num < 1 or num > len(queue.queue):
            return await ctx.send(f"❌ Please enter a number between 1 and {len(queue.queue)}")
            
        # Get the selected song
        song = queue.pop_at(num - 1)
        if not song:
            return await ctx.send("❌ Failed to get the selected song")
        
        song_name = song['title'] if isinstance(song, dict) else song.title
        
        # Move it to the front of the queue
        queue.queue.appendleft(song)
        
        # Skip current song to play the selected one
        await ctx.send(f"⏭️ Skipping to **{song_name}**...")
        await self.skip(ctx)

    @commands.command(name='nowplaying', aliases=['np'])
    async def nowplaying(self, ctx):
        """Show information about the currently playing song."""
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            return await ctx.send("❌ Nothing is playing right now!")

        try:
            # Get current track info from player
            track_data = self.player.get_current_track()
            if not track_data:
                return await ctx.send("❌ No track information available!")

            # Create and start the Now Playing view
            from views.now_playing_view import NowPlayingView
            
            # Stop previous view if exists
            if hasattr(self.bot, 'current_np_view') and self.bot.current_np_view:
                self.bot.current_np_view.stop()
                if hasattr(self.bot.current_np_view, 'message'):
                    try:
                        await self.bot.current_np_view.message.delete()
                    except:
                        pass

            # Create new view
            view = NowPlayingView(ctx, self.bot, track_data)
            await view.start()

        except Exception as e:
            logger.error(f"Error in nowplaying command: {e}")
            await ctx.send("❌ Error displaying now playing view")

    async def play_song(self, ctx, source):
        """Play a song and show now playing."""
        try:
            # Stop any existing now playing view
            if hasattr(self.bot, 'current_np_view'):
                try:
                    self.bot.current_np_view.stop()
                except:
                    pass

            # Play the song
            await self.player.play_song(ctx, source)

        except Exception as e:
            logger.error(f"Error in play_song: {e}")
            await ctx.send("❌ Error playing song")

    @commands.command(name='remove', aliases=['rm'])
    async def remove(self, ctx, *, target):
        """Remove song(s) from queue. Can specify number or @user."""
        queue = await self.get_queue(ctx)
        
        if not queue.queue:
            return await ctx.send("❌ Queue is empty!")

        # Check if target is a user mention
        if ctx.message.mentions:
            target_user = ctx.message.mentions[0]
            # Count songs by this user
            user_songs = [song for song in queue.queue 
                         if (isinstance(song, dict) and song.get('requester', None) == target_user) or
                            (hasattr(song, 'requester') and song.requester == target_user)]
            
            if not user_songs:
                return await ctx.send(f"❌ No songs found by {target_user.mention} in the queue!")

            # Create confirmation message
            confirm_embed = discord.Embed(
                title="⚠️ Remove User's Songs",
                description=f"Are you sure you want to remove all {len(user_songs)} songs requested by {target_user.mention}?",
                color=discord.Color.yellow()
            )
            confirm_msg = await ctx.send(embed=confirm_embed)
            await confirm_msg.add_reaction('✅')
            await confirm_msg.add_reaction('❌')

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == confirm_msg.id

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                
                if str(reaction.emoji) == '✅':
                    # Remove all songs by the user
                    original_length = len(queue.queue)
                    queue.queue = deque([song for song in queue.queue 
                                      if (isinstance(song, dict) and song.get('requester', None) != target_user) or
                                         (hasattr(song, 'requester') and song.requester != target_user)])
                    removed_count = original_length - len(queue.queue)
                    
                    await confirm_msg.delete()
                    await ctx.send(f"✅ Removed {removed_count} songs requested by {target_user.mention}")
                else:
                    await confirm_msg.delete()
                    await ctx.send("❌ Operation cancelled")
                    
            except asyncio.TimeoutError:
                await confirm_msg.delete()
                await ctx.send("⏱️ Operation timed out")
                
        else:
            # Original single song removal logic
            try:
                index = int(target) - 1
                if 0 <= index < len(queue.queue):
                    removed = queue.pop_at(index)
                    if removed:
                        title = removed['title'] if isinstance(removed, dict) else removed.title
                        await ctx.send(f"✅ Removed **{title}** from queue")
                    else:
                        await ctx.send("❌ Failed to remove song")
                else:
                    await ctx.send(f"❌ Please enter a number between 1 and {len(queue.queue)}")
            except ValueError:
                await ctx.send("❌ Please specify a valid number or @mention a user")
