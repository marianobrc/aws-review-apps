from aws_cdk.core import Stack, Construct, SecretValue
import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codebuild as codebuild
import aws_cdk.aws_codepipeline_actions as codepipeline_actions


class PipelineStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        app_name = kwargs.pop("app_name", "myapp").lower().strip()
        deploy_env = kwargs.pop("deploy_env")
        backend_api = kwargs.pop("backend_api")
        # backend_workers = kwargs.pop("backend_workers")
        github_connection = kwargs.pop("github_connection")
        aws_github_secret_name = kwargs.pop("aws_github_secret_name")
        aws_docker_secret_name = kwargs.pop("aws_docker_secret_name")
        source_branch = kwargs.pop("source_branch", "master")
        ecr_repo = kwargs.pop("ecr_repo")
        super().__init__(scope, id, **kwargs)

        # Create an empty Pipeline
        pipeline_name = f"{app_name}BackendPipeline{deploy_env}"
        pipeline = codepipeline.Pipeline(
            self,
            pipeline_name,
            pipeline_name=pipeline_name
        )

        # Add a source stage to trigger the pipeline on github commits
        source_output = codepipeline.Artifact()
        pipeline.add_stage(
            stage_name="Source",
            actions=[
                codepipeline_actions.CodeStarConnectionsSourceAction(
                    action_name="GITHUB_SOURCE_ACTION",
                    branch=source_branch,
                    output=source_output,
                    connection_arn=github_connection.attr_connection_arn,
                    owner=SecretValue.secrets_manager(
                        secret_id=aws_github_secret_name,
                        json_field="GITHUB_OWNER"
                    ).to_string(),
                    repo=SecretValue.secrets_manager(
                        secret_id=aws_github_secret_name,
                        json_field="GITHUB_REPO"
                    ).to_string()
                )
            ]

        )

        # Add a stage to run automatic tests before deploying
        automatic_tests_spec = codebuild.BuildSpec.from_object(
            {
                "version": '0.2',
                "phases": {
                    "install": {
                        "runtime-versions": {
                            "python": "3.8"
                        },
                        "commands": [
                            "echo 'Installing dependencies..'",
                            "pip3 install --no-cache-dir -r ./backend/requirements/base.txt",
                            "pip3 install --no-cache-dir -r ./backend/requirements/prod.txt"
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo 'Running tests..'",
                            "cd ./backend/",
                            "python3 manage.py test"
                        ]
                    },
                }
            }
        )
        # Build the env vars based on the backend API env vars
        test_env_vars = {
            k: codebuild.BuildEnvironmentVariable(value=v)
            for k, v in backend_api.env_vars.items()
        }
        # AWS API keys are passed by the Secrets Manager
        test_env_vars["AWS_ACCESS_KEY_ID"] = codebuild.BuildEnvironmentVariable(
            type=codebuild.BuildEnvironmentVariableType.SECRETS_MANAGER,
            value=backend_api.aws_api_key_id_secret_name
        )
        test_env_vars["AWS_SECRET_ACCESS_KEY"] = codebuild.BuildEnvironmentVariable(
            type=codebuild.BuildEnvironmentVariableType.SECRETS_MANAGER,
            value=backend_api.aws_api_key_secret_secret_name
        )
        # Override settings module env var to run unittests
        test_env_vars["DJANGO_SETTINGS_MODULE"] = codebuild.BuildEnvironmentVariable(
            type=codebuild.BuildEnvironmentVariableType.PLAINTEXT,
            value="quickpay.settings.ci_tests"
        )

        automatic_tests_project = codebuild.Project(
            self,
            f"{app_name}TestCodeBuildProject{deploy_env}",
            vpc=backend_api.ecs_cluster.vpc,  # Same vpc as the backend to be able to access the DB
            build_spec=automatic_tests_spec,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_3_0,
                privileged=True
            ),
            environment_variables=test_env_vars
        )
        pipeline.add_stage(
            stage_name="Test",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name="TEST_ACTION",
                    input=source_output,  # Takes the source code from a previous stage
                    project=automatic_tests_project
                )
            ]
        )

        # Add a build stage to build docker images and store them in ECR
        build_output = codepipeline.Artifact()
        build_spec = codebuild.BuildSpec.from_object(
            {
                "version": '0.2',
                "phases": {
                    "pre_build": {
                        "commands": [
                            'aws --version',
                            'COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)',
                            'IMAGE_TAG=${COMMIT_HASH:=latest}'
                        ]
                    },
                    "build": {
                        "commands": [
                            'echo $DOCKER_PASSWORD | docker login --username $DOCKER_USERNAME --password-stdin',
                            'docker build -t $REPOSITORY_URI:latest -f ./backend/docker/prod/django/Dockerfile ./backend/',
                            'docker tag $REPOSITORY_URI:latest $REPOSITORY_URI:$IMAGE_TAG',
                        ]
                    },
                    "post_build": {
                        "commands": [
                            '$(aws ecr get-login --region ${AWS_DEFAULT_REGION} --no-include-email |  sed \'s|https://||\')',
                            'docker push $REPOSITORY_URI:latest',
                            'docker push $REPOSITORY_URI:$IMAGE_TAG',
                            'printf "[{\\"name\\":\\"${CONTAINER_NAME}\\",\\"imageUri\\":\\"${REPOSITORY_URI}:latest\\"}]" > imagedefinitions.json'
                        ]
                    }
                },
                "artifacts": {
                    "files": [
                        'imagedefinitions.json'
                    ]
                }
            }
        )
        codebuild_project = codebuild.Project(
            self,
            f"{app_name}BuildCodeBuildProject{deploy_env}",
            vpc=backend_api.ecs_cluster.vpc,  # Same vpc as the backend
            build_spec=build_spec,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_2_0,
                privileged=True
            ),
            environment_variables={
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(value=ecr_repo.repository_uri_for_tag()),
                "CONTAINER_NAME": codebuild.BuildEnvironmentVariable(value=backend_api.container_name),
                "DOCKER_USERNAME": codebuild.BuildEnvironmentVariable(
                    type=codebuild.BuildEnvironmentVariableType.SECRETS_MANAGER,
                    value=f"{aws_docker_secret_name}:DOCKER_USERNAME"
                ),
                "DOCKER_PASSWORD": codebuild.BuildEnvironmentVariable(
                    type=codebuild.BuildEnvironmentVariableType.SECRETS_MANAGER,
                    value=f"{aws_docker_secret_name}:DOCKER_PASSWORD"
                )
            }
        )
        # Grant permissions to codebuild to access the ECR repo
        ecr_repo.grant_pull_push(codebuild_project.grant_principal)
        pipeline.add_stage(
            stage_name="Build",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name="BUILD_ACTION",
                    input=source_output,  # Takes the source code from a previous stage
                    outputs=[build_output],
                    project=codebuild_project
                )
            ]
        )

        # Add a Deploy stage to update ECS service & tasks with the new docker images
        ecs_api_service = backend_api.alb_fargate_service.service
        # ecs_workers_service = backend_workers.workers_fargate_service.service
        ecr_repo.grant_pull(ecs_api_service.task_definition.execution_role)
        #ecr_repo.grant_pull(ecs_workers_service.task_definition.execution_role)
        pipeline.add_stage(
            stage_name="Deploy",
            actions=[
                codepipeline_actions.EcsDeployAction(
                    action_name="DEPLOY_API_ACTION",
                    input=build_output,  # Takes the imagedefinitions.json generated in the build stage
                    service=ecs_api_service
                ),
                # codepipeline_actions.EcsDeployAction(
                #     action_name="DEPLOY_WORKERS_ACTION",
                #     input=build_output,  # Takes the imagedefinitions.json generated in the build stage
                #     service=ecs_workers_service
                # )
            ]
        )
