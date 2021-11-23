"""
Lambda function code used to create a CodeBuild project which deploys the CDK pipeline stack for the branch.
"""
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def handler(event, context):
    """Lambda function handler"""
    gh_event = json.loads(event['body'])
    logger.debug(f"GH Event received:\n{gh_event}")
    gh_branch = gh_event.get("ref")
    logger.info(f"GH event detected in branch:\n{gh_branch}")
    return {
      "statusCode": "200",
      "headers": {},
      "body": "{}"
    }
