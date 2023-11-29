import aws_cdk as cdk
from constructs import Construct
from aws_cdk.pipelines import CodePipeline, CodePipelineSource, ShellStep
from src.stage import PipelineStage, PipelineStageModel


class PipelineStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, 
                 config: PipelineStageModel, 
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        repo = cdk.aws_codecommit.Repository.from_repository_name(self, "MyRepo", 
            config.infra_repository_name)

        pipeline = CodePipeline(self, "Pipeline",
            pipeline_name="{}-infra".format(config.project_name),
            cross_account_keys=True,
            synth=ShellStep("Synth",
                input=CodePipelineSource.code_commit(repo, config.infra_repository_branch),
                commands=["npm install -g aws-cdk",
                          "python -m pip install -r requirements.txt",
                          "cdk synth"]))
        
        if config.test:
            env_test = cdk.Environment(
                account=config.test.account,
                region=config.test.region)
            pipeline.add_stage(
                PipelineStage(self, "{}-test".format(config.project_name), 
                        'test',
                        config.project_name,
                        config.test, 
                        env=env_test))
    
        if config.prod:
            env_prod = cdk.Environment(
                account=config.prod.account,
                region=config.prod.region)
            pipeline.add_stage(
                PipelineStage(self, "{}-test".format(config.project_name),
                        'prod',
                        config.project_name, 
                        config.prod, 
                        env=env_prod))
