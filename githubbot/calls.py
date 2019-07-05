# In my opinion, this is a dumb idea, but its a sane dumb idea!
# Now amplified by Sinbad's ideas! NICE!


class Queries:
    """Prebuild GraphQL query calls"""

    validateUser = """
        query ValidateUser {
            viewer {
                id
                login
            }
        }"""

    validateRepo = """
        query ValidateRepo($repoOwner: String!, $repoName: String!) {
            repository(owner: $repoOwner, name: $repoName) {
                id
                name
            }
        }"""

    findIssueOrPrId = """
        query FindIssueOrPrId($repoName: String!, $repoOwner: String!, $issueID: Int!) {
            repository(owner: $repoOwner, name: $repoName) {
                issueOrPullRequest(number: $issueID) {
                    __typename
                    ... on PullRequest {
                        id
                    }
                    ... on Issue {
                        id
                    }
                }
            }
        }"""

    findIssueOrPrComments = """
        query FindIssueOrPrComments($repoName: String!, $repoOwner: String!, $issueNumber: Int!) {
            repository(owner: $repoOwner, name: $repoName) {
                issueOrPullRequest(number: $issueNumber) {
                    __typename
                    ... on PullRequest {
                        comments(first: 100) {
                            edges {
                                node {
                                    id
                                    url
                                }
                            }
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                        }
                    }
                    ... on Issue {
                        comments(first: 100) {
                            edges {
                                node {
                                    id
                                    url
                                }
                            }
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                        }
                    }
                }
            }
        }"""

    findIssueOrPrCommentsFollowup = """
        query FindIssueOrPrCommentsFollowup($repoName: String!, $repoOwner: String!, $issueNumber: Int!, $cursor: String!) {
            repository(owner: $repoOwner, name: $repoName) {
                issueOrPullRequest(number: $issueNumber) {
                    __typename
                    ... on PullRequest {
                        comments(first: 100, after: $cursor) {
                            edges {
                                node {
                                    id
                                    url
                                }
                            }
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                        }
                    }
                    ... on Issue {
                        comments(first: 100, after: $cursor) {
                            edges {
                                node {
                                    id
                                    url
                                }
                            }
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                        }
                    }
                }
            }
        }"""


class Mutations:
    """Prebuild GraphQL mutation calls"""

    addReview = """
        mutation AddReview($issueId: ID!, $reason: String!, $reviewType: PullRequestReviewEvent!) {
            addPullRequestReview(input: {pullRequestId: $issueId, event: $reviewType, body: $reason}) {
                    clientMutationId
                }
            }"""

    lockIssue = """
        mutation LockIssue($issueId: ID!, $lockReason: LockReason!) {
            lockLockable(input: {lockableId: $issueId, lockReason: $lockReason}) {
                clientMutationId
            }
        }"""

    lockIssueNoReason = """
        mutation LockIssue($issueId: ID!) {
            lockLockable(input: {lockableId: $issueId}) {
                clientMutationId
            }
        }"""

    unlockIssue = """
        mutation UnlockIssue($issueId: ID!) {
            unlockLockable(input: {lockableId: $issueId}) {
                unlockedRecord {
                    locked
                }
            }
        }"""

    deleteComment = """
        mutation DeleteComment($commentId: ID!) {
            deleteIssueComment(input: {id: $commentId}) {
                clientMutationId
            }
        }"""

    minimizeComment = """
        mutation MinimizeComment($commentId: ID!, $minimizeReason: ReportedContentClassifiers!) {
            minimizeComment(input: {subjectId: $commentId, classifier: $minimizeReason}) {
                clientMutationId
            }
        }"""

    minimizeCommentNoReason = """
        mutation MinimizeComment($commentId: ID!) {
            minimizeComment(input: {subjectId: $commentId}) {
                clientMutationId
            }
        }"""

    unminimizeComment = """
        mutation UnminimizeComment($commentId: ID!) {
            unminimizeComment(input: {subjectID: $commentId}) {
                clientMutationId
            }
        }"""
