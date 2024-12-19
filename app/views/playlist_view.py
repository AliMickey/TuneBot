import discord
import math
from discord.ui import View, Select

class PlaylistView(View):
    def __init__(self, tracks, per_page=10):
        super().__init__(timeout=300)  # 5 minute timeout
        self.tracks = tracks
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = math.ceil(len(tracks) / per_page)
        
        # Add the select menu
        self.add_item(self.create_page_select())
    
    def create_page_select(self):
        select = Select(
            placeholder=f"Page 1/{self.total_pages}",
            options=[
                discord.SelectOption(
                    label=f"Page {i+1}",
                    value=str(i)
                ) for i in range(self.total_pages)
            ]
        )
        
        async def callback(interaction):
            self.current_page = int(select.values[0])
            await self.update_message(interaction)
            
        select.callback = callback
        return select
    
    def get_current_page_content(self):
        start_idx = self.current_page * self.per_page
        end_idx = start_idx + self.per_page
        current_tracks = self.tracks[start_idx:end_idx]
        
        content = "**Playlist Tracks:**\n"
        for i, track in enumerate(current_tracks, start=start_idx + 1):
            content += f"{i}. {track['title']} - {track['artist']}\n"
        return content
    
    async def update_message(self, interaction):
        content = self.get_current_page_content()
        await interaction.response.edit_message(content=content, view=self) 