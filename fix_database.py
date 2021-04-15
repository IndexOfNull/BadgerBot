import run
import sqlalchemy as sa

engine_uri = run.config['db_engine_uri']
engine = sa.create_engine(engine_uri)

resp = input("STOP! Do you have a backup of your BadgerBot database? [y/N]: ")
if resp.lower() != "y":
    print("aborting")
    exit()

connection = engine.connect()

trans = connection.begin()
try:
    with connection.begin() as transaction:
        connection.execute("ALTER TABLE `badgelevels` DROP FOREIGN KEY badgelevels_ibfk_1;")
        connection.execute("ALTER TABLE `badgewinners` DROP FOREIGN KEY badgewinners_ibfk_1;")

        connection.execute("ALTER TABLE `badges` CHANGE `id` `id` INT NOT NULL AUTO_INCREMENT;")
        connection.execute("ALTER TABLE `badgewinners` CHANGE `itemid` `id` INT(11) NOT NULL AUTO_INCREMENT;")
        connection.execute("ALTER TABLE `badgewinners` CHANGE `badge_id` `badge_id` INT NOT NULL;")
        connection.execute("ALTER TABLE `badgelevels` CHANGE `badge_id` `badge_id` INT NOT NULL;")

        connection.execute("ALTER TABLE `badgewinners` ADD FOREIGN KEY (`badge_id`) REFERENCES `badges`(`id`) ON DELETE CASCADE;")

        connection.execute("ALTER TABLE `badgelevels` ADD FOREIGN KEY (`badge_id`) REFERENCES `badges` (`id`) ON DELETE CASCADE;")
        connection.execute("ALTER TABLE `badges` CHANGE `text` `icon` TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;")
        connection.execute("ALTER TABLE `badges` ADD `levels` INT NOT NULL DEFAULT '0' AFTER `icon`;")
except Exception as e:
    print(e)
    print("Something went wrong while modifying the database, some changes may have still been made.")
    exit()

connection.close()
print("Successfully ran migration script.")