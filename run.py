from bot import BuddyBot
import json
import os
import argparse

parser = argparse.ArgumentParser(description="Run BadgerBot")
parser.add_argument("--generate-config", default=False, action="store_true", help="generates the config file if it doesn't exist")
parser.add_argument("--create-tables", "-c", default=False, action="store_true", help="creates required tables in the database")

args = parser.parse_args()

def generate_config():
    settings = {
        "token": "[TOKEN HERE]",
        "db_engine_uri": "mysql+pymysql://USER:PASS@IP/DATABASE"
    }
    stringed = json.dumps(settings)
    with open("config.json", "w") as f:
        f.write(stringed)

if not os.path.exists("config.json"):
    if args.generate_config:
        print("--generate-config was specified. Making a config and exiting...")
        generate_config()
    else:
        print("A bot config is required and wasn't found! Run with --generate-config to generate one. Remember to keep it super secret!")
    exit()

with open("config.json") as f:
    config = json.loads(f.read())

config['create_tables'] = args.create_tables

buddy = BuddyBot(**config)

if __name__ == "__main__":
    try:
        buddy.run()
    except:
        pass
    print("Closing")
