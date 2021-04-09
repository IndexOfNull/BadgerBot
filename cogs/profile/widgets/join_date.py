from .base import WidgetBase
import discord

class DateJoinedWidget(WidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.embed_only = True

    def handle_embed(self, ctx, user, embed):
        if not isinstance(user, discord.Member): #If we don't have a member object
            return
        t = user.joined_at
        if t: #user.joined_at can sometimes return None
            converted_time = t.strftime('%Y-%m-%d %H:%M:%S') + " UTC"
            embed.add_field(name="Date Joined", value=converted_time)
