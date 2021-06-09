from sqlalchemy import Column, Boolean, ForeignKey, BigInteger, Integer, String, Text, TIMESTAMP
from sqlalchemy.orm import relation, relationship
from utils import config
from datetime import datetime

Base = config.declarative_base

class BackgroundEntry(Base):
    __tablename__ = "backgrounds"
    id = Column(Integer, primary_key=True)
    server_id = Column(BigInteger(), nullable=False)

    name = Column(String(255, collation="utf8mb4_unicode_ci"), nullable=False)
    description = Column(Text(collation="utf8mb4_unicode_ci"), default="")
    image_url = Column(Text(collation="utf8mb4_unicode_ci"), nullable=False)

    created_on = Column(TIMESTAMP, default=datetime.now())
    #default = Column(Boolean, nullable=False, default=0)
    usable_by_default = Column(Boolean, nullable=False, default=0)
    hidden = Column(Boolean, nullable=False, default=0)

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

    def __repr__(self):
        return "<BackgroundWinner(id='%s', server_id='%s', discord_id='%s', background_id='%s')>" % (self.id, self.server_id, self.discord_id, self.background_id)

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

    