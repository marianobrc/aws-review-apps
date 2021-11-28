#!/usr/bin/env python3
import os
from aws_cdk import core as cdk

# For consistency with TypeScript code, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core

from aws_review_apps.review_app_pipeline_builder_stack import ReviewAppPipelineBuilderStack
from review_app_pipeline_stack import ReviewAppPipeline

app = cdk.App()
# Create and Destroy review apps based on GH events like PR opened/closed
ReviewAppPipelineBuilderStack(app, "ReviewAppPipelineBuilderStack",
    github_api_token=os.getenv('GH_API_TOKEN'),
    github_repo_url="https://github.com/marianobrc/aws-review-apps.git",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
)
review_app_branch = os.getenv("BRANCH")
review_app_stack_name = f"ReviewAppPipeline{review_app_branch.capitalize()}"
ReviewAppPipeline(app, review_app_stack_name,
    github_api_token=os.getenv('GH_API_TOKEN'),
    github_repo_url="https://github.com/marianobrc/aws-review-apps.git",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
)
app.synth()
