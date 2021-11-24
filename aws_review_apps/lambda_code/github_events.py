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
    dst_branch = gh_event["pull_request"]["base"]["ref"]
    src_branch = gh_event["pull_request"]["head"]["ref"]
    action = gh_event.get("action")
    logger.info(f"PR detected: {dst_branch} <- {src_branch} [{action}]")
    return {
      "statusCode": "200",
      "headers": {},
      "body": "{}"
    }
