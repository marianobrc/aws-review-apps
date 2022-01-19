from aws_cdk import core as cdk
from aws_cdk import (aws_rds as rds, aws_ec2 as ec2)


class DatabaseStack(cdk.NestedStack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        app_name = kwargs.pop("app_name", "myapp").lower().strip()
        deploy_env = kwargs.pop("deploy_env", "PROD").upper()
        vpc = kwargs.pop("vpc")  # required
        auto_pause_minutes = kwargs.pop("auto_pause_minutes", 30)
        backup_retention_days = kwargs.pop("backup_retention_days", 1)
        super().__init__(scope, construct_id, **kwargs)

        # Our network in the cloud
        self.aurora_serverless_db = rds.ServerlessCluster(
            self,
            f"{app_name}AuroraServerlessCluster{deploy_env}",
            engine=rds.DatabaseClusterEngine.AURORA_POSTGRESQL,
            vpc=vpc,
            backup_retention=cdk.Duration.days(backup_retention_days),  # 1 day retention is free
            cluster_identifier=f"{app_name}dbcluster{deploy_env}",
            deletion_protection=True,
            enable_data_api=True,  # Allow running queries in AWS console (free)
            parameter_group=rds.ParameterGroup.from_parameter_group_name(  # Specify the postgresql version
                self,
                f"{app_name}AuroraDBParameterGroup{deploy_env}",
                "default.aurora-postgresql10"  # Only this version is supported for Aurora Serverless now
            ),
            scaling=rds.ServerlessScalingOptions(
                auto_pause=cdk.Duration.minutes(auto_pause_minutes),  # The computing power is shutdown after 10 minutes of inactivity to save costs
                min_capacity=rds.AuroraCapacityUnit.ACU_2,  # The minimal capacity for postgresql allowed here is 2
                max_capacity=rds.AuroraCapacityUnit.ACU_2   # Limit scaling to limit costs
            ),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE)   # The DB is only accessible from private subnets
        )
        # Allow ingress traffic from ECS tasks SG into Aurora Cluster SG
        self.aurora_serverless_db.connections.allow_default_port_from_any_ipv4(
            description="Services in private subnets can access the DB"
        )
