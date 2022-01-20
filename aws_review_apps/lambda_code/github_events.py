"""
Lambda function used to create a CodeBuild project which deploys a new pipeline stack for every new PR.
"""
import json
import logging
import os
import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def generate_build_spec(branch: str, stack_name, account_id: str, region: str, gh_api_token: str):
    """Generates the build spec file used for the CodeBuild project"""
    return f"""version: 0.2
env:
  variables:
    REVIEW_BRANCH: {branch}
    ACCOUNT_ID: {account_id}
    REGION: {region}
    GH_API_TOKEN: {gh_api_token}
phases:
  install:
    runtime-versions:
        docker   
    commands: 
      - nohup /usr/local/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://127.0.0.1:2375 --storage-driver=overlay2&
      - timeout 15 sh -c "until docker info; do echo .; sleep 1; done"
  pre_build:
    commands:
      - npm install -g aws-cdk && pip install -r requirements.txt
  build:
    commands:
      - echo REVIEW_BRANCH:$REVIEW_BRANCH
      - echo ACCOUNT_ID:$ACCOUNT_ID
      - echo REGION:$REGION
      - echo REGION:$GH_API_TOKEN
      - cdk --version
      - cat ./cdk.context.json
      - cdk doctor
      - cdk synth -v {stack_name}
      - cdk deploy -v {stack_name} --require-approval=never
artifacts:
  files:
    - '**/*'"""


def handler(event, context):
    """Lambda function handler"""
    gh_event = json.loads(event['body'])
    logger.debug(f"GH Event received:\n{gh_event}")
    action = gh_event.get("action")
    if action == "opened":  # New PR
        dst_branch = gh_event["pull_request"]["base"]["ref"]
        src_branch = gh_event["pull_request"]["head"]["ref"]
        logger.info(f"PR detected: {dst_branch} <- {src_branch} [{action}]")
        logger.info(f"Making a codebuild project to deploy pipeline for branch {src_branch}..")
        repo_url = gh_event["pull_request"]['head']['repo']['clone_url']
        region = os.environ['AWS_REGION']
        account_id = os.environ['ACCOUNT_ID']
        gh_api_token = os.environ['GH_API_TOKEN']
        role_arn = os.environ['CODE_BUILD_ROLE_ARN']
        logger.info(f"CodeBuild role: {role_arn}..")
        artifact_bucket_name = os.environ['ARTIFACT_BUCKET']
        codebuild_client = boto3.client('codebuild')
        codebuild_project_name = f'build-review-app-{src_branch}'
        stack_name = f"ReviewPIEPLINE-{src_branch}"
        codebuild_client.create_project(
            name=codebuild_project_name,
            description=f"Build project to deploy a review app pipeline for branch {src_branch}",
            source={
                'type': 'GITHUB',
                'location': repo_url,
                'buildspec': generate_build_spec(
                    branch=src_branch,
                    stack_name=stack_name,
                    account_id=account_id,
                    region=region,
                    gh_api_token=gh_api_token
                )
            },
            sourceVersion=f'refs/heads/{src_branch}',
            artifacts={
                'type': 'S3',
                'location': artifact_bucket_name,
                'path': f'{src_branch}',
                'packaging': 'NONE',
                'artifactIdentifier': 'BranchBuildArtifact'
            },
            environment={
                'type': 'LINUX_CONTAINER',
                'image': 'aws/codebuild/standard:4.0',
                'computeType': 'BUILD_GENERAL1_SMALL',
                "privilegedMode": True
            },
            serviceRole=role_arn
        )
        logger.info(f"Deploying pipeline for branch {src_branch}..")
        codebuild_client.start_build(
            projectName=codebuild_project_name
        )

    return {
      "statusCode": "200",
      "headers": {},
      "body": "{}"
    }
