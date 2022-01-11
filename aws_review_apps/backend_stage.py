import os
from typing import Any
from aws_cdk import core as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ssm as ssm
from .docker_registry_stack import DockerRegistryStack
from .database_stack import DatabaseStack
from .static_files_stack import StaticFilesStack
from .backend_api_stack import BackendAPIStack


class BackendStage(cdk.Stage):
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
        db_auto_pause_minutes: int=5, # Pause aurora computing capacity when idle to save costs
        certificate_arn: str=None, # To use HTTPS
        **kwargs: Any,
    ):
        super().__init__(scope, id_, **kwargs)
        # Statefull resources
        stateful = cdk.Stack(self, "Stateful")
        # Get the vpc to deploy the stage
        vpc_id = ssm.StringParameter.value_from_lookup(stateful, "/Networking/VPCID")
        vpc = ec2.Vpc.from_lookup(stateful, "VPC", vpc_id=vpc_id)
        registry = DockerRegistryStack(
            stateful,
            f"{app_name}DockerRegistryStack{deploy_env}",
            app_name=app_name,
            deploy_env=deploy_env,
            env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
        )
        db = DatabaseStack(
            stateful,
            f"{app_name}DatabaseStack{deploy_env}",
            app_name=app_name,
            deploy_env=deploy_env,
            vpc=vpc,
            auto_pause_minutes=db_auto_pause_minutes,
            env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))
        )
        # Serve static files for the Backoffice (django-admin)
        static_files = StaticFilesStack(
            stateful,
            f"{app_name}StaticFilesStack{deploy_env}",
            app_name=app_name,
            deploy_env=deploy_env,
            env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))
        )
        # Stateless resources
        stateless = cdk.Stack(self, "Stateless")
        api = BackendAPIStack(
            stateless,
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
            static_files=static_files,
            vpc=vpc,
            env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))
        )
