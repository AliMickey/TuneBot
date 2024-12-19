import os
import discord
import asyncio
from discord.ext import commands
from models.spotify_client import SpotifyClient

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

class MusicBot(commands.Bot):
    def __init__(self):
        prefix = os.getenv('COMMAND_PREFIX', '..')
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        
        super().__init__(
            command_prefix=prefix,
            intents=intents,
            help_command=None
        )
        
        self.music_queues = {}
        self.spotify_client = SpotifyClient()
        self._initialized = False
        self._shutdown_event = asyncio.Event()
        self.current_np_view = None
    
    async def setup_hook(self):
        """Initialize cogs and configurations."""
        if self._initialized:
            return
            
        print("\n✅ Bot Initialization")
        
        try:
            # Load music cog
            from cogs.music import Music
            await self.add_cog(Music(self))
            print("✅ Commands")

            # Register help command
            @self.command(name='help', aliases=['h'])
            async def help_command(ctx):
                embed = discord.Embed(
                    title="🎵 TuneBot Commands",
                    description=f"Use `{ctx.prefix}command` or its alias",
                    color=discord.Color.blue()
                )

                playback = (
                    f"`play` (`p`) • Play music or add to queue\n"
                    f"`playnext` (`pn`) • Add song to play next\n"
                    f"`stop` (`ps`, `pause`) • Pause/Resume playback\n"
                    f"`skip` (`s`) • Skip to next song\n"
                    f"`nowplaying` (`np`) • Show current song info\n"
                    f"`fast` (`f`, `ff`) • Skip ahead in current song\n"
                    f"`disconnect` (`dis`, `leave`) • Leave channel"
                )
                embed.add_field(name="🎮 Music Controls", value=playback, inline=False)

                queue = (
                    f"`queue` (`q`) • View current queue\n"
                    f"`shuffle` (`sh`) • Randomize queue\n"
                    f"`clear` (`c`) • Empty the queue\n"
                    f"`playnum` (`ptn`) • Play specific song number\n"
                    f"`repeat` (`r`) • Toggle queue loop"
                )
                embed.add_field(name="📋 Queue Controls", value=queue, inline=False)

                examples = (
                    f"`{ctx.prefix}p never gonna give you up` • Search & play\n"
                    f"`{ctx.prefix}p https://youtu.be/...` • Play URL\n"
                    f"`{ctx.prefix}f` • Skip ahead 15 seconds\n"
                    f"`{ctx.prefix}f 45` • Jump to 45 seconds\n"
                    f"`{ctx.prefix}ptn 3` • Play queue item #3"
                )
                embed.add_field(name="💡 Examples", value=examples, inline=False)

                features = (
                    "• YouTube and Spotify support\n"
                    "• Search by name or URL\n"
                    "• Fast forward in songs\n"
                    "• Queue management\n"
                    "• Live song progress\n"
                    "• Loop mode"
                )
                embed.add_field(name="✨ Features", value=features, inline=False)

                await ctx.send(embed=embed)

            if self.spotify_client.check_connection():
                print("✅ Spotify")
            else:
                print("❌ Spotify")

            print("✅ Ready")
            self._initialized = True

        except Exception as e:
            print("❌ Failed to load commands")
            raise e
    
    async def on_ready(self):
        """Called when the bot is ready."""
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name=f"music | {self.command_prefix}help"
        )
        await self.change_presence(activity=activity)

    async def close(self):
        """Clean shutdown."""
        for guild in self.guilds:
            if guild.voice_client:
                await guild.voice_client.disconnect()

        if self.current_np_view:
            self.current_np_view.stop()

        self.music_queues.clear()

        await super().close()

async def main():
    """Main async function to run the bot."""
    bot = MusicBot()
    
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        raise ValueError("No Discord token found in environment variables!")
    
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        if os.path.exists('/tmp/healthy'):
            os.remove('/tmp/healthy')
