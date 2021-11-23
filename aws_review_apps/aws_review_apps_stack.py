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
from cloudcomponents.cdk_github_webhook import GithubWebhook
from cloudcomponents.cdk_secret_key import SecretKey


class AwsReviewAppsStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        github_api_token = kwargs.pop("github_api_token")
        github_repo_url = kwargs.pop("github_repo_url")
        super().__init__(scope, construct_id, **kwargs)
        # Define a lambda function to create and trigger a new pipeline on new feature branch creation

        # IAM Role for the AWS Lambda function
        lambda_role = Role(
            self,
            'LambdaPipelineBuilderRole',
            assumed_by=ServicePrincipal('lambda.amazonaws.com')
        )
        lambda_role.add_managed_policy(
            ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )
        # lambda_role.add_to_policy(PolicyStatement(
        #     actions=[
        #         'codebuild:CreateProject',
        #         'codebuild:StartBuild'
        #     ],
        #     resources=[f'arn:aws:codebuild:{region}:{account}:project/*']
        # ))

        # The lambda function
        self.review_apps_builder_lambda = aws_lambda.Function(
            self,
            'LambdaPipelineBuilderOnBranchCreateStack',
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            function_name='LambdaPipelineBuilderOnBranchCreate',
            handler='github_events.handler',
            code=aws_lambda.Code.from_asset(path.join(path.dirname(__file__), 'lambda_code')),
            role=lambda_role
        )

        # Connect GH webhooks to lambda
        self.gh_webhook_api = LambdaRestApi(self, "github-webhook", handler=self.review_apps_builder_lambda)
        self.gh_webhook_api.root.add_method("POST")

        github_api_token = SecretKey.from_plain_text(github_api_token)

        # @see https://developer.github.com/v3/activity/events/types/
        events = [
            "create",
            "delete",
            "push",
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
