import os
from aws_cdk import Stage
from constructs import Construct
from pydantic import BaseModel, Field
from typing import Optional
from src.software_factory import SoftwareFactoryStack, SoftwareFactoryModel
from src.ami_factory import AmiFactoryStack, AmiFactoryModel

class PipelineStageModel(BaseModel):
    account: Optional[str] = Field(
        default=os.getenv('CDK_DEFAULT_ACCOUNT'))
    region: Optional[str] = Field(
        default=os.getenv('CDK_DEFAULT_REGION'))
    ami_factory: Optional[AmiFactoryModel] = None
    software_factory: Optional[SoftwareFactoryModel] = None

class PipelineStage(Stage):
    def __init__(self, scope: Construct, construct_id: str, 
                env_name: str, 
                project_name: str, 
                config: PipelineStageModel, 
                **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        if config.ami_factory:
            AmiFactoryStack(self, "ami-factory", 
                env_name, project_name, config.ami_factory)

        if config.software_factory:    
            SoftwareFactoryStack(self, "sw-factory", 
                env_name, project_name, config.software_factory)
    

    