from bot import BuddyBot
import json
import os
import argparse

parser = argparse.ArgumentParser(description="Run BadgerBot")
parser.add_argument("--generate-config", default=False, action="store_true", help="generates the config file if it doesn't exist")
parser.add_argument("--create-tables", "-c", default=False, action="store_true", help="creates required tables in the database")
parser.add_argument("--config", default="config.json", help="where to load the bot's configuration")

args = parser.parse_args()

def generate_config():
    settings = {
        "token": "[TOKEN HERE]",
        "db_engine_uri": "mysql+pymysql://USER:PASS@IP/DATABASE",
        "case_insensitive": True
    }
    stringed = json.dumps(settings)
    with open(args.config, "w") as f:
        f.write(stringed)

if not os.path.exists(args.config):
    if args.generate_config:
        print("--generate-config was specified. Making a config and exiting...")
        generate_config()
    else:
        print("A bot config is required and wasn't found! Run with --generate-config to generate one. Remember to keep it super secret!")
        if args.config != "config.json":
            print("Make sure the file specified in --config exists. You can run --generate-config in conjunction with --config to generate a config in your specified location.")
    exit()

with open(args.config) as f:
    config = json.loads(f.read())

config['create_tables'] = args.create_tables

buddy = BuddyBot(**config)

if __name__ == "__main__":
    try:
        buddy.run()
    except:
        pass
    print("Closing")
