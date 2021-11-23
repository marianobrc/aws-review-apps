"""
Lambda function code used to create a CodeBuild project which deploys the CDK pipeline stack for the branch.
"""
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def handler(event, context):
    """Lambda function handler"""
    logger.debug(f"GH Event received:\n{event['body']}")
    gh_branch = event["body"].get("ref")
    logger.info(f"GH event detected in branch:\n{gh_branch}")
    return {
      "statusCode": "200",
      "headers": {},
      "body": "{}"
    }
