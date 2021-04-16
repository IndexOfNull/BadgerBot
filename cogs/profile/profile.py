import discord
from discord.ext import commands

from .widgets import BadgeWidget, DateJoinedWidget, AccountAgeWidget
from .renderer import RenderManager
from .themes import BasicTheme

from utils import checks, funcs
from utils.funcs import emoji_escape, emoji_format

import re

from io import BytesIO

#TODO: Move this into the profile widget (modularity if possible)
#TODO: Stop using name_to_id in favor of name_to_badge (maybe try with statements?)
class ProfileCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.manager = RenderManager(self.bot.db, create_tables=bot.create_tables)
        self.badger = self.manager.register_widget(BadgeWidget)
        self.manager.register_widget(DateJoinedWidget)
        self.manager.register_widget(AccountAgeWidget)
        self.maintheme = self.manager.register_theme(BasicTheme)
        #Refactor todo: find a way to get levelingwidget setup on load
        self.badge_limits = {
            "name": 32,
            "description": 175,
            "icon": 55,
            "serverbadges": 80,
            "levels": 200 #Is compared with absolute value (+ or - 200)
        }

    def make_badge_list(self, badge_entries, *, line="{0.icon} **{0.name}**{1} {0.description}\n", header="", footer=""):
        if len(header) > 0: header += "\n"
        if len(footer) > 0: footer += "\n"
        finalstr = "" #Could use a localization string
        for row in badge_entries:
            if row.levels > 0:
                finalstr += line.format(row, ((" [**" + str(row.levels) + "**]") if row.levels else "") + (":" if row.description else ""))
            else:
                finalstr += line.format(row, (":" if row.description else ""))
        return header + finalstr + footer

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
                    await ctx.send_response('badge_awarded', user, badge)
                else:
                    await ctx.send_response('badge_error', "awarding")
            else:
                await ctx.send_response('badge_hasbadge')
        else:
            await ctx.send_response('badge_notfound')

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
                    await ctx.send_response('badge_error', "awarding")
                    return
            else:
                await ctx.send_response('badge_multihasbadge')
                return
            #We'll just say they all got the badge if they already had it to avoid confusion
            mentions = ", ".join([user.mention for user in users])
            await ctx.send_response('badge_multiaward', mentions, badge)
        else:
            await ctx.send_response('badge_notfound')

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
                    await ctx.send_response('badge_error', "revoking")
                    return
            else:
                await ctx.send_response('badge_multinothasbadge')
                return
            mentions = ", ".join([user.mention for user in users])
            await ctx.send_response('badge_multirevoke', mentions, badge)
        else:
            await ctx.send_response('badge_notfound')

    @commands.command(aliases = ['stripall'])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    @funcs.require_confirmation(warning="This will strip the user of all their badges! There is no easy way of undoing this!")
    async def revokeall(self, ctx, user:discord.User):
        result = self.badger.revoke_all(ctx.guild.id, user.id) #result is the number of badges
        if result > 0:
            await ctx.send_response('badge_revokeall', user, result)
        else:
            await ctx.send_response('badge_revokeallnone', user)

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
                await ctx.send_response('badge_badgenuke', badge, result)
            else:
                await ctx.send_response('badge_badgenukenone')
        else:
            await ctx.send_response('badge_notfound')

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
                    await ctx.send_response('badge_revoked', user, badge)
                else:
                    await ctx.send_response('badge_error', "revoking")
            else:
                await ctx.send_response('badge_nothasbadge')
        else:
            await ctx.send_response('badge_notfound')

    @commands.command(aliases = ["addbadge", "makebadge"])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def createbadge(self, ctx, name:str, icon:emoji_escape, *, description:str=""):
        #Impose some limits on the parameters
        if len(name) > self.badge_limits['name']:
            await ctx.send_response('badge_limits', 'name', self.badge_limits['name'])
            return
        if len(description) > self.badge_limits['description']:
            await ctx.send_response('badge_limits', 'description', self.badge_limits['description'])
            return
        if len(icon) > self.badge_limits['icon']:
            await ctx.send_response('badge_limits', 'icon', self.badge_limits['icon'])
            return
        badge_exists = self.badger.name_to_id(ctx.guild.id, name)
        if not badge_exists: #This should be None if there is no row matching our criteria
            badge_count = self.badger.get_badge_entries(server_id=ctx.guild.id).count()
            if badge_count < self.badge_limits['serverbadges']: #Limit badges
                result = self.badger.create_badge(ctx.guild.id, name, icon, description=description)
                if result:
                    await ctx.send_response('badge_created')
                else:
                    await ctx.send_response('badge_error', "creating")
            else:
                await ctx.send_response('badge_maxbadgeslimit')
        else:
            await ctx.send_response('badge_exists')

    @commands.command()
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def badgewizard(self, ctx):
        badge_count = self.badger.get_badge_entries(server_id=ctx.guild.id).count()
        if badge_count > self.badge_limits['serverbadges']:
            await ctx.send_response('badge_maxbadgeslimit')
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
                await ctx.send_response('badge_exists')
                return
            msgs.append(await ctx.send(strs['icon'].format(self.badge_limits['icon'])))
            while not icon: #get the icon
                message = await self.bot.wait_for("message", check=message_check, timeout=maxtime)
                if len(message.content) > self.badge_limits['icon']:
                    msgs.append(await ctx.send(maxmsg.format("icon", self.badge_limits['icon'])))
                    continue
                icon = emoji_escape(message.content)
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
                await ctx.send_response('badge_created')
            else:
                await ctx.send_response('badge_error', "creating")
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
            await ctx.send_response('badge_limits', 'name', self.badge_limits['name'])
            return
        if len(icon) > self.badge_limits['icon']:
            await ctx.send_response('badge_limits', 'icon', self.badge_limits['icon'])
            return
        if description:
            if len(description) > self.badge_limits['description']:
                await ctx.send_response('badge_limits', 'description', self.badge_limits['description'])
                return
        badge_exists = self.badger.name_to_id(ctx.guild.id, name)
        if badge_exists:
            args = {}
            if icon:
                args['icon'] = emoji_escape(icon)
            if description:
                args['description'] = ('' if description.lower() in ('none', 'nothing') else description)
            updated = self.badger.update_badge(ctx.guild.id, name, newname=newname, **args)
            if updated:
                await ctx.send_response('badge_updated')
            else:
                await ctx.send_response('badge_error', "updating")
        else:
            await ctx.send_response('badge_notfound')

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
                await ctx.send_response('zapped', name)
            else:
                await ctx.send_response('badge_error', "removing")
        else:
            await ctx.send_response('badge_notfound')

    @commands.command(aliases = ["listbadges", "listbadge", "badgeslist", "badgelist"])
    @commands.guild_only()
    @commands.cooldown(1, 3, type=commands.BucketType.channel)
    async def badges(self, ctx, page:int=1):
        server_badges = self.badger.get_badge_entries(server_id=ctx.guild.id)
        paginator = funcs.Paginator(server_badges, items_per_page=20)
        pc = paginator.page_count
        if pc == 0:
            await ctx.send_response('badge_nobadges')
            return
        page = funcs.clamp(page, 1, pc)
        page_list = paginator.get_page(page-1)
        page_header = "> Badges `|` (Page " + str(page) + " of " + str(pc) + ")" #Could use a localization string
        page_footer = "\n" + ctx.responses['page_strings']['footer'].format(ctx.prefix + ctx.invoked_with)
        finalstr = self.make_badge_list(page_list, header=page_header, footer=page_footer)
        if len(finalstr) > 2000: #This is a bit of jank hack, I know. But it's far more elegant than erroring and it lets server administrators fix the problem.
            f = discord.File(BytesIO(finalstr.encode("utf-8")), filename="badgelist-pg" + str(page) + ".txt")
            await ctx.send(ctx.responses['badgelist_toolarge'], file=f)
        else:
            await ctx.send(finalstr)
        
    @commands.command(aliases=['search'])
    @commands.guild_only()
    @commands.cooldown(1, 5, type=commands.BucketType.channel)
    async def badgesearch(self, ctx, *, search:str):
        max_results = 10
        results = self.badger.badge_search(ctx.guild.id, query=search).all()
        if not results:
            await ctx.send_response('badgesearch_noresults')
            return
        results = results[:max_results] #Truncate at 10 entries
        if len(results) == 1:
            badge = results[0]
            embed = discord.Embed(title="**" + badge.name + "**", type="rich", color=discord.Color.blue())
            embed.add_field(name="Icon", value=badge.icon)
            embed.add_field(name="Levels", value=str(badge.levels))
            if badge.description:
                embed.add_field(name="Description", value=badge.description, inline=False)

            custom_emoji_match = funcs.emoji_regex.match(badge.icon) #Matches the first, which is okay
            if custom_emoji_match:
                resolved_emoji = self.bot.get_emoji(int(custom_emoji_match.groups(0)[1]))
                if resolved_emoji:
                    embed.set_thumbnail(url=resolved_emoji.url)

            await ctx.send(embed=embed)
        else:
            header = "> Badges `|` (Showing {0} results for: {1})\n".format(max_results, search)
            finalstr = self.make_badge_list(results)
            finalstr = discord.utils.remove_markdown(finalstr)
            
            replace_re = re.compile(re.escape(search), re.IGNORECASE)
            finalstr = replace_re.sub(lambda x: "**" + x.group(0) + "**", finalstr)

            finalstr = header + finalstr
            await ctx.send(finalstr)

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 3, type=commands.BucketType.user)
    async def profile(self, ctx, *, user:discord.Member=None):
        if user is None:
            user = ctx.author
        if user.bot:
            await ctx.send_response('general_useronly')
            return
        e = self.maintheme.get_embed(ctx, user)
        await ctx.send(embed=e)

    @commands.command(aliases=["setlevel", "badgelevel", "setlevels", "badgelevels", "assignlevel"])
    @checks.is_admin()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    async def assignlevels(self, ctx, badge:str, levels:int):
        if abs(levels) > self.badge_limits['levels']:
            await ctx.send_response('badgelevels_limit', self.badge_limits['levels'])
            return
        badge_id = self.badger.name_to_id(ctx.guild.id, badge)
        if not badge_id:
            await ctx.send_response('badge_notfound')
            return
        self.badger.set_badge_levels(ctx.guild.id, badge_id, levels)
        if levels == 0:
            await ctx.send_response('badgelevels_remove', badge)
        else:
            await ctx.send_response('badgelevels_set', badge, levels)

    @commands.command()
    @checks.is_mod()
    @commands.cooldown(1, 3, type=commands.BucketType.channel)
    async def hasbadge(self, ctx, user:discord.Member, *, badge:str):
        badge_id = self.badger.name_to_id(ctx.guild.id, badge)
        if badge_id: #If we got a valid id
            result = self.badger.user_has_badge(ctx.guild.id, user.id, badge_id)
            if result:
                await ctx.send_response('badge_userhasbadge')
            else:
                await ctx.send_response('badge_usernohasbadge')
        else:
            await ctx.send_response('badge_notfound')

    @commands.command()
    @checks.is_mod()
    @commands.cooldown(1, 3, type=commands.BucketType.guild)
    async def usersearch(self, ctx, page_num:int, *, badge:str): #This is bad command syntax. I should fix this with stateful paging
        resolved_badge = self.badger.name_to_badge(ctx.guild.id, badge)
        if resolved_badge: #If we got a valid id
            results = self.badger.get_award_entries(server_id=ctx.guild.id, badge_id=resolved_badge.id)
            pager = funcs.Paginator(results)
            clamped_page_num = funcs.clamp(page_num, 1, pager.page_count)
            page = pager.get_page(clamped_page_num - 1)

            header = "```md\n> {0}\n================\n".format( ctx.get_response('badgesearch.header').format(resolved_badge.name, clamped_page_num, pager.page_count, pager.item_count) )
            footer = "\n```"
            
            final = ""
            for i, winner in enumerate([x.BadgeWinner for x in page]): #Just get the BadgeWinner entries, this feels hacky
                resolved_user = self.bot.get_user(winner.discord_id)
                final += str(i + 1) + ": "
                if not resolved_user:
                    final += ctx.get_response('badgesearch.unkown_user').format(winner.discord_id) + "\n"
                else:
                    final += str(resolved_user) + "\n"

            final = header + final + footer
            await ctx.send(final)
        else:
            await ctx.send_response('badge_notfound')

    @commands.command()
    @commands.cooldown(1, 10, type=commands.BucketType.channel)
    async def leaderboard(self, ctx, page:int=1):
        lbd = self.badger.get_server_leaderboard(ctx.guild.id)
        pager = funcs.Paginator(lbd, items_per_page=10)
        page = funcs.clamp(page, 1, pager.page_count) #Clamp page so that we can't pick a page past the last page
        rows = pager.get_page(page-1) #Subtract one for computer friendliness
        header = "```md\n> {0}\n================\n".format( ctx.get_response('leaderboard.header').format(page, pager.page_count) )
        footer = "\n```"
        entry = "<{num}: {user}> {levels} levels\n"
        final = header
        for position, row in enumerate(rows):
            user = self.bot.get_user(row.discord_id)
            if not user:
                u = ctx.get_response('leaderboard.unknown_user').format(row.discord_id)
            else:
                u = str(user)
            final += entry.format(num=position + (page-1)*pager.items_per_page + 1, user=u, levels=row.levels)
        if final == header:
            final += ctx.get_response('nothing_here')
        final.rstrip()
        final += footer
        await ctx.send(final)

    @commands.command()
    async def emoji(self, ctx, *, emoji:discord.Emoji):
        emoji_str = "<:{0}:{1}>".format(emoji.name, emoji.id)
        title = ("Emoji Info " + emoji_str) if emoji.is_usable() else "Emoji Info"
        embed = discord.Embed(title=title, type="Rich", color=discord.Color.blue())
        embed.set_thumbnail(url=emoji.url)
        embed.add_field(name="Name", value=emoji.name)
        embed.add_field(name="ID", value=emoji.id)
        embed.add_field(name="Non-Nitro Copy-Paste (For badge creation)", value="`" + emoji_format(emoji_str) + "`", inline=False)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(ProfileCog(bot))