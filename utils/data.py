#This is gonna be one large file where data related stuff gets put.
#This will likely hold the code for localization, server options, and any other required things

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TIMESTAMP
from sqlalchemy import Column, Integer, BigInteger, String, Text

import datetime

from utils import checks

db = None
Base = declarative_base()
class OptionEntry(Base):
    __tablename__ = "serveropts"
    id = Column(Integer, primary_key=True)
    server_id = Column(BigInteger, nullable=False)
    name = Column(String(128), nullable=False) #names will be hardcoded in, so no special collation should be needed
    data = Column(Text(), nullable=False)
    created_on = Column(TIMESTAMP, default=datetime.datetime.now()) #a timestamp to keep track of when the row was added

class DataManager():

    def __init__(self, bot):
        self.db = bot.db
        if bot.create_tables:
            Base.metadata.create_all(bot.db.bind)

    def get_options(self, server_id, **filters):
        try:
            rows = self.db.query(OptionEntry).filter_by(server_id=server_id, **filters).all()
            return rows
        except Exception as e:
            self.db.rollback()
            raise e

    def set_option(self, server_id, option, value):
        try:
            row = OptionEntry(server_id=server_id, name=option, data=value)
            self.db.add(row)
            self.db.commit()
            return row
        except Exception as e:
            self.db.rollback()
            raise e

    def remove_option(self, server_id, option): #Not sure if this will really ever be used, oh well...
        try:
            result = self.db.query(OptionEntry).filter_by(server_id=server_id, name=option).delete()
            self.db.commit()
            return result
        except Exception as e:
            self.db.rollback()
            raise e

    