"""
Lambda function code used to create a CodeBuild project which deploys the CDK pipeline stack for the branch.
"""
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """Lambda function handler"""
    logger.info(event)
    return {
      "statusCode": "200",
      "headers": {},
      "body": "{}"
    }
