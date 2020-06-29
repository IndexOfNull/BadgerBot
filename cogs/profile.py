import discord
from discord.ext import commands
import asyncio

from cogs.widget.widgets import BadgeWidget, DateJoinedWidget, AccountAgeWidget
from cogs.widget.classes import RenderManager
from cogs.widget import themes
from utils import checks, funcs

from io import BytesIO

#This is super hacky
import sqlalchemy as sa
try:
    from cogs.leveling import BadgeLevelEntry
    ble = BadgeLevelEntry
except:
    ble = None

try:
    from cogs.widget.widgets import BadgeEntry
    be = BadgeEntry
except:
    be = None

class ProfileCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.manager = RenderManager(self.bot.db, create_tables=bot.create_tables)
        self.badger = self.manager.register_widget(BadgeWidget)
        self.manager.register_widget(DateJoinedWidget)
        self.manager.register_widget(AccountAgeWidget)
        self.maintheme = self.manager.register_theme(themes.MainTheme)
        self.levelingwidget = None
        self.badge_limits = {
            "name": 32,
            "description": 175,
            "icon": 55,
            "serverbadges": 80
        }

    @commands.command(aliases = ['givebadge', 'give'])
    @commands.guild_only()
    @checks.is_mod()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
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

    @commands.command(aliases = ['awardmu', 'multiaward'])
    @commands.guild_only()
    @checks.is_mod()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    async def awardmultiuser(self, ctx, badge:str, *users:discord.Member):
        badgeid = self.badger.name_to_id(ctx.guild.id, badge)
        if badgeid:
            badge_statuses = self.badger.users_have_badge(ctx.guild.id, [user.id for user in users], badgeid)
            award_ids = [user for user in badge_statuses.keys() if badge_statuses[user] is False] #Just get the false values
            if award_ids:
                result = self.badger.award_badge(ctx.guild.id, award_ids, badgeid)
                if not result:
                    await ctx.send(ctx.responses['badge_error'].format("awarding"))
                    return
            else:
                await ctx.send(ctx.responses['badge_multihasbadge'])
                return
            #We'll just say they all got the badge if they already had it to avoid confusion
            mentions = ", ".join([user.mention for user in users])
            await ctx.send(ctx.responses['badge_multiaward'].format(mentions, badge))
        else:
            await ctx.send(ctx.responses['badge_notfound'])

    @commands.command(aliases = ['revokemu', 'multirevoke'])
    @commands.guild_only()
    @checks.is_mod()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    async def revokemultiuser(self, ctx, badge:str, *users:discord.Member):
        badgeid = self.badger.name_to_id(ctx.guild.id, badge)
        if badgeid:
            badge_statuses = self.badger.users_have_badge(ctx.guild.id, [user.id for user in users], badgeid)
            revoke_ids = [user for user in badge_statuses.keys() if badge_statuses[user] is True]
            if revoke_ids:
                result = self.badger.revoke_badge(ctx.guild.id, revoke_ids, badgeid)
                if not result:
                    await ctx.send(ctx.responses['badge_error'].format("revoking"))
                    return
            else:
                await ctx.send(ctx.responses['badge_multinothasbadge'])
                return
            mentions = ", ".join([user.mention for user in users])
            await ctx.send(ctx.responses['badge_multirevoke'].format(mentions, badge))
        else:
            await ctx.send(ctx.responses['badge_notfound'])

    @commands.command(aliases = ['stripall'])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    @funcs.require_confirmation(warning="This will strip the user of all their badges! There is no easy way of undoing this!")
    async def revokeall(self, ctx, user:discord.Member):
        result = self.badger.revoke_all(ctx.guild.id, user.id) #result is the number of badges
        if result > 0:
            await ctx.send(ctx.responses['badge_revokeall'].format(user, result))
        else:
            await ctx.send(ctx.responses['badge_revokeallnone'].format(user))

    @commands.command(aliases = ['badgenuke'])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    @funcs.require_confirmation(warning="All users will lose this badge! There is no easy way of undoing this!")
    @funcs.require_confirmation(warning="Are you sure? This is your last chance.") #lol
    async def revokefromall(self, ctx, badge:str):
        badgeid = self.badger.name_to_id(ctx.guild.id, badge)
        if badgeid:
            result = self.badger.revoke_from_all(ctx.guild.id, badgeid)
            if result > 0:
                await ctx.send(ctx.responses['badge_badgenuke'].format(badge, result))
            else:
                await ctx.send(ctx.responses['badge_badgenukenone'])
        else:
            await ctx.send(ctx.responses['badge_notfound'])

    @commands.command(aliases = ['strip'])
    @commands.guild_only()
    @checks.is_mod()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
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

    @commands.command(aliases = ["addbadge", "makebadge"])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def createbadge(self, ctx, name:str, icon:str, *, description:str=""):
        #Impose some limits on the parameters
        if len(name) > self.badge_limits['name']:
            await ctx.send(ctx.responses['badge_limits'].format("name", self.badge_limits['name']))
            return
        if len(description) > self.badge_limits['description']:
            await ctx.send(ctx.responses['badge_limits'].format("description", self.badge_limits['description']))
            return
        if len(icon) > self.badge_limits['icon']:
            await ctx.send(ctx.responses['badge_limits'].format("icon", self.badge_limits['icon']))
            return
        badge_exists = self.badger.name_to_id(ctx.guild.id, name)
        if not badge_exists: #This should be None if there is no row matching our criteria
            badge_count = self.badger.get_server_badges(ctx.guild.id).count()
            if badge_count < self.badge_limits['serverbadges']: #Limit badges
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
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def badgewizard(self, ctx):

        badge_count = self.badger.get_server_badges(ctx.guild.id).count()
        if badge_count > self.badge_limits['serverbadges']:
            await ctx.send(ctx.responses['badge_maxbadgeslimit'])
            return
        strs = ctx.responses['badgewizard_strings']
        maxmsg = strs['limit']
        maxtime = 30 #Max time per prompt
        msgs = []
        try:
            msgs.append(await ctx.send(strs['start'].format(maxtime) + "\n" + strs['name'].format(self.badge_limits['name'])))
            name = icon = description = None

            def message_check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            while not name: #get the name
                message = await self.bot.wait_for("message", check=message_check, timeout=maxtime)
                if len(message.content) > self.badge_limits['name']:
                    msgs.append(await ctx.send(maxmsg.format("name", self.badge_limits['name'])))
                    continue
                name = message.content
            badge_exists = self.badger.name_to_id(ctx.guild.id, name)
            if badge_exists:
                await ctx.send(ctx.responses['badge_exists'])
                return
            msgs.append(await ctx.send(strs['icon'].format(self.badge_limits['icon'])))
            while not icon: #get the icon
                message = await self.bot.wait_for("message", check=message_check, timeout=maxtime)
                if len(message.content) > self.badge_limits['icon']:
                    msgs.append(await ctx.send(maxmsg.format("icon", self.badge_limits['icon'])))
                    continue
                icon = message.content
            msgs.append(await ctx.send(strs['description'].format(self.badge_limits['description'])))
            while not description: #get the description
                msg = await self.bot.wait_for("message", check=message_check, timeout=maxtime)
                if msg.content.lower() in ("none", "blank"):
                    description = ""
                    break
                if len(msg.content) > self.badge_limits['description']:
                    msgs.append(await ctx.send(maxmsg.format("description", self.badge_limits['description'])))
                    continue
                description = msg.content
            if not self.levelingwidget: #detect the leveling widget
                self.levelingwidget = self.manager.get_widget("LevelWidget")
            levels = None
            if self.levelingwidget: #ask for levels if we find the leveling widget
                msgs.append(await ctx.send(strs['levels']))
                message = await self.bot.wait_for("message", check=message_check, timeout=maxtime)
                if not message.content.lower() in ("0", "blank", "none"):
                    try:
                        levels = int(message.content)
                    except:
                        pass
            result = self.badger.create_badge(ctx.guild.id, name, icon, description=description)
            if levels:
                self.levelingwidget.assign_levels(ctx.guild.id, result.id, levels)
            if result:
                await ctx.send(ctx.responses['badge_created'])
            else:
                await ctx.send(ctx.responses['badge_error'].format("creating"))
            await ctx.channel.delete_messages(msgs)
        except Exception as e:
            raise e

    @commands.command(aliases=["editbadge", "modifybadge"])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def updatebadge(self, ctx, name:str, newname:str, icon:str=None, *, description:str=None):
        #Impose some limits on the parameters
        if len(name) > self.badge_limits['name']:
            await ctx.send(ctx.responses['badge_limits'].format("name", self.badge_limits['name']))
            return
        if len(icon) > self.badge_limits['icon']:
            await ctx.send(ctx.responses['badge_limits'].format("icon", self.badge_limits['icon']))
            return
        if description:
            if len(description) > self.badge_limits['description']:
                await ctx.send(ctx.responses['badge_limits'].format("description", self.badge_limits['description']))
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
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    @funcs.require_confirmation(warning="All users with this badge will be stripped of it. There is no undoing this!") #Localization support would be nice here
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
    @commands.cooldown(1, 5, type=commands.BucketType.channel)
    async def badges(self, ctx, page:int=1):
        if not self.levelingwidget:
            self.levelingwidget = self.manager.get_widget("LevelWidget")
        page -= 1 #So that we can be comfy while the user is
        if page < 0: #Make it so they can't go lower than 0
            page = 0
        if ble and be and self.levelingwidget:
            server_badges = self.bot.db.query(BadgeEntry, BadgeLevelEntry.levels)\
                .filter_by(server_id=ctx.guild.id)\
                .outerjoin(BadgeLevelEntry, BadgeEntry.id == BadgeLevelEntry.badge_id)
        else:
            server_badges = self.badger.get_server_badges(ctx.guild.id)
        paginator = funcs.Paginator(server_badges, items_per_page=10)
        pc = paginator.page_count
        if pc == 0:
            await ctx.send(ctx.responses['badge_nobadges'])
            return
        if page + 1 > pc:
            page = pc - 1 #Cap the pages argument to the actual amount of pages
        line = "{0.text} **{0.name}**{1} {0.description}\n"
        finalstr = "> Badges `|` (Page " + str(page+1) + " of " + str(pc) + ")\n" #Could use a localization string
        page_list = paginator.get_page(page)
        for row in page_list:
            if ble and be and self.levelingwidget: #This could be optimized by making two for loops inside an if statement instead of this way
                finalstr += line.format(row.BadgeEntry, ((" [**" + str(row.levels) + "**]") if row.levels else "") + (":" if row.BadgeEntry.description else ""))
            else:
                finalstr += line.format(row, (":" if row.description else ""))
        finalstr += "\n" + ctx.responses['page_strings']['footer'].format(ctx.prefix + ctx.invoked_with)
        if len(finalstr) > 2000: #This is a bit of jank hack, I know. But it's far more elegant than erroring and it lets server administrators fix the problem.
            f = discord.File(BytesIO(finalstr.encode("utf-8")), filename="badgelist-pg" + str(page) + ".txt")
            await ctx.send(ctx.responses['badgelist_toolarge'], file=f)
        else:
            await ctx.send(finalstr)
        
    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 3, type=commands.BucketType.user)
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