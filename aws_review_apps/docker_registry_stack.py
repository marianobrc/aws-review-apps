from aws_cdk import core as cdk
from aws_cdk import (aws_ecr as ecr, )


class DockerRegistryStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        app_name = kwargs.pop("app_name", "myapp").lower().strip()
        deploy_env = kwargs.pop("deploy_env", "PROD").upper()
        super().__init__(scope, construct_id, **kwargs)
        self.ecr_repo = ecr.Repository(
            self,
            f'{app_name}ECRRepository{deploy_env}',
            repository_name=f"{app_name}-{deploy_env.lower()}"  # Important: keep teh name lowercase
        )

