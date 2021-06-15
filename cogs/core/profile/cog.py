import discord
from discord.ext import commands

from utils import checks, funcs, pagination, http
from utils.funcs import emoji_escape

import re
from io import BytesIO
from PIL import Image
from urllib.parse import urlparse

from .data import badges, profilecards
from . import imager

class ProfileCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.badger = badges.BadgeManager(self.bot.db)
        self.profile_carder = profilecards.ProfileCardManager(self.bot.db)
        self.badge_limits = {
            "name": 32,
            "description": 175,
            "icon": 55,
            "serverbadges": 80,
            "levels": 200 #Is compared with absolute value (+ or - 200)
        }
        self.background_limits = {
            "name": 32,
            "description": 175,
            "domains": ["i.imgur.com", "cdn.discordapp.com"], #everything after subdomain (does not support subdomains with . in them)
            "max_backgrounds": 15,
            "max_bytes": 2048000, #one MiB
            "max_size": (2000, 2000),
            "max_dl_time": 5, #how long before timing out a download (protects against bait-and-switch attacks)
            "mimes": ["image/png", "image/jpeg"]
        }

    def make_badge_list(self, badge_entries, *, line="{0.icon} **{0.name}**{1} {0.description}\n", header="", footer=""):
        if len(header) > 0: header += "\n"
        if len(footer) > 0: 
            footer = "\n" + footer
        finalstr = "" #Could use a localization string
        for row in badge_entries:
            if row.levels > 0:
                finalstr += line.format(row, ((" [**" + str(row.levels) + "**]") if row.levels else "") + (":" if row.description else ""))
            else:
                finalstr += line.format(row, (":" if row.description else ""))
        return header + finalstr + footer

    def make_background_list(self, background_entries, *, line="\> **{0.name}**{1} {0.description}\n", header="", footer=""):
        if len(header) > 0: header += "\n"
        if len(footer) > 0: 
            footer = "\n" + footer
        finalstr = ""
        for row in background_entries:
            finalstr += line.format(row, (":" if row.description else ""))
        return header + finalstr + footer

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 5, type=commands.BucketType.user)
    async def profile2(self, ctx, *, user:discord.Member=None):
        if user is None:
            user = ctx.author
        badges = self.badger.get_award_entries(server_id=ctx.guild.id, discord_id=user.id).all()
        prefs = self.profile_carder.get_preferences(ctx.guild.id, user.id)
        bg_url = None
        spotlight = None
        if prefs:
            bg_url = prefs.background.image_url if prefs.background else None
            spotlight = prefs.spotlighted_badge if prefs.spotlighted_badge else None
        img = await imager.make_profile_card(user, badges=badges, bg_url=bg_url, spotlight=spotlight)
        img.show()

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 3, type=commands.BucketType.user)
    async def profile(self, ctx, *, user:discord.Member=None):
        if user is None:
            user = ctx.author

        embed = discord.Embed(title=user.name + "#" + user.discriminator, type="rich", color=user.color)
        avatar_url = user.avatar_url_as(static_format='png', size=1024)
        embed.set_author(name="User Profile")
        embed.set_thumbnail(url=avatar_url)

        #Badges and level
        ubadges = self.badger.get_award_entries(server_id=ctx.guild.id, discord_id=user.id).all()
        icons = " ".join([x.BadgeEntry.icon for x in ubadges]).strip()
        level = sum([x.BadgeEntry.levels for x in ubadges])
        icons = icons if icons else "No Badges"
        embed.add_field(name="Badges [" + str(len(ubadges)) + "]", value=icons, inline=False)
        if level > 0:
            embed.add_field(name="Level", value=str(level), inline=True)

        t = user.joined_at
        if t: #user.joined_at can sometimes return None
            converted_time = t.strftime('%Y-%m-%d %H:%M:%S') + " UTC"
            embed.add_field(name="Date Joined", value=converted_time)

        t = user.created_at
        if t: #user.created_at can sometimes return None
            converted_time = t.strftime('%Y-%m-%d %H:%M:%S') + " UTC"
            embed.add_field(name="Account Created", value=converted_time)

        await ctx.send(embed=embed)

    @commands.command(aliases = ['givebadge', 'give'])
    @commands.guild_only()
    @checks.is_mod()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    async def award(self, ctx, user:discord.Member, *, badge:str):
        resolved_badge = self.badger.name_to_badge(ctx.guild.id, badge)
        if resolved_badge:
            badgeid = resolved_badge.id
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

    @commands.command(aliases = ['awardmu'])
    @commands.guild_only()
    @checks.is_mod()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    async def awardmultiuser(self, ctx, badge:str, *users:discord.Member):
        resolved_badge = self.badger.name_to_badge(ctx.guild.id, badge)
        if resolved_badge:
            badgeid = resolved_badge.id
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

    @commands.command(aliases = ['awardmb'])
    @commands.guild_only()
    @checks.is_mod()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    async def awardmultibadge(self, ctx, user:discord.Member, *badges:str):
        #Figure out what badges we want to give and every badge we already have
        resolved_badges = self.badger.names_to_badges(ctx.guild.id, badges)
        resolved_ids = [badge.id for badge in resolved_badges]
        user_badges = self.badger.get_award_entries(discord_id=user.id, server_id=ctx.guild.id).all()
        user_badges_ids = set([x.BadgeEntry.id for x in user_badges])

        #Use the previous information to figure out what badges the user already has
        #Doing it this way allows us to get a list without duplicates (e.g. the user was awarded the same badge twice; compatibility)
        already_awarded = self.badger.get_badge_entries(server_id=ctx.guild.id).filter(data.BadgeEntry.id.in_(user_badges_ids)).all()
        already_awarded_ids = [x.id for x in already_awarded]
        ids_set = set(resolved_ids)
        to_award = ids_set.difference(set(already_awarded_ids)) #See what they don't have

        self.badger.award_multibadge(ctx.guild.id, user.id, to_award) #Give them what they don't have

        awarded_badges = [x for x in resolved_badges if x.id in to_award] #Get the badge objects that we game them
        unawarded_badges = [x for x in resolved_badges if x.id not in to_award] #The same but what we didn't give them
        
        #Final message formatting
        final = ""
        if len(resolved_badges) != len(badges):
            final += ctx.get_response("badge_awardmb.skipped") + "\n"
        if len(awarded_badges) > 0:
            header = ctx.get_response('badge_awardmb.awarded').format(user)
            final = self.make_badge_list(awarded_badges, line="\\> {0.icon} **{0.name}**\n", header=header)
        if len(unawarded_badges) > 0:
            header = ctx.get_response('badge_awardmb.already_awarded')
            final += "\n" + self.make_badge_list(unawarded_badges, line="\\> {0.icon} **{0.name}**\n", header=header)
        await ctx.send(final.rstrip())

    @commands.command(aliases = ['revokemb'])
    @commands.guild_only()
    @checks.is_mod()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    async def revokemultibadge(self, ctx, user:discord.Member, *badges:str):
        #Figure out what badges we want to take and every badge we already have
        resolved_badges = self.badger.names_to_badges(ctx.guild.id, badges)
        resolved_ids = [badge.id for badge in resolved_badges]
        user_badges = self.badger.get_award_entries(discord_id=user.id, server_id=ctx.guild.id).all()
        user_badges_ids = set([x.BadgeEntry.id for x in user_badges])

        #Use the previous information to figure out what badges the user already has
        #Doing it this way allows us to get a list without duplicates (e.g. the user was awarded the same badge twice; compatibility)
        already_awarded = self.badger.get_badge_entries(server_id=ctx.guild.id).filter(data.BadgeEntry.id.in_(user_badges_ids)).all()
        already_awarded_ids = [x.id for x in already_awarded]
        ids_set = set(resolved_ids)
        to_revoke = ids_set.intersection(set(already_awarded_ids)) #See what they don't have

        self.badger.revoke_multibadge(ctx.guild.id, user.id, to_revoke) #Give them what they don't have

        revoked_badges = [x for x in resolved_badges if x.id in to_revoke] #Get the badge objects that we game them
        unrevoked_badges = [x for x in resolved_badges if x.id not in to_revoke] #The same but what we didn't give them
        
        #Final message formatting
        final = ""
        if len(resolved_badges) != len(badges):
            final += ctx.get_response("badge_revokemb.skipped") + "\n"
        if len(revoked_badges) > 0:
            header = ctx.get_response('badge_revokemb.revoked').format(user)
            final = self.make_badge_list(revoked_badges, line="\\> {0.icon} **{0.name}**\n", header=header)
        if len(unrevoked_badges) > 0:
            header = ctx.get_response('badge_revokemb.not_revoked')
            final += "\n" + self.make_badge_list(unrevoked_badges, line="\\> {0.icon} **{0.name}**\n", header=header)
        await ctx.send(final.rstrip())

    @commands.command(aliases = ['revokemu', 'multirevoke'])
    @commands.guild_only()
    @checks.is_mod()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    async def revokemultiuser(self, ctx, badge:str, *users:discord.Member):
        resolved_badge = self.badger.name_to_badge(ctx.guild.id, badge)
        if resolved_badge:
            badgeid = resolved_badge.id
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
        resolved_badge = self.badger.name_to_badge(ctx.guild.id, badge)
        if resolved_badge:
            result = self.badger.revoke_from_all(ctx.guild.id, resolved_badge.id)
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
        resolved_badge = self.badger.name_to_badge(ctx.guild.id, badge)
        if resolved_badge:
            badgeid = resolved_badge.id
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
        badge_exists = self.badger.name_to_badge(ctx.guild.id, name)
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
        strs = ctx.get_response('badgewizard_strings')
        maxmsg = strs['limit']
        maxtime = 30 #Max time per prompt
        msgs = []
        try:
            msgs.append(await ctx.send(strs['start'].format(maxtime) + "\n" + strs['name'].format(self.badge_limits['name'])))
            name = icon = description = levels = None

            def message_check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            while not name: #get the name
                message = await self.bot.wait_for("message", check=message_check, timeout=maxtime)
                if len(message.content) > self.badge_limits['name']:
                    msgs.append(await ctx.send(maxmsg.format("name", self.badge_limits['name'])))
                    continue
                name = message.content
            badge_exists = self.badger.name_to_badge(ctx.guild.id, name)
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
            while not levels:
                msgs.append(await ctx.send(strs['levels']))
                message = await self.bot.wait_for("message", check=message_check, timeout=maxtime)
                if not message.content.lower() in ("0", "blank", "none"):
                    try:
                        parsed_levels = int(message.content)
                        if parsed_levels > self.badge_limits['levels']:
                            msgs.append(await ctx.send_response('badgelevels_limit', self.badge_limits['levels']))
                            continue
                        levels = parsed_levels
                        break
                    except:
                        msgs.append(await ctx.send(strs['invalid_levels']))
                else:
                    break
            result = self.badger.create_badge(ctx.guild.id, name, icon, description=description)
            if levels:
                self.badger.set_badge_levels(ctx.guild.id, result.id, levels)
            if result:
                await ctx.send_response('badge_created')
            else:
                await ctx.send_response('badge_error', "creating")
            await ctx.channel.delete_messages(msgs)
        except Exception as e:
            try:
                await ctx.channel.delete_messages(msgs)
            except:
                pass
            raise e

    @commands.command(aliases=["editbadge", "modifybadge"])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def updatebadge(self, ctx, name:str, newname:str, icon:str=None, *, description:str=None):
        #Impose some limits on the parameters
        if len(newname) > self.badge_limits['name']:
            await ctx.send_response('badge_limits', 'name', self.badge_limits['name'])
            return
        if icon:
            if len(icon) > self.badge_limits['icon']:
                await ctx.send_response('badge_limits', 'icon', self.badge_limits['icon'])
                return
        if description:
            if len(description) > self.badge_limits['description']:
                await ctx.send_response('badge_limits', 'description', self.badge_limits['description'])
                return
        badge_exists = self.badger.name_to_badge(ctx.guild.id, name)
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
        resolved_badge = self.badger.name_to_badge(ctx.guild.id, name)
        if resolved_badge: #If we got a valid id
            result = self.badger.remove_badge(ctx.guild.id, resolved_badge.id)
            if result:
                await ctx.send_response('zapped', name)
            else:
                await ctx.send_response('badge_error', "removing")
        else:
            await ctx.send_response('badge_notfound')

    async def badges_real(self, ctx, paginator):
        pc = paginator.page_count
        if pc == 0:
            await ctx.send_response('badge_nobadges')
            return
        page_list = paginator.get_current_page()
        page = paginator.current_page + 1
        page_header = "> Badges `|` (Page " + str(page) + " of " + str(pc) + ")" #Could use a localization string
        page_footer = ctx.responses['page_strings']['footer'].format(ctx)
        finalstr = self.make_badge_list(page_list, header=page_header, footer=page_footer)
        if len(finalstr) > 2000: #This is a bit of jank hack, I know. But it's far more elegant than erroring and it lets server administrators fix the problem.
            f = discord.File(BytesIO(finalstr.encode("utf-8")), filename="badgelist-pg" + str(page) + ".txt")
            await ctx.send(ctx.responses['badgelist_toolarge'], file=f)
        else:
            await ctx.send(finalstr)

    @commands.command(aliases = ["listbadges", "listbadge", "badgeslist", "badgelist"])
    @commands.guild_only()
    @commands.cooldown(1, 3, type=commands.BucketType.channel)
    async def badges(self, ctx, page:int=None):
        server_badges = self.badger.get_badge_entries(server_id=ctx.guild.id)
        paginator, _, _, _ = self.bot.pagination_manager.ensure_paginator(user_id=ctx.author.id, ctx=ctx, obj=server_badges, reinvoke=self.badges_real)
        paginator.current_page = page-1 if page else 0
        await self.badges_real(ctx, paginator)

    #TODO: make this use the new pagination system
    @commands.command(aliases=['search'])
    @commands.guild_only()
    @commands.cooldown(1, 5, type=commands.BucketType.channel)
    async def badgesearch(self, ctx, *, search:str):
        max_results = 10
        results = self.badger.badge_search(ctx.guild.id, query=search).all()
        if not results:
            await ctx.send_response('badgesearch.noresults')
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

            #Put back any accidentally replaced emojis (regex is a dark art...)
            emoji_re = re.compile(r'(?<=<:)(.*?)\*\*(' + re.escape(search) + r')\*\*(.*?)(?=:\d*?>)', re.IGNORECASE)
            finalstr = emoji_re.sub(lambda x: x.group(1) + x.group(2) + x.group(3), finalstr)

            finalstr = header + finalstr
            await ctx.send(finalstr)

    @commands.command(aliases=["setlevel", "badgelevel", "setlevels", "badgelevels", "assignlevel"])
    @checks.is_admin()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    async def assignlevels(self, ctx, badge:str, levels:int):
        if abs(levels) > self.badge_limits['levels']:
            await ctx.send_response('badgelevels_limit', self.badge_limits['levels'])
            return
        resolved_badge = self.badger.name_to_badge(ctx.guild.id, badge)
        if not resolved_badge:
            await ctx.send_response('badge_notfound')
            return
        self.badger.set_badge_levels(ctx.guild.id, resolved_badge.id, levels)
        if levels == 0:
            await ctx.send_response('badgelevels_remove', badge)
        else:
            await ctx.send_response('badgelevels_set', badge, levels)

    @commands.command()
    @checks.is_mod()
    @commands.cooldown(1, 3, type=commands.BucketType.channel)
    async def hasbadge(self, ctx, user:discord.Member, *, badge:str):
        resolved_badge = self.badger.name_to_badge(ctx.guild.id, badge)
        if resolved_badge: #If we got a valid id
            result = self.badger.user_has_badge(ctx.guild.id, user.id, resolved_badge.id)
            if result:
                await ctx.send_response('badge_userhasbadge')
            else:
                await ctx.send_response('badge_usernohasbadge')
        else:
            await ctx.send_response('badge_notfound')

    async def usersearch_real(self, ctx, paginator, resolved_badge):
        page = paginator.get_current_page()
        current_page = paginator.current_page + 1
        header = "```md\n> {0}\n================\n".format( ctx.get_response('badgesearch.header').format(resolved_badge.name, current_page, paginator.page_count, paginator.item_count) )
        footer = "\n```"
        
        final = ""
        for i, winner in enumerate([x.BadgeWinner for x in page]): #Just get the BadgeWinner entries, this feels hacky
            resolved_user = self.bot.get_user(winner.discord_id)
            final += str(i + 1) + ": "
            if not resolved_user:
                final += ctx.get_response('badgesearch.unknown_user').format(winner.discord_id) + "\n"
            else:
                final += str(resolved_user) + "\n"

        final = header + final + footer
        await ctx.send(final)

    @commands.command()
    @checks.is_mod()
    @commands.cooldown(1, 3, type=commands.BucketType.guild)
    async def usersearch(self, ctx, *, badge:str): #This is bad command syntax. I should fix this with stateful paging
        resolved_badge = self.badger.name_to_badge(ctx.guild.id, badge)
        if resolved_badge: #If we got a valid id
            results = self.badger.get_award_entries(server_id=ctx.guild.id, badge_id=resolved_badge.id)
            wrapped_real = funcs.async_partial(self.usersearch_real, resolved_badge)
            paginator = pagination.Paginator(results) #Reset the paginator every time this is run.
            self.bot.pagination_manager.update_user(user_id=ctx.author.id, ctx=ctx, paginator=paginator, reinvoke=wrapped_real)
            await self.usersearch_real(ctx, paginator, resolved_badge)
        else:
            await ctx.send_response('badge_notfound')

    async def leaderboard_real(self, ctx, paginator):
        rows = paginator.get_current_page()
        page = paginator.current_page + 1
        header = "```md\n> {0}\n================\n".format( ctx.get_response('leaderboard.header').format(page, paginator.page_count) )
        footer = "\n```"
        entry = "<{num}: {user}> {levels} levels\n"
        final = header
        for position, row in enumerate(rows):
            user = self.bot.get_user(row.discord_id)
            if not user:
                u = ctx.get_response('leaderboard.unknown_user').format(row.discord_id)
            else:
                u = str(user)
            final += entry.format(num=position + (page-1)*paginator.items_per_page + 1, user=u, levels=row.levels)
        if final == header:
            final += ctx.get_response('nothing_here')
        final.rstrip()
        final += footer
        await ctx.send(final)

    @commands.command()
    @commands.cooldown(1, 10, type=commands.BucketType.channel)
    async def leaderboard(self, ctx, page:int=None):
        lbd = self.badger.get_server_leaderboard(ctx.guild.id) #This should have little overhead as the query is built, but not executed
        paginator, _, _, _ = self.bot.pagination_manager.ensure_paginator(user_id=ctx.author.id, ctx=ctx, obj=lbd, reinvoke=self.leaderboard_real)
        paginator.current_page = page-1 if page else 0 #Set the page we want
        await self.leaderboard_real(ctx, paginator) #Invoke the commands

    #Returns a boolean indicating if the given url is safe for use
    async def get_valid_image(self, ctx, image_url):
        limits = self.background_limits
        url_info = urlparse(image_url)
        if url_info.scheme == "": #fill in the protocol if none was given
            url_info = url_info._replace(scheme="http") #was told that _replace is not private but just namespaced with an underscore ¯\_(ツ)_/¯
        image_url = url_info.geturl() #extra safety (hopefully)
        if url_info.scheme not in ('http', 'https') or url_info.netloc not in limits['domains']:
            await ctx.send_response('backgrounds.invalid_url', ", ".join(limits['domains']))
            return False

        #fetch to ensure size and validity
        try:
            media = await http.download_media(image_url, mimes=limits['mimes'], timeout=limits['max_dl_time'])
        except:
            await ctx.send_response('backgrounds.fetch_failed')
            return False

        if media.getbuffer().nbytes > limits['max_bytes']:
            await ctx.send_response('backgrounds.too_large', funcs.sizeof_fmt(limits['max_bytes']))
            return False

        img = Image.open(media)
        if img.width > limits['max_size'][0] or img.height > limits['max_size'][1]:
            await ctx.send_response('backgrounds.image_size', *limits['max_size'])
            return False
        
        return img

    @commands.command(aliases=["addbg", "makebg"])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 20, type=commands.BucketType.guild)
    async def createbg(self, ctx, name:str, image_url:str, *, description:str=""):
        limits = self.background_limits
        if len(name) > limits['name']:
            await ctx.send_response('backgrounds.limits', 'name', limits['name'])
            return
        if len(description) > limits['description']:
            await ctx.send_response('backgrounds.limits', 'description', limits['description'])
            return

        existing_bg = self.profile_carder.name_to_background(ctx.guild.id, name)
        if not existing_bg:
            background_count = self.profile_carder.get_background_entries(server_id=ctx.guild.id).count()
            if background_count < limits['max_backgrounds']:

                async with ctx.channel.typing(): #do image validation after everything else
                    url_valid = await self.get_valid_image(ctx, image_url)
                    if not url_valid: return

                result = self.profile_carder.create_background(ctx.guild.id, name, image_url, description=description)
                if result:
                    await ctx.send_response('backgrounds.created')
                else:
                    await ctx.send_response('backgrounds.creation_error')
            else:
                await ctx.send_response('backgrounds.max_backgrounds', limits['max_backgrounds'])
        else:
            await ctx.send_response('backgrounds.already_exists')

    @commands.command(aliases=["delbg", "rmbg", "rembg", "removebg"])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    @funcs.require_confirmation(warning="All users with this background will be stripped of it. There is no easy way of undoing this!")
    async def deletebg(self, ctx, name:str):
        resolved_background = self.profile_carder.name_to_background(ctx.guild.id, name)
        if resolved_background:
            result = self.profile_carder.remove_background(ctx.guild.id, resolved_background.id)
            if result:
                await ctx.send_response('zapped', resolved_background.name)
            else:
                await ctx.send_response('backgrounds.deletion_error')
        else:
            await ctx.send_response('backgrounds.not_found')

    @commands.command(aliases=["editbg", "modifybg"])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 20, type=commands.BucketType.guild)
    async def updatebg(self, ctx, name:str, newname:str, url:str=None, *, description=None):
        limits = self.background_limits
        if len(newname) > limits['name']:
            await ctx.send_response('backgrounds.limits', 'name', limits['name'])
            return
        if description:
            if len(description) > limits['description']:
                await ctx.send_response('backgrounds.limits', 'description', limits['description'])
                return
        if url:
            if url.lower() in ('same', 'keep', ''):
                url = None

        existing_bg = self.profile_carder.name_to_background(ctx.guild.id, name)
        if existing_bg:
            args = {}
            if url:
                args['image_url'] = url
                with ctx.channel.typing():
                    valid = await self.get_valid_image(ctx, url)
                    if not valid: return
            if description:
                args['description'] = ('' if description.lower() in ('none', 'nothing') else description)
            updated = self.profile_carder.update_background(ctx.guild.id, existing_bg.id, new_name=newname, **args)
            if updated:
                await ctx.send_response('backgrounds.updated')
            else:
                await ctx.send_response('backgrounds.update_error')
        else:
            await ctx.send_response('backgrounds.not_found')

    @commands.command(aliases=["givebg"])
    @commands.guild_only()
    @checks.is_mod()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    async def awardbg(self, ctx, user:discord.Member, background:str):
        resolved_background = self.profile_carder.name_to_background(ctx.guild.id, background)
        if resolved_background:
            has_background = self.profile_carder.user_has_background(ctx.guild.id, user.id, resolved_background.id)
            if not has_background:
                result = self.profile_carder.award_background(ctx.guild.id, user.id, resolved_background.id)
                if result:
                    await ctx.send_response('backgrounds.awarded', user, background)
                else:
                    await ctx.send_response('backgrounds.award_error')
            else:
                await ctx.send_response('backgrounds.has_background')
        else:
            await ctx.send_response('backgrounds.not_found')

    @commands.command()
    @commands.guild_only()
    @checks.is_mod()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    async def revokebg(self, ctx, user:discord.Member, background:str):
        resolved_background = self.profile_carder.name_to_background(ctx.guild.id, background)
        if resolved_background:
            has_background = self.profile_carder.user_has_background(ctx.guild.id, user.id, resolved_background.id)
            if has_background:
                result = self.profile_carder.revoke_background(ctx.guild.id, user.id, resolved_background.id)
                if result:
                    await ctx.send_response('backgrounds.revoked', user, background)
                else:
                    await ctx.send_response('backgrounds.revoke_error')
            else:
                await ctx.send_response('backgrounds.user_missing_bg')
        else:
            await ctx.send_response('backgrounds.not_found')
        

    @commands.command(aliases=['bgstripall'])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    @funcs.require_confirmation(warning="This will strip the user of all their backgrounds! There is no easy way of undoing this!")
    async def bgrevokeall(self, ctx, user:discord.Member):
        count = self.profile_carder.revoke_all(ctx.guild.id, user.id)
        if count > 0:
            await ctx.send_response('backgrounds.revoked_all', user, count)
        else:
            await ctx.send_response('backgrounds.none_revoked', user)

    @commands.command(aliases=['bgnuke'])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    @funcs.require_confirmation(warning="All users will lose this background! There is no easy way of undoing this!")
    @funcs.require_confirmation(warning="Are you sure? This is your last chance.") #lol
    async def bgrevokefromall(self, ctx, background:str):
        resolved_background = self.profile_carder.name_to_background(ctx.guild.id, background)
        if resolved_background:
            count = self.profile_carder.revoke_from_all(ctx.guild.id, resolved_background.id)
            if count > 0:
                await ctx.send_response('backgrounds.nuked', resolved_background.name, count)
            else:
                await ctx.send_response('backgrounds.none_nuked')
        else:
            await ctx.send_response('backgrounds.not_found')

    async def backgrounds_real(self, ctx, paginator):
        pc = paginator.page_count
        if pc == 0:
            await ctx.send_response('backgrounds.no_backgrounds')
            return
        page_list = paginator.get_current_page()
        page = paginator.current_page + 1
        page_header = ctx.get_response('backgrounds.page_header').format(page, pc) #Could use a localization string
        page_footer = ctx.get_response('page_strings.footer').format(ctx)
        finalstr = self.make_background_list(page_list, header=page_header, footer=page_footer)
        if len(finalstr) > 2000: #This is a bit of jank hack, I know. But it's far more elegant than erroring and it lets server administrators fix the problem.
            f = discord.File(BytesIO(finalstr.encode("utf-8")), filename="bglist-pg" + str(page) + ".txt")
            await ctx.send(ctx.get_response('backgrounds.page_too_large'), file=f)
        else:
            await ctx.send(finalstr)

    @commands.command(aliases=['serverbgs', 'bglist', 'allbgs'])
    @commands.guild_only()
    @commands.cooldown(1, 3, type=commands.BucketType.channel)
    async def serverbackgrounds(self, ctx, page:int=None):
        server_backgrounds = self.profile_carder.get_background_entries(server_id=ctx.guild.id)
        paginator, _, _, _ = self.bot.pagination_manager.ensure_paginator(user_id=ctx.author.id, ctx=ctx, obj=server_backgrounds, reinvoke=self.backgrounds_real)
        paginator.current_page = page-1 if page else 0
        await self.backgrounds_real(ctx, paginator)

    async def mybackgrounds_real(self, ctx, paginator):
        pc = paginator.page_count
        if pc == 0:
            await ctx.send_response('backgrounds.user_no_backgrounds')
            return
        page_list = paginator.get_current_page()
        page = paginator.current_page + 1
        page_header = ctx.get_response('backgrounds.user_page_header').format(page, pc)
        page_footer = ctx.get_response('page_strings.footer').format(ctx)
        finalstr = self.make_background_list(page_list, header=page_header, footer=page_footer)
        if len(finalstr) > 2000: #This is a bit of jank hack, I know. But it's far more elegant than erroring and it lets server administrators fix the problem.
            f = discord.File(BytesIO(finalstr.encode("utf-8")), filename="mybglist-pg" + str(page) + ".txt")
            await ctx.send(ctx.get_response('backgrounds.page_too_large'), file=f)
        else:
            await ctx.send(finalstr)

    #Shows the user their backgrounds
    @commands.command(aliases=['bgs'])
    @commands.guild_only()
    @commands.cooldown(1, 3, type=commands.BucketType.channel)
    async def backgrounds(self, ctx, page:int=None):
        award_entries = self.profile_carder.get_award_entries(server_id=ctx.guild.id, discord_id=ctx.author.id)
        background_entries = [x.BackgroundEntry for x in award_entries]
        paginator, _, _, _ = self.bot.pagination_manager.ensure_paginator(user_id=ctx.author.id, ctx=ctx, obj=background_entries, reinvoke=self.mybackgrounds_real)
        paginator.current_page = page-1 if page else 0
        await self.mybackgrounds_real(ctx, paginator)

    @commands.command(aliases=['setspotlight'])
    @commands.guild_only()
    @commands.cooldown(1, 5, type=commands.BucketType.user)
    async def spotlight(self, ctx, badge:str):
        resolved_badge = self.badger.name_to_badge(ctx.guild.id, badge)
        if resolved_badge:
            has_badge = self.badger.user_has_badge(ctx.guild.id, ctx.author.id, resolved_badge.id)
            if has_badge:
                self.profile_carder.update_preferences(ctx.guild.id, ctx.author.id, spotlighted_badge_id=resolved_badge.id)
                await ctx.send_response('profiles.spotlighted', resolved_badge.name)
            else:
                await ctx.send_response('profiles.missing_badge')
        else:
            await ctx.send('badge_notfound')

    @commands.command(aliases=['setbackground', 'setbg'])
    @commands.guild_only()
    @commands.cooldown(1, 5, type=commands.BucketType.user)
    async def background(self, ctx, background:str):
        resolved_background = self.profile_carder.name_to_background(ctx.guild.id, background)
        if resolved_background:
            has_background = self.profile_carder.user_has_background(ctx.guild.id, ctx.author.id, resolved_background.id)
            if has_background:
                self.profile_carder.update_preferences(ctx.guild.id, ctx.author.id, background_id=resolved_background.id)
                await ctx.send_response('profiles.background_changed', resolved_background.name)
            else:
                await ctx.send_response('profiles.missing_background')
        else:
            await ctx.send_response('backgrounds.not_found')

def setup(bot):
    bot.add_cog(ProfileCog(bot))