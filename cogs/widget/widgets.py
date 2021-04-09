from sqlalchemy.types import TIMESTAMP
from sqlalchemy import Column, Integer, BigInteger, SmallInteger, String, ForeignKey, Text, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

import discord

from datetime import datetime, timezone
def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

def aslocaltimestr(utc_dt):
    return utc_to_local(utc_dt).strftime('%Y-%m-%d %H:%M:%S')


from .classes import WidgetBase

Base = declarative_base()

class BadgeEntry(Base):
    __tablename__ = "badges"
    id = Column(SmallInteger, primary_key=True) #You know why this is here
    server_id = Column(BigInteger(), nullable=False)
    name = Column(String(255, collation="utf8mb4_unicode_ci"), nullable=False)
    description = Column(Text(collation="utf8mb4_unicode_ci"), default="")
    text = Column(Text(collation="utf8mb4_unicode_ci"), nullable=False) #A piece of text. For use in rendering out to text. Also use utf8mb4 for full unicode support.
    created_on = Column(TIMESTAMP, default=datetime.now()) #a timestamp to keep track of when the row was added
    
    def __repr__(self):
        return "<BadgeEntry(id='%s', text='%s', created_on='%s')>" % (self.id, self.text, self.created_on)

class BadgeWinner(Base):
    __tablename__ = "badgewinners"
    itemid = Column(Integer, primary_key=True) # A unique index for cataloging the event
    server_id = Column(BigInteger(), nullable=False)
    discord_id = Column(BigInteger(), nullable=False) # 0 -> 2^63 - 1
    badge_id = Column(SmallInteger, ForeignKey(BadgeEntry.id, ondelete="CASCADE"), nullable=False) # -16000 -> ~16,000, keeps track of what badge
    awarded = Column(TIMESTAMP, default=datetime.now()) #a timestamp to keep track of when the row was added

    badge = relationship("BadgeEntry", foreign_keys="BadgeWinner.badge_id") #Make a reference to the badge in question

    def __repr__(self):
        return "<BadgeWinner(discord_id='%s', badge_id='%s', badge='%s', timestamp='%s')>" % (self.discord_id, self.badge_id, self.badge, self.awarded)

class BadgeWidget(WidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.build_tables: #Unfortunately this can't be inherited due to each table being created on a different declaritive_base()
            Base.metadata.create_all(self.db.bind)

    def award_badge(self, server_id, discord_ids, badge_id):
        single = False
        if not isinstance(discord_ids, list):
            discord_ids = [discord_ids]
            single = True
        try:
            objects = []
            for user in discord_ids:
                winner = BadgeWinner(server_id=server_id, discord_id=user, badge_id=badge_id)
                objects.append(winner)
                self.db.add(winner)
            self.db.commit()
            if single: #return just the object if they passed an int
                return objects[0]
            else: #give them the whole list otherwise
                return objects #Maybe make this return a list later
        except Exception as e: #May need to add exc.IntegrityError. I don't think that's possible with this though
            self.db.rollback()
            raise e

    def get_server_badges(self, server_id):
        rows = self.db.query(BadgeEntry).filter_by(server_id=server_id)
        return rows

    def get_user_badges(self, server_id, discord_id):
        rows = self.db.query(BadgeWinner).filter_by(server_id=server_id, discord_id=discord_id)
        return rows

    def user_has_badge(self, server_id, discord_id, badge_id):
        result = self.db.query(BadgeWinner).filter_by(server_id=server_id, discord_id=discord_id, badge_id=badge_id).first()
        if result:
            return True
        return False

    def users_have_badge(self, server_id, discord_ids, badge_id): #Returns a dictionary with user ids as keys with a bool representing if they have a badge
        result = self.db.query(BadgeWinner.discord_id).filter_by(server_id=server_id, badge_id=badge_id)\
                    .filter(BadgeWinner.discord_id.in_(discord_ids))\
                    .all()
        extracted_ids = [row.discord_id for row in result]
        d = {}
        for user in discord_ids:
            d[user] = user in extracted_ids
        return d

    def revoke_badge(self, server_id, discord_ids, badge_id):
        if not isinstance(discord_ids, list):
            discord_ids = [discord_ids]
        try:
            result = self.db.query(BadgeWinner).filter_by(server_id=server_id, badge_id=badge_id)\
                    .filter(BadgeWinner.discord_id.in_(discord_ids))\
                    .delete(synchronize_session=False) #We should be able to get away with this because we commit right after. We can always use 'fetch'
            self.db.commit()
            return result
        except Exception as e: #Maybe add exc.IntegrityError
            self.db.rollback()
            raise e

    def revoke_all(self, server_id, discord_id):
        try:
            result = self.db.query(BadgeWinner).filter_by(server_id=server_id, discord_id=discord_id).delete(synchronize_session=False)
            self.db.commit()
            return result
        except Exception as e:
            self.db.rollback()
            raise e

    def revoke_from_all(self, server_id, badge_id):
        try:
            result = self.db.query(BadgeWinner).filter_by(server_id=server_id, badge_id=badge_id).delete(synchronize_session=False)
            self.db.commit()
            return result
        except Exception as e:
            self.db.rollback()
            raise e

    def name_to_id(self, server_id, badge_name):
        rows = self.db.query(BadgeEntry).filter_by(server_id=server_id, name=badge_name).first()
        if rows:
            return rows.id
        else:
            return None

    def remove_badge(self, server_id, id):
        try:
            result = self.db.query(BadgeEntry).filter_by(server_id=server_id, id = id).delete() #This calls directly to the database, 
            self.db.commit()
            return result
        except Exception as e: #Maybe add exc.IntegrityError
            self.db.rollback()
            raise e

    def create_badge(self, server_id, name, text, **kwargs):
        try:
            badge = BadgeEntry(server_id=server_id, name=name, text=text, **kwargs)
            self.db.add(badge)
            self.db.commit()
            return badge
        except Exception as e:  #Maybe add exc.IntegrityError
            self.db.rollback()
            raise e

    def update_badge(self, server_id, name, **kwargs):
        try:
            badge = self.db.query(BadgeEntry).filter_by(server_id=server_id, name=name).first()
            badge.name = kwargs.pop("newname", badge.name)
            badge.text = kwargs.pop("text", badge.text)
            badge.description = kwargs.pop("description", badge.description)
            self.db.commit()
            return badge
        except Exception as e:
            self.db.rollback()
            raise e

    def badge_search(self, server_id, query):
        try:
            #Build the SQL "LIKE" query
            base_query = self.db.query(BadgeEntry)
            q1 = base_query.filter(BadgeEntry.name.like("%{}%".format(query)))
            q2 = base_query.filter(BadgeEntry.text.like("%{}%".format(query)))
            final_query = q1.union(q2)

            return final_query
        except Exception as e:
            self.db.rollback()
            raise e

    def handle_embed(self, ctx, user, embed):
        ubadges = self.get_user_badges(ctx.guild.id, user.id)
        icons = []
        count = 0
        for winentry in ubadges:
            icons.append(winentry.badge.text + " ")
            count += 1
        icons = icons if icons else "No Badges"
        embed.add_field(name="Badges [" + str(count) + "]", value="".join(icons).strip(), inline=False)
        return embed

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

class AccountAgeWidget(WidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.embed_only = True

    def handle_embed(self, ctx, user, embed):
        if not isinstance(user, discord.User) and not isinstance(user, discord.Member): #If we don't have a user-like object
            return
        t = user.created_at
        if t: #user.joined_at can sometimes return None
            converted_time = t.strftime('%Y-%m-%d %H:%M:%S') + " UTC"
            embed.add_field(name="Account Created", value=converted_time)
