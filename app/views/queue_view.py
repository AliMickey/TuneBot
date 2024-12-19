import discord
import math
from utils.format import format_duration
import logging

logger = logging.getLogger('queue.view')

class QueueView(discord.ui.View):
    def __init__(self, ctx, bot):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.bot = bot
        self.page = 0
        self.items_per_page = 20
        self.message = None
        
        # Add navigation buttons
        self.add_item(self.create_first_button())
        self.add_item(self.create_prev_button())
        self.add_item(self.create_next_button())
        self.add_item(self.create_last_button())
        self.add_item(self.create_jump_button())

    def create_first_button(self):
        """Create first page button."""
        button = discord.ui.Button(
            label="First",
            emoji="⏮️",
            style=discord.ButtonStyle.primary,
            disabled=True,
            custom_id="first_button"
        )
        button.callback = self.first_button_callback
        return button

    def create_prev_button(self):
        """Create previous page button."""
        button = discord.ui.Button(
            label="Previous",
            emoji="◀️",
            style=discord.ButtonStyle.primary,
            disabled=True,
            custom_id="prev_button"
        )
        button.callback = self.prev_button_callback
        return button

    def create_next_button(self):
        """Create next page button."""
        button = discord.ui.Button(
            label="Next",
            emoji="▶️",
            style=discord.ButtonStyle.primary,
            custom_id="next_button"
        )
        button.callback = self.next_button_callback
        return button

    def create_last_button(self):
        """Create last page button."""
        button = discord.ui.Button(
            label="Last",
            emoji="⏭️",
            style=discord.ButtonStyle.primary,
            custom_id="last_button"
        )
        button.callback = self.last_button_callback
        return button

    def create_jump_button(self):
        """Create jump to page button."""
        button = discord.ui.Button(
            label="Jump",
            emoji="📑",
            style=discord.ButtonStyle.secondary,
            custom_id="jump_button"
        )
        button.callback = self.jump_button_callback
        return button

    async def first_button_callback(self, interaction: discord.Interaction):
        """Handle first page button."""
        self.page = 0
        self.update_button_states()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def prev_button_callback(self, interaction: discord.Interaction):
        """Handle previous page button."""
        self.page = max(0, self.page - 1)
        self.update_button_states()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def next_button_callback(self, interaction: discord.Interaction):
        """Handle next page button."""
        total_pages = math.ceil(len(self.bot.music_queues[self.ctx.guild.id].queue) / self.items_per_page)
        self.page = min(self.page + 1, total_pages - 1)
        self.update_button_states()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def last_button_callback(self, interaction: discord.Interaction):
        """Handle last page button."""
        total_pages = math.ceil(len(self.bot.music_queues[self.ctx.guild.id].queue) / self.items_per_page)
        self.page = total_pages - 1
        self.update_button_states()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def jump_button_callback(self, interaction: discord.Interaction):
        """Handle jump to page button."""
        total_pages = math.ceil(len(self.bot.music_queues[self.ctx.guild.id].queue) / self.items_per_page)
        modal = JumpPageModal(total_pages)
        await interaction.response.send_modal(modal)
        await modal.wait()
        
        if modal.page_number:
            self.page = modal.page_number - 1
            self.update_button_states()
            await interaction.message.edit(embed=self.get_embed(), view=self)

    def update_button_states(self):
        """Update button disabled states."""
        total_pages = math.ceil(len(self.bot.music_queues[self.ctx.guild.id].queue) / self.items_per_page)
        
        for child in self.children:
            if child.custom_id == "first_button" or child.custom_id == "prev_button":
                child.disabled = self.page == 0
            elif child.custom_id == "next_button" or child.custom_id == "last_button":
                child.disabled = self.page >= total_pages - 1

    def get_queue_page(self):
        """Get the current page of the queue."""
        if self.ctx.guild.id not in self.bot.music_queues:
            return []
            
        queue = self.bot.music_queues[self.ctx.guild.id]
        if not queue or not queue.queue:
            return []
            
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        return list(queue.queue)[start:end]

    def get_embed(self):
        """Create queue embed."""
        queue_items = self.get_queue_page()
        total_queue = len(self.bot.music_queues[self.ctx.guild.id].queue) if self.ctx.guild.id in self.bot.music_queues else 0
        
        embed = discord.Embed(
            title="🎵 Music Queue",
            description=f"Page {self.page + 1}/{math.ceil(total_queue / self.items_per_page)}\n" \
                       f"Showing {self.items_per_page} tracks per page",
            color=discord.Color.blue()
        )

        if not queue_items:
            embed.description = "📪 Queue is empty\n*Use ..play to add some tracks!*"
            return embed

        # Format queue items
        queue_text = []
        start_index = self.page * self.items_per_page
        
        for i, item in enumerate(queue_items, start=start_index + 1):
            if isinstance(item, dict):
                # Spotify track
                title = f"{item['title']} {item.get('artist', '')}"
                duration = format_duration(item.get('duration', 0))
                requester = item.get('requester', 'Unknown')
                artist = item.get('artist', 'Unknown')
            else:
                # YouTube track
                title = getattr(item, 'title', 'Unknown')
                duration = format_duration(getattr(item, 'duration', 0))
                requester = getattr(item, 'requester', 'Unknown')
                artist = getattr(item, 'uploader', 'Unknown')

            # Format requester mention
            if isinstance(requester, (discord.Member, discord.User)):
                requester = requester.mention
            else:
                requester = str(requester)

            queue_text.append(
                f"{str(i).zfill(2)} {title}\n└─ {requester} | ⏱️ {duration} | 🎵 {artist}"
            )

        # Split into chunks if needed
        if len("\n".join(queue_text)) > 1024:
            half = len(queue_text) // 2
            embed.add_field(
                name=f"📑 Queue (Page {self.page + 1}/{math.ceil(total_queue / self.items_per_page)})",
                value="\n".join(queue_text[:half]),
                inline=False
            )
            embed.add_field(
                name="Continued",
                value="\n".join(queue_text[half:]),
                inline=False
            )
        else:
            embed.add_field(
                name=f"📑 Queue (Page {self.page + 1}/{math.ceil(total_queue / self.items_per_page)})",
                value="\n".join(queue_text),
                inline=False
            )
        
        # Queue Status
        queue = self.bot.music_queues[self.ctx.guild.id]
        status = [
            f"• Total Tracks: {total_queue}",
            f"• 🔁 Loop: {'Enabled' if queue.loop else 'Disabled'}",
            f"• 🔊 Volume: {int(queue.volume * 100)}%",
            f"• 🎲 Shuffled: {queue.shuffle_count} times",
            f"• ⏱️ Total Duration: {self.get_total_duration()}"
        ]
        embed.add_field(name="📊 Queue Status", value="\n".join(status), inline=False)

        # Add contributors section
        contributors = {}
        for item in queue.queue:
            requester = item.get('requester', None) if isinstance(item, dict) else getattr(item, 'requester', None)
            if hasattr(requester, 'mention'):
                if requester.mention not in contributors:
                    contributors[requester.mention] = {'tracks': 0, 'duration': 0}
                contributors[requester.mention]['tracks'] += 1
                duration = item.get('duration', 0) if isinstance(item, dict) else getattr(item, 'duration', 0)
                contributors[requester.mention]['duration'] += duration

        if contributors:
            contributor_text = "\n".join(
                f"• 👤 {mention} | 🎵 {stats['tracks']} tracks | ⏱️ {format_duration(stats['duration'])}"
                for mention, stats in contributors.items()
            )
            embed.add_field(name="👥 Contributors", value=contributor_text, inline=False)
        
        return embed

    def get_total_duration(self):
        """Calculate total duration of queue."""
        if self.ctx.guild.id not in self.bot.music_queues:
            return "0:00"
            
        queue = self.bot.music_queues[self.ctx.guild.id]
        if not queue or not queue.queue:
            return "0:00"
            
        total_seconds = 0
        for item in queue.queue:
            if isinstance(item, dict):
                total_seconds += item.get('duration', 0)
            else:
                total_seconds += getattr(item, 'duration', 0)
                
        return format_duration(total_seconds)

    async def show(self):
        """Display the queue."""
        embed = self.get_embed()
        self.message = await self.ctx.send(embed=embed, view=self)

class JumpPageModal(discord.ui.Modal, title="Jump to Page"):
    def __init__(self, max_pages):
        super().__init__()
        self.max_pages = max_pages
        self.page_number = None
        
        self.page_input = discord.ui.TextInput(
            label=f"Enter page number (1-{max_pages})",
            placeholder="Enter a number...",
            min_length=1,
            max_length=len(str(max_pages)),
            required=True
        )
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            page = int(self.page_input.value)
            if 1 <= page <= self.max_pages:
                self.page_number = page
                await interaction.response.defer()
            else:
                await interaction.response.send_message(
                    f"❌ Please enter a number between 1 and {self.max_pages}",
                    ephemeral=True
                )
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number",
                ephemeral=True
            )
