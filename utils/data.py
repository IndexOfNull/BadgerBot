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
    data = Column(Text(collation="utf8mb4_unicode_ci"), nullable=False)
    created_on = Column(TIMESTAMP, default=datetime.datetime.now()) #a timestamp to keep track of when the row was added

class OptionNotRegistered(Exception): pass

class DataManager():

    def __init__(self, bot):
        self.db = bot.db
        if bot.create_tables:
            Base.metadata.create_all(bot.db.bind)
        self.server_options = {}

    def register_option(self, name, default = None): #this is so we can keep integrity
        self.server_options[name] = default

    def get_options(self, server_id, **filters):
        try:
            process = filters.pop("process", True)
            basic = filters.pop("basic", False)
            hasfilters = filters != {}
            rows = self.db.query(OptionEntry).filter_by(server_id=server_id, **filters).all()
            rowkeys = [row.name for row in rows]
            if process:
                for key, value in self.server_options.items():
                    if hasfilters:
                        cont = True
                        for fname, fval in filters.items():
                            if fname == key or fval == value:
                                cont = False
                        if cont:
                            continue
                    if not key in rowkeys:
                        entry = OptionEntry(server_id=server_id, name=key, data=value)
                        entry.fake = True #Let the rest of the program know that this was not pulled from the db.
                        rows.append(entry)
            if not basic:
                return rows
            return {row.name: row.data for row in rows}
        except Exception as e:
            self.db.rollback()
            raise e

    def set_option(self, server_id, option, value, bypass=False):
        if not option in self.server_options and not bypass:
            raise OptionNotRegistered(option + " is not registered. Be sure to register it or pass True for the bypass param.")
        try:
            entry = self.db.query(OptionEntry).filter_by(server_id=server_id, name=option).first()
            if entry:
                entry.data = value
            else:
                entry = OptionEntry(server_id=server_id, name=option, data=value)
                self.db.add(entry)
            self.db.commit()
            return entry
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

    