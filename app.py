#!/usr/bin/env python3
import os
from aws_cdk import core as cdk

# For consistency with TypeScript code, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core
from aws_review_apps.review_app_pipeline_builder_stack import ReviewAppPipelineBuilderStack
from aws_review_apps.backend_stage import BackendStage
from aws_review_apps.networking_stack import NetworkingStack

app = cdk.App()
# One VPC and VPC endpoints are shared by the different environments
network = NetworkingStack(
    app,
    f"MyBackendNetworkingStack",
    app_name="MyBackend",
    deploy_env="GLOBAL",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
)

# One instance of the whole system for Development/Staging
BackendStage(
    app,
    "MyBackendInStaging",
    app_name="MyBackend",
    deploy_env="STAGE",
    django_settings="api.settings.stage",
    django_secret_name="/awsreviewapps/djangosecretkey/stage",
    db_secret_name="/awsreviewapps/dbsecrets/stage",
    aws_api_key_id_secret_name="/awsreviewapps/awsapikeyid",
    aws_api_key_secret_secret_name="/awsreviewapps/awsapikeysecret",
    task_cpu=256,
    task_desired_count=1,
    min_scaling_capacity=1,
    max_scaling_capacity=1,  # Keep ecs tasks count at minimum in staging
    task_memory_mib=512,
    db_auto_pause_minutes=30,
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
)
# Define an environment for review apps
review_branch = os.getenv("REVIEW_BRANCH", "Dev").capitalize()
BackendStage(
    app,
    f"MyBackendReview{review_branch}",
    app_name="MyBackend",
    deploy_env=f"REVIEW-{review_branch}",
    django_settings="api.settings.stage",
    django_secret_name="/awsreviewapps/djangosecretkey/review",
    db_secret_name="/awsreviewapps/dbsecrets/review",
    aws_api_key_id_secret_name="/awsreviewapps/awsapikeyid",
    aws_api_key_secret_secret_name="/awsreviewapps/awsapikeysecret",
    task_cpu=256,
    task_desired_count=1,
    min_scaling_capacity=1,
    max_scaling_capacity=1,  # Keep ecs tasks count at minimum in staging
    task_memory_mib=256,
    db_auto_pause_minutes=10,
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
)
# Create and Destroy review apps based on GH events like PR opened/closed
ReviewAppPipelineBuilderStack(app, "ReviewAppPipelineBuilderStack",
    github_api_token=os.getenv('GH_API_TOKEN'),
    github_repo_url="https://github.com/marianobrc/aws-review-apps.git",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
)
app.synth()
