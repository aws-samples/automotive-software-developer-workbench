import os
import yaml
from aws_cdk import App, Environment, Stack
from pydantic import BaseModel
from typing import Optional
from src.pipeline import PipelineStack, PipelineStageModel
from src.software_factory import SoftwareFactoryStack
from src.ami_factory import AmiFactoryStack


class AppModel(BaseModel):
    project_name: str
    infra_repository_name: Optional[str] = None
    infra_repository_branch: Optional[str] = None
    dev: PipelineStageModel
    test: Optional[PipelineStageModel] = None
    prod: Optional[PipelineStageModel] = None

app = App()

config_filename = app.node.try_get_context('config')
if app.node.try_get_context('config') != None:
    print(f'Configuration file: {config_filename}')
    with open(config_filename, 'r') as file:
        config = AppModel(**yaml.safe_load(file))
        
        env_dev = Environment(account=config.dev.account, region=config.dev.region)

        if config.infra_repository_name:
            PipelineStack(app, "{}-pipeline".format(config.project_name),
                config,
                env=env_dev)
        
        if config.dev.ami_factory: 
            AmiFactoryStack(app, "{}-dev-ami-factory".format(config.project_name),
                'dev',
                config.project_name,
                config.dev.ami_factory,
                env=env_dev)
        
        if config.dev.software_factory: 
            SoftwareFactoryStack(app, "{}-dev-software-factory".format(config.project_name),
                'dev',
                config.project_name,
                config.dev.software_factory,
                env=env_dev)
else:
    Stack(app, "DummyStack")

app.synth()