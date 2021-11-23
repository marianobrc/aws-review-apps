#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

# For consistency with TypeScript code, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core

from aws_review_apps.aws_review_apps_stack import AwsReviewAppsStack


app = cdk.App()
AwsReviewAppsStack(app, "AwsReviewAppsStack",
    github_api_token=os.getenv('GH_API_TOKEN'),
    github_repo_url="https://github.com/marianobrc/aws-review-apps",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
)
app.synth()
