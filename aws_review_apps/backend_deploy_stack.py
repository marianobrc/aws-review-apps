import os
from typing import Any
from aws_cdk import core as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ssm as ssm
from .database_stack import DatabaseStack
from .static_files_stack import StaticFilesStack
from .backend_api_stack import BackendAPIStack


class BackendStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id_: str,
        *,
        app_name: str,
        deploy_env: str,
        django_settings: str,
        django_secret_name: str,
        db_secret_name: str,
        aws_api_key_id_secret_name: str,
        aws_api_key_secret_secret_name: str,
        task_cpu: int,
        task_desired_count: int,
        min_scaling_capacity: int,
        max_scaling_capacity: int,
        task_memory_mib: int,
        db_auto_pause_minutes: int = 5,  # Pause aurora computing capacity when idle to save costs
        certificate_arn: str = None,  # To use HTTPS
        **kwargs: Any,
    ):
        super().__init__(scope, id_, **kwargs)
        # Statefull resources
        # Get the vpc to deploy the stage
        vpc_id = ssm.StringParameter.value_from_lookup(self, "/Networking/VPCID")
        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)
        self.db = DatabaseStack(
            self,
            f"{app_name}DatabaseStack{deploy_env}",
            app_name=app_name,
            deploy_env=deploy_env,
            vpc=vpc,
            auto_pause_minutes=db_auto_pause_minutes,
            #env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))
        )
        # Serve static files for the Backoffice (django-admin)
        self.static_files = StaticFilesStack(
            self,
            f"{app_name}StaticFilesStack{deploy_env}",
            app_name=app_name,
            deploy_env=deploy_env,
            #env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))
        )
        # Stateless resources
        self.api = BackendAPIStack(
            self,
            f"BackendAPIStack{deploy_env}",
            app_name=app_name,
            deploy_env=deploy_env,
            certificate_arn=certificate_arn,
            django_settings=django_settings,
            django_secret_name=django_secret_name,
            db_secret_name=db_secret_name,
            aws_api_key_id_secret_name=aws_api_key_id_secret_name,
            aws_api_key_secret_secret_name=aws_api_key_secret_secret_name,
            task_cpu=task_cpu,
            task_desired_count=task_desired_count,
            min_scaling_capacity=min_scaling_capacity,
            max_scaling_capacity=max_scaling_capacity,  # Keep ecs tasks count at minimum in staging
            task_memory_mib=task_memory_mib,
            static_files=self.static_files,
            vpc=vpc,
            #env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))
        )
