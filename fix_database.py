import run
import sqlalchemy as sa

engine_uri = run.config['db_engine_uri']
engine = sa.create_engine(engine_uri)

connection = engine.connect()

trans = connection.begin()
connection.execute("ALTER TABLE `badgewinners` CHANGE `itemid` `id` INT(11) NOT NULL AUTO_INCREMENT;")
connection.execute("ALTER TABLE `badges` CHANGE `id` `id` INT NOT NULL AUTO_INCREMENT;")
connection.execute("ALTER TABLE `badges` CHANGE `text` `icon` TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;")
connection.execute("ALTER TABLE `badges` ADD `levels` INT NOT NULL DEFAULT '0' AFTER `icon`;")
trans.commit()