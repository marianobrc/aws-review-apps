import os
from aws_cdk import core as cdk
from aws_cdk import (
    aws_ecs as ecs, aws_ecs_patterns as ecs_patterns, aws_secretsmanager as secretsmanager, aws_ssm as ssm,
    aws_elasticloadbalancingv2 as elbv2, aws_certificatemanager as acm
)


class BackendAPIStack(cdk.NestedStack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        app_name = kwargs.pop("app_name", "myapp").lower().strip()
        vpc = kwargs.pop("vpc")
        deploy_env = kwargs.pop("deploy_env", "PROD").upper()
        certificate_arn = kwargs.pop("certificate_arn", None)
        django_settings = kwargs.pop("django_settings", "").lower().strip()
        django_secret_name = kwargs.pop("django_secret_name")
        db_secret_name = kwargs.pop("db_secret_name")  # Name of a secret in Secrets Manager containing DB credentials
        self.aws_api_key_id_secret_name = kwargs.pop("aws_api_key_id_secret_name")  # Name of a secret in Secrets Manager containing AWS API Keys
        self.aws_api_key_secret_secret_name = kwargs.pop("aws_api_key_secret_secret_name")
        static_files = kwargs.pop("static_files")
        task_cpu = kwargs.pop("task_cpu", 256)
        task_desired_count = kwargs.pop("task_desired_count", 2)
        min_scaling_capacity = kwargs.pop("min_scaling_capacity", 1)
        max_scaling_capacity = kwargs.pop("max_scaling_capacity", 2)
        task_memory_mib = kwargs.pop("task_memory_mib", 1024)
        super().__init__(scope, construct_id, **kwargs)

        self.ecs_cluster = ecs.Cluster(self, f"{app_name}ECSCluster{deploy_env}", vpc=vpc)

        # Prepare environment variables
        self.container_name = f"{app_name}_api_{deploy_env.lower()}"
        self.env_vars = {
            "DJANGO_SETTINGS_MODULE": django_settings,
            "DJANGO_DEBUG": "False",
            "DB_AWS_SECRET_NAME": db_secret_name,
            "AWS_DATA_PATH": "/home/mybackend/botocore/",
            "AWS_ACCOUNT_ID": os.getenv('CDK_DEFAULT_ACCOUNT'),
            "AWS_STORAGE_BUCKET_NAME": static_files.s3_bucket.bucket_name,
            "CLOUDFRONT_URL": static_files.cloudfront_distro.distribution_domain_name,
            "DJANGO_SECRET_AWS_SECRET_NAME": django_secret_name
        }
        # SSL cert is optional (only required for custom domains)
        if certificate_arn:
            domain_ssl_cert = acm.Certificate.from_certificate_arn(
                self, f"{app_name}BackendAPICertificate{deploy_env}",
                certificate_arn=certificate_arn
            )
            protocol = elbv2.ApplicationProtocol.HTTPS
        else:
            domain_ssl_cert=None
            protocol=elbv2.ApplicationProtocol.HTTP
        # Create the load balancer, ECS service and tasks
        self.alb_fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, f"{app_name}BackendAPI{deploy_env}",
            protocol=protocol,
            certificate=domain_ssl_cert,
            platform_version=ecs.FargatePlatformVersion.VERSION1_4,
            cluster=self.ecs_cluster,  # Required
            cpu=task_cpu,  # Default is 256
            memory_limit_mib=task_memory_mib,  # Default is 512
            desired_count=task_desired_count,  # Default is 1
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset(
                    directory="backend/",
                    file="docker/prod/django/Dockerfile"
                ),
                container_name=self.container_name,
                container_port=8000,
                environment=self.env_vars,
                secrets={
                    "AWS_ACCESS_KEY_ID": ecs.Secret.from_secrets_manager(
                        secretsmanager.Secret.from_secret_name_v2(
                            self, f"{app_name}AWSAccessKeyIDSecret",
                            secret_name=self.aws_api_key_id_secret_name
                        )
                    ),
                    "AWS_SECRET_ACCESS_KEY": ecs.Secret.from_secrets_manager(
                        secretsmanager.Secret.from_secret_name_v2(
                            self, f"{app_name}AWSAccessKeySecretSecret",
                            secret_name=self.aws_api_key_secret_secret_name,
                        )
                    ),
                }
            ),
            public_load_balancer=True
        )
        # Set the health checks settings
        self.alb_fargate_service.target_group.configure_health_check(
            path="/status/",
            healthy_threshold_count=3,
            unhealthy_threshold_count=2
        )
        # Autoscaling based on CPU utilization
        scalable_target = self.alb_fargate_service.service.auto_scale_task_count(
            min_capacity=min_scaling_capacity,
            max_capacity=max_scaling_capacity
        )
        scalable_target.scale_on_cpu_utilization(
            f"{app_name}CpuScaling{deploy_env}",
            target_utilization_percent=75,
        )
