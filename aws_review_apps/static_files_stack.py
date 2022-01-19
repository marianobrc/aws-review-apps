from aws_cdk import core as cdk
from aws_cdk import (aws_s3 as s3, aws_cloudfront as cloudfront)


class StaticFilesStack(cdk.NestedStack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        app_name = kwargs.pop("app_name", "myapp").lower().strip()
        deploy_env = kwargs.pop("deploy_env", "PROD").upper()
        super().__init__(scope, construct_id, **kwargs)

        # Create a private bucket
        self.s3_bucket = s3.Bucket(
            self, f"{app_name}StaticFilesBucket{deploy_env}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # Make the bucket accessible through a cloudfront distribution only
        self.oai = cloudfront.OriginAccessIdentity(
            self, f"{app_name}StaticFilesBucketOAI{deploy_env}",
            comment="OAI to access backend static files."
        )
        self.s3_bucket.grant_read(self.oai)
        self.cloudfront_distro = cloudfront.CloudFrontWebDistribution(
            self, f"{app_name}StaticFilesCloudFrontDistro{deploy_env}",
            origin_configs=[
                cloudfront.SourceConfiguration(
                    s3_origin_source=cloudfront.S3OriginConfig(
                        s3_bucket_source=self.s3_bucket,
                        origin_access_identity=self.oai
                    ),
                    behaviors=[
                        cloudfront.Behavior(is_default_behavior=True)
                    ],
                )
            ]
        )
