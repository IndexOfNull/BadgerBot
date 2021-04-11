from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, BigInteger, SmallInteger, String, ForeignKey, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime

import sqlalchemy as sa

from .base import WidgetBase

Base = declarative_base()

class BadgeEntry(Base):
    __tablename__ = "badges"
    id = Column(SmallInteger, primary_key=True) #You know why this is here
    server_id = Column(BigInteger(), nullable=False)
    name = Column(String(255, collation="utf8mb4_unicode_ci"), nullable=False)
    description = Column(Text(collation="utf8mb4_unicode_ci"), default="")
    icon = Column(Text(collation="utf8mb4_unicode_ci"), nullable=False) #A badge icon. Use utf8mb4 for full unicode support (emojis and stuff).
    created_on = Column(TIMESTAMP, default=datetime.now()) #a timestamp to keep track of when the row was added

    levels = Column(Integer, default=0, nullable=False) #Used to be in its own module, decided to move it here

    def __repr__(self):
        return "<BadgeEntry(id='%s', text='%s', created_on='%s')>" % (self.id, self.icon, self.created_on)

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

    def get_badge_entries(self, **filters): #Be careful with this or you'll get ALL badge entries.
        rows = self.db.query(BadgeEntry).filter_by(**filters)
        return rows

    def get_award_entries(self, **filters): #Be careful with this or you'll get ALL award entries.
        rows = self.db.query(BadgeWinner, BadgeEntry)\
            .filter_by(**filters)\
            .outerjoin(BadgeEntry, BadgeWinner.badge_id == BadgeEntry.id)
        return rows

    def get_server_leaderboard(self, server_id, *, order="desc"):
        if order not in ("desc", "asc"):
            raise Exception("Order must be 'asc' or 'desc'.")
        results = self.db.query(BadgeWinner.server_id, BadgeWinner.discord_id, sa.func.sum(BadgeEntry.levels).label("levels"))\
            .outerjoin(BadgeEntry, BadgeEntry.id == BadgeWinner.badge_id)\
            .group_by(BadgeWinner.discord_id)\
            .filter_by(server_id=server_id)\
            .order_by(sa.desc("levels"))
        return results

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

    def create_badge(self, server_id, name, icon, **kwargs):
        try:
            badge = BadgeEntry(server_id=server_id, name=name, icon=icon, **kwargs)
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
            badge.icon = kwargs.pop("icon", badge.icon)
            badge.description = kwargs.pop("description", badge.description)
            self.db.commit()
            return badge
        except Exception as e:
            self.db.rollback()
            raise e

    def badge_search(self, server_id, query):
        try:
            #Build the SQL "LIKE" query
            base_query = self.db.query(BadgeEntry).filter_by(server_id=server_id)
            q1 = base_query.filter(BadgeEntry.name.like("%{}%".format(query)))
            q2 = base_query.filter(BadgeEntry.icon.like("%{}%".format(query)))
            final_query = q1.union(q2)

            return final_query
        except Exception as e:
            self.db.rollback()
            raise e

    def set_badge_levels(self, server_id, badge_id, levels):
        try:
            badge = self.db.query(BadgeEntry).filter_by(server_id=server_id, id=badge_id).first()
            badge.levels = levels
            self.db.commit()
            return badge
        except Exception as e:
            self.db.rollback()
            raise e

    def handle_embed(self, ctx, user, embed):
        ubadges = self.get_award_entries(server_id=ctx.guild.id, discord_id=user.id).all()

        icons = "".join([x.BadgeEntry.icon for x in ubadges]).strip()
        level = sum([x.BadgeEntry.levels for x in ubadges])

        icons = icons if icons else "No Badges"
        embed.add_field(name="Badges [" + str(len(ubadges)) + "]", value="".join(icons).strip(), inline=False)
        if level > 0:
            embed.add_field(name="Level", value=str(level), inline=True)
        return embed