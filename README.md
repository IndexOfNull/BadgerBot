# BadgerBot

Hello, this is a little project of mine called BadgerBot. It is currently ~~***unfinished***~~ in a working state where most things work as expected. It is primarily designed to be a system for giving badges to server members, but there are some other modules that add some fun things. You can check the projects tab if you want to see what's planned and where I'm going with this.

**WARNING: There have been a lot of database changes recently (including the installation of Alembic). You should read the README in the alembic directory for directions on upgrading your database (if you need to, which you probably do).**

You are welcome to open an issue or PR so my code can be fixed :)

# Requirements

* Python 3.7 or above. Anything past 3.5.3 should work, but may need additional tweaking.
* Pipenv (for now)
* A database, any should work. I personally use MySQL (MariaDB), but something like PostgreSQL should work too.

This should be all you need to run this properly.

# Installation

Installation is pretty simple, and can basically be done with these steps:

1. Clone the repository, `cd` into it, and setup a pipenv environment:

```
git clone https://github.com/IndexOfNull/BadgerBot
cd BadgerBot
pipenv install
```

You should be able to change the Python version in the Pipfile if pipenv complains. You should only really need to do this if you are running Python 3.8.

4. Run the bot with `python3 run.py --generate-config` to get a config file. The bot will not start after a config has been made.

5. Open the `config.json` file and fill in the necessary details like your bot token and database URI.

6. Open the `alembic.ini` file and fill in the same database URI you did in `config.json`.

7. Run `alembic upgrade head` to run migrations.

- You should be good to go.


# Important Notes

## The `config.json` File

*  **token**:
This is your bot's Discord token. You can get it from Discord's dev portal.

*  **db_engine_uri**:
This is your database location and credentials. It should be formatted like this: `engine+engineaddon://user:password@ip/database`. You can omit `:password` if your database user does not have one.

*  **case_insensitive**:
`Default: true`
Specifies if commands should be case insensitive or not.

*  **db_ping_interval**:
`Default: 14400`
How often should we ping the database (just running `SELECT 1`) before it kills our connection for inactivity. Set this to `0` to disable.

*  **privileged_intents**:
`Default: ["members"]`
`Options: "members", "presences"`
What gateway intents we should enable. You must enable these in the Discord developer portal as well. The members intent is required for the leaderboard to work. See [here](https://discordpy.readthedocs.io/en/latest/intents.html) for more info.

### Updates and the `config.json`

Updates will occasionally require new options to be added in the `config.json`. This could cause problems, as your config could become outdated. To combat this, the bot will identify missing options and fill them in automatically. However, it does this in memory and does not write the corrected config by default. You can tell the bot to write the corrected config by specifying `--write-updated-config`

I may change it to be on by default, but running it after you update to the latest commit would probably be a good idea for now.

### Miscellaneous

You can change the config file path by specifying `--config <PATH>`.

# Additional Info

If you are curious about how the bot implements different things, check out the info.md file.