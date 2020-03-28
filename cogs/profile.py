import discord
from discord.ext import commands

from cogs.widget.widgets import BadgeWidget, DateJoinedWidget, AccountAgeWidget
from cogs.widget.classes import RenderManager
from cogs.widget import themes
from utils import checks, funcs

class ProfileCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.manager = RenderManager(self.bot.db, create_tables=bot.create_tables)
        self.badger = self.manager.register_widget(BadgeWidget)
        self.manager.register_widget(DateJoinedWidget)
        self.manager.register_widget(AccountAgeWidget)
        self.maintheme = self.manager.register_theme(themes.MainTheme)

    @commands.command(aliases = ['givebadge', 'give'])
    @commands.guild_only()
    @checks.is_mod()
    async def award(self, ctx, user:discord.Member, *, badge:str):
        badgeid = self.badger.name_to_id(ctx.guild.id, badge)
        if badgeid:
            has_badge = self.badger.user_has_badge(ctx.guild.id, user.id, badgeid)
            if not has_badge:
                result = self.badger.award_badge(ctx.guild.id, user.id, badgeid)
                if result:
                    await ctx.send(ctx.responses['badge_awarded'].format(user, badge))
                else:
                    await ctx.send(ctx.responses['badge_error'].format("awarding"))
            else:
                await ctx.send(ctx.responses['badge_hasbadge'])
        else:
            await ctx.send(ctx.responses['badge_notfound'])

    @commands.command(aliases = ['strip'])
    @commands.guild_only()
    @checks.is_mod()
    async def revoke(self, ctx, user:discord.Member, *, badge:str):
        badgeid = self.badger.name_to_id(ctx.guild.id, badge)
        if badgeid:
            has_badge = self.badger.user_has_badge(ctx.guild.id, user.id, badgeid)
            if has_badge:
                result = self.badger.revoke_badge(ctx.guild.id, user.id, badgeid)
                if result:
                    await ctx.send(ctx.responses['badge_revoked'].format(user, badge))
                else:
                    await ctx.send(ctx.responses['badge_error'].format("revoking"))
            else:
                await ctx.send(ctx.responses['badge_nothasbadge'])
        else:
            await ctx.send(ctx.responses['badge_notfound'])

    @commands.command(aliases = ["addbadge"])
    @commands.guild_only()
    @checks.is_admin()
    async def createbadge(self, ctx, name:str, icon:str, *, description:str=""):
        #Impose some limits on the parameters
        if len(name) > 32:
            await ctx.send(ctx.responses['badge_limits'].format("name", 32))
            return
        if len(description) > 175:
            await ctx.send(ctx.responses['badge_limits'].format("description", 175))
            return
        badge_exists = self.badger.name_to_id(ctx.guild.id, name)
        if not badge_exists: #This should be None if there is no row matching our criteria
            badge_count = self.badger.get_server_badges(ctx.guild.id).count()
            if badge_count < 80: #Limit badges to 80
                result = self.badger.create_badge(ctx.guild.id, name, icon, description=description)
                if result:
                    await ctx.send(ctx.responses['badge_created'])
                else:
                    await ctx.send(ctx.responses['badge_error'].format("creating"))
            else:
                await ctx.send(ctx.responses['badge_maxbadgeslimit'])
        else:
            await ctx.send(ctx.responses['badge_exists'])

    @commands.command()
    @commands.guild_only()
    @checks.is_admin()
    async def updatebadge(self, ctx, name:str, newname:str, icon:str=None, *, description:str=None):
        #Impose some limits on the parameters
        if len(name) > 32:
            await ctx.send(ctx.responses['badge_limits'].format("name", 32))
            return
        if description:
            if len(description) > 175:
                await ctx.send(ctx.responses['badge_limits'].format("description", 175))
                return
        badge_exists = self.badger.name_to_id(ctx.guild.id, name)
        if badge_exists:
            args = {}
            if icon:
                args['text'] = icon
            if description:
                args['description'] = description
            updated = self.badger.update_badge(ctx.guild.id, name, newname=newname, **args)
            if updated:
                await ctx.send(ctx.responses['badge_updated'])
            else:
                await ctx.send(ctx.responses['badge_error'].format("updating"))
        else:
            await ctx.send(ctx.responses['badge_notfound'])

    @commands.command(aliases = ["removebadge", "rembadge", "delbadge", "rmbadge"])
    @commands.guild_only()
    @checks.is_admin()
    @funcs.require_confirmation()
    async def deletebadge(self, ctx, *, name:str):
        badgeid = self.badger.name_to_id(ctx.guild.id, name)
        if badgeid: #If we got a valid id
            result = self.badger.remove_badge(ctx.guild.id, badgeid)
            if result:
                await ctx.send(ctx.responses['zapped'].format(name))
            else:
                await ctx.send(ctx.responses['badge_error'].format("removing"))
        else:
            await ctx.send(ctx.responses['badge_notfound'])

    @commands.command(aliases = ["listbadges", "listbadge", "badgeslist", "badgelist"])
    @commands.guild_only()
    async def badges(self, ctx):
        line = "{0.text} **{0.name}**{1} {0.description}\n"
        finalstr = "> __Badges__\n"
        server_badges = self.badger.get_server_badges(ctx.guild.id)
        count = 0
        for row in server_badges:
            count += 1
            finalstr += line.format(row, (":" if row.description else ""))
        if count == 0:
            finalstr = ctx.responses['badge_nobadges']
        await ctx.send(finalstr)

    @commands.command()
    @commands.guild_only()
    async def profile(self, ctx, *, user:discord.Member=None):
        if user is None:
            user = ctx.author
        if user.bot:
            await ctx.send(ctx.responses['general_useronly'])
            return
        e = self.maintheme.get_embed(ctx, user)
        await ctx.send(embed=e)

def setup(bot):
    bot.add_cog(ProfileCog(bot))