#!/usr/bin/env python3
import os
from aws_cdk import core as cdk

# For consistency with TypeScript code, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core

from aws_review_apps.docker_registry_stack import DockerRegistryStack
from aws_review_apps.review_app_pipeline_builder_stack import ReviewAppPipelineBuilderStack
from aws_review_apps.github_connection_stack import GitHubConnectionStack
from aws_review_apps.networking_stack import NetworkingStack
from aws_review_apps.pipeline_stack import PipelineStack

# Secrets store in SSM
aws_github_secret_name = "/awsreviewapps/github"
# Docker credentials for authenticated requests are stored in AWS Secrets manager
aws_docker_secret_name = "/awsreviewapps/dockersecrets"

app = cdk.App()
# One VPC and VPC endpoints are shared by the different environments
network = NetworkingStack(
    app,
    f"MyBackendNetworkingStack",
    app_name="MyBackend",
    deploy_env="GLOBAL",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
)

# A common GH connector can be used across environments
github_connector = GitHubConnectionStack(
    app,
    "GitHubConnectionStack",
    deploy_env="COMMON",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
)

# One ECR repo
ecr_registry = DockerRegistryStack(
    app,
    "MyBackendDockerRegistry",
    app_name="MyBackend",
    deploy_env="GLOBAL",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
)
ecr_repo = ecr_registry.ecr_repo

# Create and Destroy review apps based on GH events like PR opened/closed
ReviewAppPipelineBuilderStack(app, "PipelineBuilder",
    github_api_token=os.getenv('GH_API_TOKEN'),
    github_repo_url="https://github.com/marianobrc/aws-review-apps.git",
    aws_docker_secret_name=aws_docker_secret_name,
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
)
# Define an environment for review apps
review_branch = os.getenv("REVIEW_BRANCH", "Dev").lower()
if review_branch:
    review_app_pipeline = PipelineStack(
        app,
        f"ReviewPIEPLINE-{review_branch}",
        app_name="MyBackend",
        deploy_env=f"REVIEW-{review_branch}",
        ecr_repo=ecr_repo,
        app_config=dict(
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
            db_auto_pause_minutes=10
        ),
        github_connection=github_connector.connection,
        aws_github_secret_name=aws_github_secret_name,
        aws_docker_secret_name=aws_docker_secret_name,
        source_branch=review_branch,
        env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    )
app.synth()
