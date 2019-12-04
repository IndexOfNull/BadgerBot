from sqlalchemy.types import TIMESTAMP
from sqlalchemy import Column, Integer, BigInteger, SmallInteger, String, ForeignKey, Text, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


import datetime

from .classes import WidgetBase

Base = declarative_base()


class BadgeEntry(Base):
    __tablename__ = "badges"
    id = Column(SmallInteger, primary_key=True) #You know why this is here
    name = Column(String(255), nullable=False)
    description = Column(Text(collation="utf8mb4_unicode_ci"), default="")
    image = Column(String(255), nullable=False) #An image path, may turn into a blob. For use in rendering with PIL. Collation shouldn't be an issue here
    text = Column(String(255, collation="utf8mb4_unicode_ci"), nullable=False) #A piece of text. For use in rendering out to text. Also use utf8mb4 for full unicode support.
    created_on = Column(TIMESTAMP, default=datetime.datetime.now()) #a timestamp to keep track of when the row was added
    
    def __repr__(self):
        return "<BadgeEntry(id='%s', image='%s', text='%s', created_on='%s')>" % (self.id, self.image, self.text, self.created_on)

class BadgeWinner(Base):
    __tablename__ = "badgewinners"
    itemid = Column(Integer, primary_key=True) # A unique index for cataloging the event
    discord_id = Column(BigInteger(), nullable=False) # 0 -> 2^63 - 1
    badge_id = Column(SmallInteger, ForeignKey(BadgeEntry.id, ondelete="CASCADE"), nullable=False) # -16000 -> ~16,000, keeps track of what badge
    awarded = Column(TIMESTAMP, default=datetime.datetime.now()) #a timestamp to keep track of when the row was added

    badge = relationship("BadgeEntry", foreign_keys="BadgeWinner.badge_id") #Make a reference to the badge in question

    def __repr__(self):
        return "<BadgeWinner(discord_id='%s', badge_id='%s', badge='%s', timestamp='%s')>" % (self.discord_id, self.badge_id, self.badge, self.awarded)

class BadgeWidget(WidgetBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.build_tables: #Unfortunately this can't be inherited due to each table being created on a different declaritive_base()
            Base.metadata.create_all(self.db.bind)

    def award_badge(self, discord_id, badge_id):
        try:
            winner = BadgeWinner(discord_id=discord_id, badge_id=badge_id)
            result = self.db.query(BadgeWinner).filter_by(discord_id = discord_id)
            for row in result:
                print(row)
                print(row.badge)
            self.db.add(winner)
            self.db.commit()
            return winner
        except: #May need to add exc.IntegrityError. I don't think that's possible with this though
            self.db.rollback()
            return False

    def revoke_badge(self, discord_id, badge_id):
        try:
            result = self.db.query(BadgeWinner).filter_by(discord_id=discord_id, badge_id=badge_id).delete()
            self.db.commit()
            return result
        except exc.IntegrityError:
            self.db.rollback()
            return False

    def name_to_id(self, badge_name):
        rows = self.db.query(BadgeEntry).filter_by(name=badge_name).first()
        if rows:
            return rows.id
        else:
            return None

    def remove_badge(self, id):
        try:
            result = self.db.query(BadgeEntry).filter_by(id = id).delete() #This calls directly to the database, 
            self.db.commit()
            return result
        except exc.IntegrityError:
            self.db.rollback()
            return False

    def create_badge(self, name, text, image, **kwargs):
        try:
            badge = BadgeEntry(name=name, image=image, text=text, **kwargs)
            self.db.add(badge)
            self.db.commit()
            return True
        except exc.IntegrityError:
            self.db.rollback()
            return False