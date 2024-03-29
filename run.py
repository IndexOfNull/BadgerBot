from bot import BuddyBot
import discord
import json
import os
import argparse

parser = argparse.ArgumentParser(description="Run BadgerBot")
parser.add_argument("--generate-config", default=False, action="store_true", help="generates the config file if it doesn't exist")
parser.add_argument("--create-tables", "-c", default=False, action="store_true", help="creates required tables in the database")
parser.add_argument("--config", default="config.json", help="where to load the bot's configuration")
parser.add_argument("--write-updated-config", default=False, action="store_true", help="write new values not present into the config rather than injecting them at runtime")

args = parser.parse_args()

settings = {
    "token": "[TOKEN HERE]",
    "db_engine_uri": "mysql+pymysql://USER:PASS@IP/DATABASE",
    "case_insensitive": True,
    "db_ping_interval": 14400,
    "dev_mode": False,
    "privileged_intents": ["members"]
}

def write_config(opts):

    stringed = json.dumps(opts, indent=4, separators=(',', ': '))
    with open(args.config, "w") as f:
        f.write(stringed)

if not os.path.exists(args.config):
    if args.generate_config:
        print("--generate-config was specified. Making a config and exiting...")
        write_config(settings)
    else:
        print("A bot config is required and wasn't found! Run with --generate-config to generate one. Remember to keep it super secret!")
        if args.config != "config.json":
            print("Make sure the file specified in --config exists. You can run --generate-config in conjunction with --config to generate a config in your specified location.")
    exit()

with open(args.config) as f:
    config = json.loads(f.read())

missing_options = { k : settings[k] for k in set(settings) - set(config) } #Get default key-val for missing options
config.update(missing_options) #Merge the dictionaries

if args.write_updated_config is True: #Write it if the user wants to
    write_config(config)

#command line options -> kwarg
config['create_tables'] = args.create_tables

buddy = BuddyBot(**config)

if __name__ == "__main__":
    try:
        buddy.run()
    except discord.errors.PrivilegedIntentsRequired:
        print("You are trying to use privileged intents that have not been enabled in the Discord developer portal. Consider explicitly enabling the privileged intents. If doing so is not possible, consider disabling the intents in your config file.")
    except KeyboardInterrupt:
        task = buddy.loop.create_task(buddy.close())
        buddy.loop.run_until_complete(buddy.close())
