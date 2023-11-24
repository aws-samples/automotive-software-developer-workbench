from constructs import Construct
from aws_cdk import (
    Stack,
    aws_ssm as ssm,
    aws_iam as iam,
)
from src.image_builder import ImageBuilder, ComponentModel, AmiModel
from pydantic import BaseModel
from typing import Optional, List
            
class AmiFactoryModel(BaseModel):
    instance_types: List[str]
    components: Optional[List[ComponentModel]] = []
    amis: List[AmiModel]
              
class AmiFactoryStack(Stack):
  def __init__(self, scope: Construct, construct_id: str, 
        env_name: str, 
        project_name: str, 
        config: AmiFactoryModel, 
        **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)
    
    builder = ImageBuilder(self, 'ImageBuilder', 
        env_name, 
        project_name, 
        config.instance_types)

    try:
        # read the first line from download-url.txt file
        with open("./download-url.txt", "r") as f:
            download_url = f.readline()
            parameter = ssm.StringParameter(self, "DownloadUrl",
                                    parameter_name="download_url",
                                    string_value=download_url)
            parameter.grant_read(builder.role)
    except FileNotFoundError:
        print('[WARNING] File download-url.txt not found')
        pass

    builder.role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name(
            'AWSCodeCommitFullAccess'));
    
    for component in config.components:
        builder.add_component(component)
    
    for ami in config.amis:
        builder.add_ami(ami)

