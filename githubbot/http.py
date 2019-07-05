import aiohttp
import logging

from .calls import Queries, Mutations
from dataclasses import dataclass

baseUrl = "https://api.github.com/graphql"
log = logging.getLogger("red.githubbot.http")


@dataclass
class ReviewType(object):
    APPROVE: str = "APPROVE"
    COMMENT: str = "COMMENT"
    DISMISS: str = "DISMISS"
    REQUEST_CHANGES: str = "REQUEST_CHANGES"


@dataclass
class LockReasons(object):
    OFF_TOPIC: str = "OFF_TOPIC"
    RESOLVED: str = "RESOLVED"
    SPAM: str = "SPAM"
    TOO_HEATED: str = "TOO_HEATED"


@dataclass
class MinimizeReasons(object):
    ABUSE: str = "ABUSE"
    OFF_TOPIC: str = "OFF_TOPIC"
    OUTDATED: str = "OUTDATED"
    RESOLVED: str = "RESOLVED"
    SPAM: str = "SPAM"


class GitHubAPI:
    def __init__(self, token: str):
        headers = {
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.queen-beryl-preview+json",
        }
        self.session = aiohttp.ClientSession(headers=headers)

    async def validateUser(self):
        async with self.session.post(baseUrl, json={"query": Queries.validateUser}) as call:
            return await call.json()

    async def validateRepo(self, repoOwner: str, repoName: str):
        async with self.session.post(
            baseUrl,
            json={
                "query": Queries.validateRepo,
                "variables": {"repoOwner": repoOwner, "repoName": repoName},
            },
        ) as call:
            return await call.json()

    async def findIssueOrPrId(self, repoOwner: str, repoName: str, issueID: int):
        async with self.session.post(
            baseUrl,
            json={
                "query": Queries.findIssueOrPrId,
                "variables": {"repoOwner": repoOwner, "repoName": repoName, "issueID": issueID},
            },
        ) as call:
            return await call.json()

    async def findIssueOrPrComments(
        self, repoOwner: str, repoName: str, issueNumber: int, cursor: str = None
    ):
        if cursor is None:
            async with self.session.post(
                baseUrl,
                json={
                    "query": Queries.findIssueOrPrComments,
                    "variables": {
                        "repoOwner": repoOwner,
                        "repoName": repoName,
                        "issueNumber": issueNumber,
                    },
                },
            ) as call:
                return await call.json()
        else:
            async with self.session.post(
                baseUrl,
                json={
                    "query": Queries.findIssueOrPrCommentsFollowup,
                    "variables": {
                        "repoOwner": repoOwner,
                        "repoName": repoName,
                        "issueNumber": issueNumber,
                        "cursor": cursor,
                    },
                },
            ) as call:
                return await call.json()

    async def addReview(self, issueId: str, reason: str, reviewType: ReviewType):
        async with self.session.post(
            baseUrl,
            json={
                "query": Mutations.addReview,
                "variables": {"issueId": issueId, "reason": reason, "reviewType": reviewType},
            },
        ) as call:
            return await call.json()

    async def lockIssue(self, issueId: str, lockReason: LockReasons = None):
        if lockReason is None:
            async with self.session.post(
                baseUrl,
                json={"query": Mutations.lockIssueNoReason, "variables": {"issueId": issueId}},
            ) as call:
                return await call.json()
        else:
            async with self.session.post(
                baseUrl,
                json={
                    "query": Mutations.lockIssue,
                    "variables": {"issueId": issueId, "lockReason": lockReason},
                },
            ) as call:
                return await call.json()

    async def unlockIssue(self, issueId: str):
        async with self.session.post(
            baseUrl, json={"query": Mutations.unlockIssue, "variables": {"issueId": issueId}}
        ) as call:
            return await call.json()

    async def deleteComment(self, commentId: str):
        async with self.session.post(
            baseUrl, json={"query": Mutations.deleteComment, "variables": {"commentId": commentId}}
        ) as call:
            return await call.json()

    async def minimizeComment(self, commentId: str, reason: MinimizeReasons):
        async with self.session.post(
            baseUrl,
            json={
                "query": Mutations.minimizeComment,
                "variables": {"commentId": commentId, "minimizeReason": reason},
            },
        ) as call:
            return await call.json()

    async def unminimizeComment(self, commentId: str):
        async with self.session.post(
            baseUrl,
            json={"query": Mutations.unminimizeComment, "variables": {"commentId": commentId}},
        ) as call:
            return await call.json()
