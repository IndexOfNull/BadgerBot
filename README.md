# BadgerBot
Hello, this is a little project of mine called BadgerBot. It is currently ***unfinished***,  but is in a semi-functional state. Its main purpose right now is to just be a badge system (hence the name), but that will probably branch out more in the future. You can check the projects tab if you want to see what's planned and where I'm going with this.

**I would not clone this if you were looking for a fully-featured bot. You will not get any support; you're on your own.**

# Requirements

* At least python 3.5.3
* Pipenv (for now)
* A database, any should work. I personally use MySQL (MariaDB), but stuff like PostgreSQL should work too.

This should be all you need to run this properly.

# Installing
Installing is pretty simple, and can basically be done with these steps:

1. Clone the repository with `git clone https://github.com/IndexOfNull/BadgerBot` and `cd BadgerBot`
2. Install the dependencies. There is no requirements.txt file right now, but you can get everything you need with pipenv: `pipenv install`. You should be able to change the python version in Pipfile if needed, but that's uncharted territory.
3. Run the bot with `python3 run.py --generate-config` to get a config file.
4. Open the config.json file and fill in the necessary details like your bot token and database URI.
5. Run the bot again with `python3 run.py --create-tables` to create all the necessary tables in your database

   *Note*: You shouldn't (normally) have to include the `--create-tables` argument. You can omit it from now on.

7. You should be good to go.