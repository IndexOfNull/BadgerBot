
# BadgerBot

Hello, this is a little project of mine called BadgerBot. It is currently ***unfinished***, but it should be in a functional state. Its main purpose right now is to just be a badge system (hence the name), but that will probably branch out more in the future. You can check the projects tab if you want to see what's planned and where I'm going with this.

  

**I would not clone this if you were looking for a fully-featured bot. You will not get any support; you're on your own.**

  

# Requirements

  

* Python 3.7 or above. Anything past 3.5.3 should work, but may need additional tweaking.

* Pipenv (for now)

* A database, any should work. I personally use MySQL (MariaDB), but something like PostgreSQL should work too.

  

This should be all you need to run this properly.

  

# Installing

Installing is pretty simple, and can basically be done with these steps:

1. Clone the repository, `cd` into it, and setup a pipenv environment:
```
git clone https://github.com/IndexOfNull/BadgerBot
cd BadgerBot
pipenv install
```
You should be able to change the Python version in the Pipfile if pipenv complains. You should only really need to do this if you are running Python 3.8.

4. Run the bot with `python3 run.py --generate-config` to get a config file. The bot will not start after a config has been made.

5. Open the `config.json` file and fill in the necessary details like your bot token and database URI. 

6. Run the bot again with `python3 run.py --create-tables` to create all the necessary tables in your database

  

*Note*: You shouldn't (normally) have to include the `--create-tables` argument. You can omit it from now on.

  

 - You should be good to go.

 # Important Notes
## The `config.json` File
* **token**:
This is your bot's Discord token. You can get it from Discord's dev portal.

* **db_engine_uri**:
This is your database location and credentials. It should be formatted like this: `engine+engineaddon://user:password@ip/database`. You can omit `:password` if your database user does not have one.

* **case_insensitive**:
Specifies if commands should be case insensitive or not. This defaults to `true`.

* **web_secret**:
This is a "password" of sorts that authenticates requests made to the bot's internal webserver. This is not statically filled; the value filled in by default should be plenty secure.

* **pool_recycle**:
This is how long the database connection should be allowed to live before being closed and reopened. Most people probably will not have to change this, but people with different database configurations may have to. This defaults to `3600` seconds (1 hour).
### Updates and the `config.json`
Updates will occasionally require new options to be added in the `config.json`. This could cause problems, as your config could become outdated. To combat this, the bot will identify missing options and fill them in automatically. However, it does this in memory and does not write the corrected config by default. You can tell the bot to write the corrected config by specifying `--write-updated-config`

I may change it to be on by default, but running it after you update to the latest commit would probably be a good idea for now.

### Miscellaneous
You can change the config file path by specifying `--config <PATH>`.

# Additional Info

If you are curious about how the bot implements different things, check out the info.md file.