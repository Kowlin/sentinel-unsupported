import discord
import aiohttp

from typing import Optional, Union
from redbot.core import checks, commands, Config

from .calls import Queries, Mutations
from .http import GitHubAPI, ReviewType, LockReasons, MinimizeReasons
from .exceptions import RepoNotFound

BaseCog = getattr(commands, "Cog", object)
DEFAULT_GUILD = {"github_repos": {}}

"""
{
    "reponame": {
        "owner": "Cog-Creators",
        "repo": "Red-DiscordBot",
        "allowed_role": role ID
    }
}
"""

# TODO, make the has roleID checks into their own checks... Later though


class GitHubBot(BaseCog):
    """GitHub Bot designed for approvals"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=25360016)
        self.config.register_guild(**DEFAULT_GUILD)

        self.rt = ReviewType  # TODO REMOVE THIS LATER, THIS IS JUST DEBUGGING
        self.lr = LockReasons
        self.mr = MinimizeReasons

    @commands.group(name="githubbotset", aliases=["ghbs"])
    async def ghbs(self, ctx):
        """Manage GitHub Bot"""
        pass

    @checks.is_owner()
    @ghbs.command(name="token")
    async def ghbs_token(self, ctx, *, token: str):
        """Set a Personal Access token

        To get an Personal Access token visit:
        https://github.com/settings/tokens
        Select the "Repo" and "Read:user" permissions.

        Is is strongly recommended to do this in your DMs"""
        message = """To set your token use the following command:
        ``set api github token,<YOUR TOKEN HERE>``
        And reload the cog afterwards, since I didn't exactly check yet on whenever it should try to reload

        *Also be smart and do it in DMs with me*"""
        await ctx.send(message)

    @ghbs.group(name="repo")
    async def ghbs_repo(self, ctx):
        """Manage the repositories the bot can interact with

        When adding or removing a repository please do it with the owner and repository name in it.
        As example:
        Cog-Creators/Red-DiscordBot"""
        pass

    @checks.is_owner()
    @ghbs_repo.command(name="add", usage="<name> <repository owner/repository name> <role>")
    async def ghbsr_add(self, ctx, name: str, repo: str, role: discord.Role):
        """Add a new repository

        name: The name the repository will be accessed
        repository: The repository in a "owner/repository" format.
        role: The role that can interact with the repo"""
        api_config = await self.bot.db.api_tokens.get_raw("github", default={"token": None})
        if api_config["token"] is None:
            return await ctx.send("There is no token set. Please set a token.")

        repo = repo.split("/")
        if len(repo) != 2:
            return await ctx.send(
                "The repository you've provided looks invalid. Please double check"
            )
        valid = await self._process_validate_repo(repo[0], repo[1])
        if valid is False:
            return await ctx.send("It seems that I cannot access this repo or its invalid.")

        repo_list = await self.config.guild(ctx.guild).github_repos()
        if name in repo_list.keys():
            return await ctx.send("There already exists repo under this name")

        repo_list[name] = {"owner": repo[0], "repo": repo[1], "role": role.id}
        await self.config.guild(ctx.guild).github_repos.set(repo_list)
        return await ctx.tick()

    @checks.admin_or_permissions(manage_guild=True)
    @ghbs_repo.command(name="remove")
    async def ghbsr_remove(self, ctx, name: str):
        """Remove a repository"""
        repo_list = await self.config.guild(ctx.guild).github_repos()  # Returns dictionary
        try:
            del repo_list[name]
        except:
            return await ctx.send("This repository name isn't found")
        await self.config.guild(ctx.guild).github_repos.set(repo_list)
        await ctx.tick()

    @ghbs_repo.command(name="list")
    async def ghbsr_list(self, ctx):
        """List the repositories"""
        repo_list = await self.config.guild(ctx.guild).github_repos()
        formated_list = ""
        if len(repo_list) == 0:
            return await ctx.send("No repositories have been set.")
        for name, data in repo_list.items():
            formated_list += f"{name}: {data['owner']}/{data['repo']}"
        return await ctx.send(formated_list)

    # HERE BE NO MORE SET COMMANDS!~

    @commands.group(aliases=["gh"])
    async def github(self, ctx):
        """Manage GitHub repositories from within Discord"""
        pass

    @github.command(usage="[repo] <issueId> [lockReason]")
    async def lock(self, ctx, repo: Optional[str], issueId: Optional[int], lockReason: Optional[str]):
        """Lock an issue or pull request.

        Arguments:
        `repo (Optional)`: A linked repository. Optional if there is only one linked repo
        `issueId`: Issue or PR ID
        `lockReason (Optional)`: A reason for the lock. Valid reasons are: offtopic, resolved, spam, or heated
        """
        valid_reasons = ["offtopic", "resolved", "spam", "heated"]
        if lockReason is not None and lockReason.lower() not in valid_reasons:
            return await ctx.send_help()

        # For lack of better idea on what to do with this... Enjoy this extremely dumb fucking handling of data classes
        if lockReason is not None:
            if lockReason.lower() == "offtopic":
                lockReason = LockReasons.OFF_TOPIC
            if lockReason.lower() == "resolved":
                lockReason = LockReasons.RESOLVED
            if lockReason.lower() == "spam":
                lockReason = LockReasons.SPAM
            if lockReason.lower() == "heated":
                lockReason = LockReasons.TOO_HEATED

        if repo.isdigit() is True:
            issueId = int(repo)
            repo = None
        if repo is None:
            repo = await self._get_repo_if_single(ctx.guild)
        if repo is False:
            return await ctx.send(
                "There are multiple repos linked to this server, please specify a repo.\nSee ``ghbs repo list`` to see the list."
            )

        if await self._has_allowed_role(ctx.author, repo) is False:
            return await ctx.send("You're not authorised to administer this repo.")

        issueId = await self._get_issue_or_pr_id(ctx.guild, repo, issueId)

        if lockReason is not None:
            httpResult = await self.http.lockIssue(issueId, lockReason)
        else:
            httpResult = await self.http.lockIssue(issueId)

        if "errors" in httpResult.keys():
            return await ctx.send(f"There was an error.\n``{httpResult['errors']}``")
        else:
            return await ctx.tick()

    #  After thinking about it for long enough, its easier to make this into multiple commands then a single big one.
    @github.command()
    async def approve(self, ctx, repo: Optional[str], prId: Optional[int], *, comments: Optional[str]):
        """Approve a pull request.

        Arguments:
        `repo (Optional)`: A linked repository, Optional if there is only one repository linked.
        `prId`: Pull Request ID
        `comments (Optional)`: Comments that will be attached alongside the approval.
        """
        if repo.isdigit() is True:
            prId = int(repo)
            repo = None
        if repo is None:
            repo = await self._get_repo_if_single(ctx.guild)
        if repo is False:
            return await ctx.send(
                "There are multiple repos linked to this server, please specify a repo.\nSee ``ghbs repo list`` to see the list."
            )

        if await self._has_allowed_role(ctx.author, repo) is False:
            return await ctx.send("You're not authorised to administer this repo.")

        prId = await self._get_pr_id(ctx.guild, repo, prId)
        if prId is False:
            return await ctx.send("The Pull request you tried to approve was an issue, whoops.")

        review_comment = f"Approved by {str(ctx.author)}"
        if comments is not None:
            review_comment += f"\n\n{comments}"

        httpResult = await self.http.addReview(prId, review_comment, ReviewType.APPROVE)
        if "errors" in httpResult.keys():
            return await ctx.send(f"There was an error.\n``{httpResult['errors']}``")
        else:
            return await ctx.tick()

    @github.command()
    async def requestchanges(self, ctx, repo: Optional[str], prId: Optional[int], *, comments: Optional[str]):
        """Request changes for a pull request.

        Arguments:
        `repo (Optional)`: A linked repository, Optional if there is only one repository linked.
        `prId`: Pull Request ID
        `comments (Optional)`: Comments that will be attached alongside the approval.
        """
        if repo.isdigit() is True:
            prId = int(repo)
            repo = None
        if repo is None:
            repo = await self._get_repo_if_single(ctx.guild)
        if repo is False:
            return await ctx.send(
                "There are multiple repos linked to this server, please specify a repo.\nSee ``ghbs repo list`` to see the list."
            )

        if await self._has_allowed_role(ctx.author, repo) is False:
            return await ctx.send("You're not authorised to administer this repo.")

        prId = await self._get_pr_id(ctx.guild, repo, prId)
        if prId is False:
            return await ctx.send("The Pull request you tried to approve was an issue, whoops.")

        review_comment = f"Changes requested by {str(ctx.author)}"
        if comments is not None:
            review_comment += f"\n\n{comments}"

        httpResult = await self.http.addReview(prId, review_comment, ReviewType.REQUEST_CHANGES)
        if "errors" in httpResult.keys():
            return await ctx.send(f"There was an error.\n``{httpResult['errors']}``")
        else:
            return await ctx.tick()


# TODO. Fix this... if its needed, doubt it is lol.
#    @github.command()
#    async def dismiss(self, ctx, repo: Optional[str], prId: Optional[int], *, comments: Optional[str]):
#        """Dismiss the bot review for a pull request.
#
#        **Warning:** This will dismiss ALL reviews left by the bot.
#
#        Arguments:
#        `repo (Optional)`: A linked repository, Optional if there is only one repository linked.
#        `prId`: Pull Request ID
#        `comments (Optional)`: Comments that will be attached alongside the approval.
#        """
#        if repo.isdigit() is True:
#            prId = int(repo)
#            repo = None
#        if repo is None:
#            repo = await self._get_repo_if_single(ctx.guild)
#        if repo is False:
#            return await ctx.send(
#                "There are multiple repos linked to this server, please specify a repo.\nSee ``ghbs repo list`` to see the list."
#            )
#
#        if await self._has_allowed_role(ctx.author, repo) is False:
#            return await ctx.send("You're not authorised to administer this repo.")
#
#        prId = await self._get_pr_id(ctx.guild, repo, prId)
#        if prId is False:
#            return await ctx.send("The Pull request you tried to approve was an issue, whoops.")
#
#        review_comment = f"Dismissed by {str(ctx.author)}"
#        if comments is not None:
#            review_comment += f"\n\n{comments}"
#
#        httpResult = await self.http.addReview(prId, review_comment, ReviewType.DISMISS)
#        if "errors" in httpResult.keys():
#            return await ctx.send(f"There was an error.\n``{httpResult['errors']}``")
#        else:
#            return await ctx.tick()

    # ALL THE INTERNAL NONSENSE

    async def _set_token(self):
        """Get the token and prepare the header"""
        config_api = await self.bot.db.api_tokens.get_raw("github", default={"token": None})
        if config_api["token"] is None:
            return False
        self.http = GitHubAPI(token=config_api["token"])
        return True

    async def _get_repo_if_single(self, guild: discord.Guild):
        """Get the repo if its the only one in a guild, otherwise return false"""
        repo_list = await self.config.guild(guild).github_repos()
        if await self._has_single_repo(guild) is False:  # Can't find correct repo due to multiple
            return False
        else:
            print(list(repo_list.keys())[0])
            return list(repo_list.keys())[
                0
            ]  # I assume that we can safely do this since we only have one repo.

    async def _get_issue_or_pr_id(self, guild: discord.Guild, repo, issueId: int):
        """Get the internal ID needed for every GH action"""
        repo_list = await self.config.guild(guild).github_repos()
        if repo not in repo_list.keys():
            raise RepoNotFound

        repo = repo_list[repo]
        httpResult = await self.http.findIssueOrPrId(repo["owner"], repo["repo"], issueId)
        if "errors" in httpResult.keys():
            raise Exception(f"{httpResult['errors']}")
        return httpResult["data"]["repository"]["issueOrPullRequest"]["id"]

    async def _get_pr_id(self, guild: discord.Guild, repo, prId: int):
        """Get the internal ID needed for every GH action

        Returns false if its not a pull request."""
        repo_list = await self.config.guild(guild).github_repos()
        if repo not in repo_list.keys():
            raise RepoNotFound

        repo = repo_list[repo]
        httpResult = await self.http.findIssueOrPrId(repo["owner"], repo["repo"], prId)
        if "errors" in httpResult.keys():
            raise Exception(f"{httpResult['errors']}")
        if httpResult["data"]["repository"]["issueOrPullRequest"]["__typename"] == "PullRequest":
            return httpResult["data"]["repository"]["issueOrPullRequest"]["id"]
        else:
            return False

    async def _has_single_repo(self, guild: discord.Guild):
        """Check if there is only a single repo on the guild"""
        repo_list = await self.config.guild(guild).github_repos()
        if len(repo_list.keys()) == 1:
            print(True)
            return True
        else:
            print(False)  # DEBUG PRINT REMOVE
            return False

    async def _has_allowed_role(self, author: discord.Member, repo: str):
        """Check if the author has the dedicated role required to use the commands"""
        guild = author.guild
        if await self.bot.is_owner(author):
            return True
        repo_list = await self.config.guild(guild).github_repos()
        if repo not in repo_list.keys():
            raise RepoNotFound
        required_role_id = repo_list[repo]["role"]

        for role in author.roles:
            if role.id == required_role_id:
                return True
        return False

    async def _process_validate_repo(self, owner: str, repo: str):
        """Check if the given repo is a existing one"""
        httpResult = await self.http.validateRepo(owner, repo)
        if "errors" in httpResult.keys():
            return False  # There is an error while fetching the repo
        else:
            return True
