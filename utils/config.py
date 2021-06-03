#Globals module to share important information across other modules
from sqlalchemy.ext.declarative import declarative_base

create_tables = False #Set to true if you want to autocreate the database schema
database = None #Database handle
declarative_base = declarative_base() #Common declarative base for auto table creation