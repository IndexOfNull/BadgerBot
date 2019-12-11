import discord
from discord.ext import commands

from mods.widget.badge import BadgeWidget
from mods.widget.classes import RenderManager
from utils import checks

class ProfileCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.manager = RenderManager(self.bot.db, create_tables=bot.create_tables)
        self.badger = self.manager.register_widget(BadgeWidget)

    @commands.command(aliases = ['givebadge', 'give'])
    @commands.guild_only()
    @checks.is_mod()
    async def award(self, ctx, user:discord.Member, badge:str):
        badgeid = self.badger.name_to_id(ctx.guild.id, badge)
        if badgeid:
            has_badge = self.badger.user_has_badge(ctx.guild.id, user.id, badgeid)
            if not has_badge:
                result = self.badger.award_badge(ctx.guild.id, user.id, badgeid)
                if result:
                    await ctx.send(":military_medal: " + user.mention + " has been awarded the \"" + badge + "\" badge.")
                else:
                    await ctx.send(":neutral_face: Something went wrong while awarding the badge.")
            else:
                await ctx.send(":red_circle: That user already has that badge.")
        else:
            await ctx.send(":grey_question: There doesn't appear to be a badge with that name.")

    @commands.command(aliases = ['strip'])
    @commands.guild_only()
    @checks.is_mod()
    async def revoke(self, ctx, user:discord.Member, badge):
        badgeid = self.badger.name_to_id(ctx.guild.id, badge)
        if badgeid:
            has_badge = self.badger.user_has_badge(ctx.guild.id, user.id, badgeid)
            if has_badge:
                result = self.badger.revoke_badge(ctx.guild.id, user.id, badgeid)
                if result:
                    await ctx.send(":cloud_lightning: " + user.mention + " has been stripped of their \"" + badge + "\" badge.")
                else:
                    await ctx.send(":neutral_face: Something went wrong while revoking the badge.")
            else:
                await ctx.send(":red_circle: That user doesn't have that badge.")
        else:
            await ctx.send(":grey_question: There doesn't appear to be a badge with that name.")

    @commands.command(aliases = ["addbadge"])
    @commands.guild_only()
    @checks.is_admin()
    async def createbadge(self, ctx, name:str, icon:str, *, description:str=""):
        #Impose some limits on the parameters
        if len(name) > 32:
            await ctx.send(":red_circle: The name for your badge is more than 32 characters. Please shorten it.")
            return
        if len(icon) > 32:
            await ctx.send(":red_circle: The icon for your badge is more than 32 characters. Please shorten it")
            return
        if len(description) > 175:
            await ctx.send(":red_circle: The description for your badge is more than 175 characters. Please shorten it.")
            return
        badge_exists = self.badger.name_to_id(ctx.guild.id, name)
        if not badge_exists: #This should be None if there is no row matching our criteria
            badge_count = self.badger.get_server_badges(ctx.guild.id).count()
            if badge_count < 50: #Limit badges to 50
                result = self.badger.create_badge(ctx.guild.id, name, icon, description=description)
                if result:
                    await ctx.send(":shield: Your badge has been created!")
                else:
                    await ctx.send(":neutral_face: Something went wrong while trying to create your badge.")
            else:
                await ctx.send(":compression: You can only have up to 50 badges on your server.")
        else:
            await ctx.send(":red_circle: That badge already exists!")

    @commands.command(aliases = ["removebadge", "rembadge", "delbadge", "rmbadge"])
    @commands.guild_only()
    @checks.is_admin()
    async def deletebadge(self, ctx, *, name:str):
        badgeid = self.badger.name_to_id(ctx.guild.id, name)
        if badgeid: #If we got a valid id
            result = self.badger.remove_badge(ctx.guild.id, badgeid)
            if result:
                await ctx.send(":sob: Goodbye, " + name)
            else:
                await ctx.send(":neutral_face: Something went wrong while trying to remove your badge.")
        else:
            await ctx.send(":grey_question: There doesn't appear to be a badge with that name.")

    @commands.command(aliases = ["listbadges", "listbadge", "badgeslist", "badgelist"])
    @commands.guild_only()
    async def badges(self, ctx):
        line = "{0.text} **{0.name}**: {0.description}\n"
        finalstr = "> __Badges__\n"
        server_badges = self.badger.get_server_badges(ctx.guild.id)
        count = 0
        for row in server_badges:
            count += 1
            finalstr += line.format(row)
        if count == 0:
            finalstr = ":white_sun_small_cloud: This server has no badges."
        await ctx.send(finalstr)

    #Maybe add an update command down the line.

def setup(bot):
    bot.add_cog(ProfileCog(bot))