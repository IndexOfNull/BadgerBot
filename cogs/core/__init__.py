from .profile import cog as profile_cog
from . import core

def setup(bot):
    core.setup(bot)
    profile_cog.setup(bot)

"""
def teardown(bot):
    profile_cog.teardown(bot)
    core.teardown(bot)
"""