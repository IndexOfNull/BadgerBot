#Globals module to share important information across other modules
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData

create_tables = False #Set to true if you want to autocreate the database schema
database = None #Database handle

db_key_naming_conventions = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
base_metadata = MetaData(naming_convention=db_key_naming_conventions)
declarative_base = declarative_base(metadata=base_metadata) #Common declarative base for auto table creationconvention = {
