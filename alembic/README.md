# Alembic Migrations

Hello, its about time I've started using Alembic. Up here I just want to say I am sincerely sorry that I was not wise enough to use this before. If you've been using BadgerBot for a while, there's a good chance you've suffered because of that.

But that all ends now; updating to the latest database schema should be as easy as one command (`alembic update head`)

Now, that being said, the first migration is to create a schema compatible with commit `22bb31`. It will NOT migrate your outdated database; this tool is for future use. Keep reading if you are running an outdated database.

# READ THIS IF YOU ARE USING AN OLDER SCHEMA

If you are using an older database ***(you probably are)***, follow this mini-guide to automatically get upgrade your database to the latest commit.

Note: if you have any local changes that you wish to keep, stash them with git first or you *will* lose them.

1. Take note of your current git head with `git rev-parse HEAD`. This will be useful if you need to downgrade. **DO NOT TOUCH YOUR DATABASE YET**

2. Update the local git repository, switch to the proper HEAD, and create the alembic versions folder:
    ```
    git checkout master
    git pull
    git reset --hard 8accbe50511ebcd033a6feb8bb24943ec9157099
    ```
    Alembic should be installed in the project at this point. It should have a stopgap migration already installed

4. **MAKE A BACKUP OF YOUR DATABASE!** Seriously, I did my best to make this script good, but there still could be a problem with it. In line with best practices, you should be responsible and make a backup just in case.

5. Run `alembic upgrade head`. Alembic will get your database up to the latest version.

6. Verify your data (poke around your database for a bit, make sure everything looks good)

7. Hard reset to the latest commit with `git reset --hard HEAD`

9. Update `version_num` in `alembic_version` to be `0d992f099915`. This will prevent alembic from doing the initial creation migration.

10. Run `alembic upgrade head` to run all migrations that have happened since.

11. Done!

Thank you for sticking with me and I wish you the best of bot hosting :)