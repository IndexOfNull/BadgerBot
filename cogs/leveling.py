import sqlalchemy as sa
from sqlalchemy.types import TIMESTAMP
from sqlalchemy import Column, Integer, BigInteger, SmallInteger, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from datetime import datetime

import discord
from discord.ext import commands

from cogs.widget.classes import WidgetBase
from cogs.widget.widgets import BadgeEntry, BadgeWinner
from utils import checks, funcs

Base = declarative_base()
class BadgeLevelEntry(Base):
    __tablename__ = "badgelevels"
    id = Column(Integer, primary_key=True)
    server_id = Column(BigInteger(), nullable=False)
    badge_id = Column(SmallInteger, ForeignKey(BadgeEntry.id, ondelete="CASCADE"), nullable=False)
    levels = Column(Integer, default=0)
    created_on = Column(TIMESTAMP, default=datetime.now())

    badge = relationship(BadgeEntry, foreign_keys="BadgeLevelEntry.badge_id")

class LevelWidget(WidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.embed_only = True
        self.badge_widget = self.render_manager.get_widget("BadgeWidget")

    def get_levels(self, server_id, **filters):
        try:
            rows = self.db.query(BadgeLevelEntry).filter_by(server_id=server_id, **filters).all()
            return rows
        except Exception as e:
            self.db.rollback()
            raise e

    def assign_levels(self, server_id, badge_id, levels):
        try:
            existing_entry = self.db.query(BadgeLevelEntry).filter_by(server_id=server_id, badge_id=badge_id).first()
            if existing_entry:
                if levels == 0: #make 0 delete the row, resetting the badges levels
                    self.db.delete(existing_entry)
                    self.db.commit()
                    return existing_entry
                existing_entry.levels = levels
                self.db.commit()
                return existing_entry
            else:
                if levels == 0: #Don't even bother lol
                    return
                entry = BadgeLevelEntry(server_id=server_id, badge_id=badge_id, levels=levels)
                self.db.add(entry)
                self.db.commit()
                return entry
        except Exception as e:
            self.db.rollback()
            raise e
    
    def handle_embed(self, ctx, user, embed):
        rows = self.get_levels(ctx.guild.id)
        usr_badges = self.badge_widget.get_user_badges(ctx.guild.id, user.id)
        id_to_lvl = {row.badge_id: row.levels for row in rows}
        total = 0
        for row in usr_badges:
            if row.badge_id in id_to_lvl: #Make sure that there is indeed a level entry for the current badge in the iteration
                total += id_to_lvl[row.badge_id]
        embed.insert_field_at(1, name="Level", value=str(total), inline=False)
        embed.color = user.color
        return embed

class LevelCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db
        self.profilecog = self.bot.get_cog("ProfileCog") #This is a crucial dependency for this cog
        if not self.profilecog:
            raise Exception("ProfileCog is missing, leveling will not work!")
        self.rendermanager = self.profilecog.manager
        self.levelwidget = self.rendermanager.register_widget(LevelWidget)
        if self.bot.create_tables:
            Base.metadata.create_all(self.db.bind)



    """@commands.command() #We don't need this anymore because the ProfileCog will autodetect 
    @commands.cooldown(1, 5, type=commands.BucketType.channel)
    async def levels(self, ctx):
        line = "{0.text} **{0.name}**: {1}\n"
        finalstr = "> __Badge Levels__\n"
        levels = self.levelwidget.get_levels(ctx.guild.id)
        if not levels:
            await ctx.send(ctx.responses['badgelevels_nolevels'])
            return
        for entry in levels:
            finalstr += line.format(entry.badge, entry.levels)
        await ctx.send(finalstr)"""

    @commands.command(aliases=["setlevel", "badgelevel", "setlevels", "badgelevels", "assignlevels"])
    @checks.is_admin()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    async def assignlevel(self, ctx, badge:str, levels:int):
        if abs(levels) > 200:
            await ctx.send(ctx.responses['badgelevels_limit'].format(30))
            return
        badge_id = self.profilecog.badger.name_to_id(ctx.guild.id, badge)
        if not badge_id:
            await ctx.send(ctx.responses['badge_notfound'])
            return
        self.levelwidget.assign_levels(ctx.guild.id, badge_id, levels)
        if levels == 0:
            await ctx.send(ctx.responses['badgelevels_remove'].format(badge))
        else:
            await ctx.send(ctx.responses['badgelevels_set'].format(badge, levels))

    @commands.command()
    @commands.cooldown(1, 10, type=commands.BucketType.channel)
    async def leaderboard(self, ctx, page:int=1):
        lbd = self.db.query(BadgeWinner.server_id, BadgeWinner.discord_id, sa.func.sum(BadgeLevelEntry.levels)\
            .label("levels"))\
            .join(BadgeLevelEntry, sa.and_(BadgeWinner.badge_id == BadgeLevelEntry.badge_id, BadgeWinner.server_id == ctx.guild.id))\
            .group_by(BadgeWinner.discord_id)\
            .order_by(sa.desc("levels"))
        pager = funcs.Paginator(lbd, items_per_page=10)
        page = funcs.clamp(page, 1, pager.page_count) #Clamp page so that we can't pick a page past the last page
        rows = pager.get_page(page-1) #Subtract one for computer friendliness
        header = "```md\n> {0}\n================\n".format( ctx.responses['leaderboard_strings']['leaderboard'].format(page, pager.page_count) )
        footer = "\n```"
        entry = "<{num}: {user}> {levels} levels\n"
        final = header
        for position, row in enumerate(rows):
            user = self.bot.get_user(row.discord_id)
            if not user:
                u = ctx.responses['leaderboard_strings']['unknown_user'] + "#" + str(row.discord_id)
            else:
                u = str(user)
            final += entry.format(num=position + (page-1)*pager.items_per_page + 1, user=u, levels=row.levels)
        if final == header:
            final += ctx.responses['leaderboard_strings']['nothing']
        final.rstrip()
        final += footer
        await ctx.send(final)

def setup(bot):
    bot.add_cog(LevelCog(bot))