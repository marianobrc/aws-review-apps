from os import path
from aws_cdk import core as cdk
# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core
from aws_cdk.aws_apigateway import LambdaRestApi
from aws_cdk.aws_iam import Role, ServicePrincipal, ManagedPolicy, PolicyStatement
from aws_cdk import aws_lambda
from aws_cdk import aws_s3 as s3
from cloudcomponents.cdk_github_webhook import GithubWebhook
from cloudcomponents.cdk_secret_key import SecretKey


class ReviewAppPipelineBuilderStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        account_id = cdk.Aws.ACCOUNT_ID
        region = cdk.Aws.REGION
        github_api_token = kwargs.pop("github_api_token")
        github_repo_url = kwargs.pop("github_repo_url")
        super().__init__(scope, construct_id, **kwargs)

        # IAM Role for the AWS Lambda function
        lambda_role = Role(
            self,
            'LambdaBuilderRole',
            assumed_by=ServicePrincipal('lambda.amazonaws.com')
        )
        lambda_role.add_managed_policy(
            ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )
        lambda_role.add_to_policy(PolicyStatement(
            actions=[
                'codebuild:CreateProject',
                'codebuild:StartBuild'
            ],
            resources=[f'arn:aws:codebuild:{region}:{account_id}:project/*']
        ))
        # Artifact bucket for AWS CodeBuild projects related to each branch
        artifact_bucket = s3.Bucket(
            self,
            'BranchArtifacts',
            encryption=s3.BucketEncryption.KMS_MANAGED,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # AWS Lambda and AWS CodeBuild projects' IAM Roles.
        # IAM Role for the feature branch AWS CodeBuild project.
        code_build_role = Role(
            self,
            'CodeBuildExecutionRole',
            assumed_by=ServicePrincipal('codebuild.amazonaws.com'))
        code_build_role.add_to_policy(PolicyStatement(
            actions=[
                'cloudformation:DescribeStacks', 'cloudformation:DeleteStack',
                'cloudformation:GetTemplate', 'cloudformation:CreateChangeSet',
                'cloudformation:DescribeChangeSet', 'cloudformation:DeleteChangeSet',
                'cloudformation:ExecuteChangeSet', 'cloudformation:DescribeStackEvents',
            ],
            resources=[f'arn:aws:cloudformation:{region}:{account_id}:stack/*/*']
        ))
        code_build_role.add_to_policy(PolicyStatement(
            actions=['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
            resources=[
                f'arn:aws:logs:{region}:{account_id}:log-group:/aws/codebuild/build-review-app-*',
                f'arn:aws:logs:{region}:{account_id}:log-group:/aws/codebuild/build-review-app-*:*']
        ))
        code_build_role.add_to_policy(PolicyStatement(
            actions=['s3:DeleteObject', 's3:PutObject', 's3:GetObject', 's3:ListBucket'],
            resources=[f'{artifact_bucket.bucket_arn}/*', f'{artifact_bucket.bucket_arn}']
        ))
        code_build_role.add_to_policy(PolicyStatement(
            actions=['sts:AssumeRole'],
            resources=[f'arn:*:iam::{account_id}:role/*'],
            conditions={
                "ForAnyValue:StringEquals": {
                    "iam:ResourceTag/aws-cdk:bootstrap-role": [
                        "image-publishing",
                        "file-publishing",
                        "deploy"
                    ]
                }
            }
        ))
        lambda_role.add_to_policy(PolicyStatement(
            actions=['iam:PassRole'],
            resources=[code_build_role.role_arn]
        ))

        # Define a lambda function to create and trigger a new pipeline on new PRs
        self.review_apps_builder_lambda = aws_lambda.Function(
            self,
            'LambdaPRHandler',
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            function_name='LambdaPipelineBuilderOnPR',
            handler='github_events.handler',
            code=aws_lambda.Code.from_asset(path.join(path.dirname(__file__), 'lambda_code')),
            environment={
                "ACCOUNT_ID": account_id,
                # "AWS_REGION": region,  # Region is already set by lambda
                "GH_API_TOKEN": github_api_token,
                "CODE_BUILD_ROLE_ARN": code_build_role.role_arn,
                "ARTIFACT_BUCKET": artifact_bucket.bucket_name,
            },
            role=lambda_role
        )

        # Connect GH webhooks to lambda
        self.gh_webhook_api = LambdaRestApi(self, "github-webhook", handler=self.review_apps_builder_lambda)
        self.gh_webhook_api.root.add_method("POST")

        github_api_token = SecretKey.from_plain_text(github_api_token)

        # @see https://developer.github.com/v3/activity/events/types/
        events = [
            "pull_request"
        ]

        GithubWebhook(
            self, "GithubWebhook",
            github_api_token=github_api_token,
            github_repo_url=github_repo_url,
            payload_url=self.gh_webhook_api.url,
            events=events,
            log_level="debug"
        )
