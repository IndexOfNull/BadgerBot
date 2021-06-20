from sqlalchemy import Column, Boolean, ForeignKey, BigInteger, Integer, String, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.schema import Index, UniqueConstraint
from utils import config
from datetime import datetime
from . import badges

Base = config.declarative_base

#TODO: use proper SQL naming conventions
#TODO: maybe make a decorator for autorollback of failed transactions
class BackgroundEntry(Base):
    __tablename__ = "backgrounds"
    id = Column(Integer, primary_key=True)
    server_id = Column(BigInteger(), nullable=False)

    name = Column(String(150, collation="utf8mb4_unicode_ci"), nullable=False) #must be below 191 characters or something because indexing
    description = Column(Text(collation="utf8mb4_unicode_ci"), default="")
    image_url = Column(Text(collation="utf8mb4_unicode_ci", length=500), nullable=False)

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
    #id = Column(Integer, primary_key=True) #oh well, not gonna use a surrogate because Session.merge() is too convenient
    server_id = Column(BigInteger(), nullable=False, primary_key=True)
    
    discord_id = Column(BigInteger(), nullable=False, primary_key=True)
    spotlighted_award_id = Column(Integer, ForeignKey(badges.BadgeWinner.id, ondelete="SET NULL")) #TODO: evaluate ondelete validity with relationship()
    background_award_id = Column(Integer, ForeignKey(BackgroundWinner.id, ondelete="SET NULL"))

    _background_award_entry = relationship("BackgroundWinner", foreign_keys="ProfilePreferences.background_award_id")
    _spotlighted_award_entry = relationship("BadgeWinner", foreign_keys="ProfilePreferences.spotlighted_award_id")

    @property
    def background(self):
        return None if self._background_award_entry is None else self._background_award_entry.background #Be careful about ordering here...

    @property
    def spotlighted_badge(self):
        return None if self._spotlighted_award_entry is None else self._spotlighted_award_entry.badge

    #__table_args__ = (UniqueConstraint(server_id, discord_id, name="_server_member_uc"), ) #Ensure one preference entry per user per server

class ProfileCardManager():

    def __init__(self, db):
        self.db = db

    def award_background(self, server_id, discord_id, background_id):
        try:
            winner = BackgroundWinner(server_id=server_id, discord_id=discord_id, background_id=background_id)
            self.db.add(winner)
            self.db.commit()
            return winner
        except Exception as e:
            self.db.rollback()
            raise e

    def revoke_background(self, server_id, discord_id, background_id):
        try:
            result = self.db.query(BackgroundWinner).filter_by(server_id=server_id, discord_id=discord_id, background_id=background_id).delete()
            self.db.commit()
            return result
        except Exception as e:
            self.db.rollback()
            raise e

    def revoke_all(self, server_id, discord_id):
        try:
            results = self.db.query(BackgroundWinner).filter_by(server_id=server_id, discord_id=discord_id).delete(synchronize_session=False)
            self.db.commit()
            return results
        except Exception as e:
            self.db.rollback()
            raise e

    def revoke_from_all(self, server_id, background_id):
        try:
            result = self.db.query(BackgroundWinner).filter_by(server_id=server_id, background_id=background_id).delete(synchronize_session=False)
            self.db.commit()
            return result
        except Exception as e:
            self.db.rollback()
            raise e

    def name_to_background(self, server_id, background_name):
        row = self.db.query(BackgroundEntry).filter_by(server_id=server_id, name=background_name).first()
        if row:
            return row
        return None

    def get_background_entries(self, **filters):
        rows = self.db.query(BackgroundEntry).filter_by(**filters)
        return rows

    def get_award_entries(self, **filters):
        rows = self.db.query(BackgroundWinner, BackgroundEntry)\
            .filter_by(**filters)\
            .outerjoin(BackgroundEntry, BackgroundWinner.background_id == BackgroundEntry.id)
        return rows

    def user_has_background(self, server_id, discord_id, background_id):
        result = self.get_award_entries(server_id=server_id, discord_id=discord_id, background_id=background_id).first()
        return True if result else False

    def create_background(self, server_id, name, image_url, *, description="", usable_by_default=False, hidden=False):
        try:
            background = BackgroundEntry(server_id=server_id, name=name, description=description, image_url=image_url, usable_by_default=usable_by_default, hidden=hidden)
            self.db.add(background)
            self.db.commit()
            return background
        except Exception as e:
            self.db.rollback()
            raise e

    def remove_background(self, server_id, background_id):
        try:
            result = self.db.query(BackgroundEntry).filter_by(server_id=server_id, id=background_id).delete()
            self.db.commit()
            return result
        except Exception as e:
            self.db.rollback()
            raise e

    def update_background(self, server_id, background_id, **kwargs):
        try:
            background = self.db.query(BackgroundEntry).filter_by(server_id=server_id, id=background_id).first()
            background.name = kwargs.pop("new_name", background.name)
            background.image_url = kwargs.pop("image_url", background.image_url)
            background.usable_by_default = kwargs.pop("usable_by_default", background.usable_by_default)
            background.hidden = kwargs.pop("hidden", background.hidden)
            background.description = kwargs.pop("description", background.description)
            self.db.commit()
            return background
        except Exception as e:
            self.db.rollback()
            raise e

    #kwargs are spotlighted_award_id and background_award_id
    #You must use an award entry (cannot be a badge or background entry directly)
    def update_preferences(self, server_id, discord_id, **kwargs):
        try:
            prefs = ProfilePreferences(server_id=server_id, discord_id=discord_id, **kwargs)
            self.db.merge(prefs)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def get_preferences(self, server_id, discord_id):
        prefs = self.db.query(ProfilePreferences).filter_by(server_id=server_id, discord_id=discord_id).first()
        if prefs:
            return prefs
        return None