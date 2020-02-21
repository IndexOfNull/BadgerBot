from mods.widget import classes
import discord

class MainTheme(classes.ThemeBase):

    def get_embed(self, ctx, user):
        embed = discord.Embed(title=user.name + "#" + user.discriminator, type="rich", color=discord.Color.light_grey())
        avatar_url = user.avatar_url_as(static_format='png', size=1024)
        embed.set_author(name="User Profile")
        embed.set_thumbnail(url=avatar_url)
        for widget in self.render_manager.widgets:
            widget.handle_embed(ctx, user, embed)
        return embed