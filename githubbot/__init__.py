from .core import GitHubBot


async def setup(bot):
    cog = GitHubBot(bot)
    await cog._set_token()
    bot.add_cog(cog)
