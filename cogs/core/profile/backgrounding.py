from sqlalchemy import Column, Boolean, ForeignKey, BigInteger, Integer, String, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.schema import Index, UniqueConstraint
from utils import config
from datetime import datetime
from . import badging

Base = config.declarative_base

#TODO: use proper SQL naming conventions
class BackgroundEntry(Base):
    __tablename__ = "backgrounds"
    id = Column(Integer, primary_key=True)
    server_id = Column(BigInteger(), nullable=False)

    name = Column(String(150, collation="utf8mb4_unicode_ci"), nullable=False) #must be below 191 characters or something because indexing
    description = Column(Text(collation="utf8mb4_unicode_ci"), default="")
    image_url = Column(Text(collation="utf8mb4_unicode_ci"), nullable=False)

    created_on = Column(TIMESTAMP, default=datetime.now())
    #default = Column(Boolean, nullable=False, default=0)
    usable_by_default = Column(Boolean, nullable=False, default=0)
    hidden = Column(Boolean, nullable=False, default=0)

    __table_args__ = (UniqueConstraint(server_id, name, name="_server_bg_name_uc"), ) #Ensure unique names per server

    def __repr__(self):
        return "<BackgroundEntry(id='%s', server_id='%s', name='%s', image_url='%s', ...)>" % (self.id, self.server_id, self.name, self.image_url)

class BackgroundWinner(Base):
    __tablename__ = "background_winners"
    id = Column(Integer, primary_key=True)
    server_id = Column(BigInteger(), nullable=False)

    discord_id = Column(BigInteger(), nullable=False)
    background_id = Column(Integer, ForeignKey(BackgroundEntry.id, ondelete="CASCADE"), nullable=False)
    awarded = Column(TIMESTAMP, default=datetime.now())

    background = relationship("BackgroundEntry", foreign_keys="BackgroundWinner.background_id")

    __table_args__ = (
        Index("_server_member_ix", server_id, discord_id),
        UniqueConstraint(discord_id, background_id, name="_discord_bg_id_uc", ) #make it so users can only have one background win entry per background
    )

    def __repr__(self):
        return "<BackgroundWinner(id='%s', server_id='%s', discord_id='%s', background_id='%s')>" % (self.id, self.server_id, self.discord_id, self.background_id)

class ProfilePreferences(Base):
    __tablename__ = "profile_preferences"
    id = Column(Integer, primary_key=True)
    server_id = Column(BigInteger(), nullable=False)
    
    discord_id = Column(BigInteger(), nullable=False)
    spotlighted_badge_id = Column(Integer, ForeignKey(badging.BadgeEntry.id))
    background_id = Column(Integer, ForeignKey(BackgroundEntry.id))

    background = relationship("BackgroundEntry", foreign_keys="ProfilePreferences.background_id")
    spotlighted_badge = relationship("BadgeEntry", foreign_keys="ProfilePreferences.spotlighted_badge_id")

    __table_args__ = (UniqueConstraint(server_id, discord_id, name="_server_member_uc"), ) #Ensure one preference entry per user per server

class BackgroundManager(): #maybe make some of this apart of the actual ORM class instance

    def __init__(self, db):
        self.db = db

    def award_background(self, server_id, discord_ids, background_id):
        raise NotImplemented()

    def revoke_background(self, server_id, discord_ids, background_id):
        raise NotImplemented()

    def revoke_all(self, server_id, discord_id):
        raise NotImplemented()

    def revoke_from_all(self, server_id, badge_id):
        raise NotImplemented()

    def name_to_background(self, server_id, background_name):
        raise NotImplemented()

    def get_background_entries(self, **filters):
        raise NotImplemented()

    def get_award_entries(self, **filters):
        raise NotImplemented()

    def user_has_background(self, server_id, discord_id, background_id):
        raise NotImplemented()

    def create_background(self, server_id, name, image_url, *, description="", usable_by_default=False, hidden=False):
        raise NotImplemented()

    def remove_background(self, server_id, background_id):
        raise NotImplemented()

    def set_default(self, server_id, background_id): 
        raise NotImplemented()

    