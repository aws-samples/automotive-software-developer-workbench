import sys
import re
import yaml
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_imagebuilder as imagebuilder,
    aws_ssm as ssm,
)
from cdk_ec2_key_pair import KeyPair
from botocore.exceptions import ClientError
import boto3

def get_base_ami(base_amis_mapping_document: str, region: str) -> str:
    try:
        with open(base_amis_mapping_document, "r") as f:
            _mapping = json.load(f)
    except FileNotFoundError as e:
        print(f'[WARNING] File {base_amis_mapping_document} not found')
        raise e

    if not region in _mapping.keys():
        print(f'[ERROR] The AMI is not available for region {region}')
        sys.exit(1)
    else:
        ami_id = _mapping[region]

    try:
        client = boto3.client('ec2', region)
        ret = client.describe_images(ImageIds=[ami_id])
        if len(ret['Images']) == 0:
            print(f'[ERROR] You don\'t have permission to use {ami_id}')
            sys.exit(1)
            
    except ClientError as e:
        if e.response['Error']['Code'].startswith('InvalidAMIID.'):
            print(f'[ERROR] The project blueprint {ami_id} is invalid')
            return
        raise e
    
    return ami_id

class ComponentModel(BaseModel):
    name: str
    document: str
    platform: str
    version: str
        
class VolumeModel(BaseModel):
    size: int = Field(gt=8)
    device_name: str
    type: Optional[str] = Field(default='gp3', pattern=r'^(gp2)|(gp3)$')
    
class AmiModel(BaseModel):
    name: str
    description: str
    version: str
    platform: str
    base_amis_mapping_document: str
    components: List[str]
    volumes: List[VolumeModel]
    distributions: List[str]

class ImageBuilder(Construct):
    def __init__(self, scope: Construct, id: str, 
                 env_name: str, 
                 project_name: str,
                 instance_types: List[str]):
        super().__init__(scope, id)
        
        self._components = []
        self._amis = []
        
        self._env_name = env_name
        self._project_name = project_name
        name = f'{project_name}-{env_name}-infrastructure';

        self.role = iam.Role(self, 'Role',
            assumed_by = iam.ServicePrincipal('ec2.amazonaws.com'),
            role_name = name)

        self.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                'AmazonSSMManagedInstanceCore'));
        self.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                'EC2InstanceProfileForImageBuilder'));
        self.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                'EC2InstanceProfileForImageBuilderECRContainerBuilds'));

        instance_profile = iam.CfnInstanceProfile(self, 'InstanceProfile', 
            instance_profile_name = name,
            roles = [ self.role.role_name ])
        
        key = KeyPair(self, "KeyPair",
            name=name,
            store_public_key=True)
        
        #TBD: include specific VPC configuration, because run will fail if no default VPC
        configuration  = imagebuilder.CfnInfrastructureConfiguration(self, 'Configuration', 
              name = f'{project_name}-{env_name}',
              instance_types = instance_types,
              instance_profile_name = name,
              key_pair = key.key_pair_name,
              terminate_instance_on_failure = False)
        self.attr_arn = configuration.attr_arn
        
        configuration.add_dependency(instance_profile)

    def add_component(self, component: ComponentModel):
        with open(f"{component.document}", "r") as f:
            data = f.read()
            document = yaml.load(data, Loader=yaml.FullLoader)
            # remove spaces and hyphen and uppercase the first letter of each word
            resource_id = document['name']. \
                replace('-', ' '). \
                title(). \
                replace(' ', '')
            self._components.append(
                imagebuilder.CfnComponent(self, f'Component{resource_id}', 
                    name=component.name,
                    platform=component.platform,
                    version=component.version,
                    description=document['description'],
                    data = data))

    def add_ami(self, ami: AmiModel):
        region = Stack.of(self).region
        account = Stack.of(self).account
        parent_ami = get_base_ami(base_amis_mapping_document = ami.base_amis_mapping_document, region = region)
        
        block_device_mappings = []
        for volume in ami.volumes:
            block_device_mappings.append(
                imagebuilder.CfnImageRecipe.InstanceBlockDeviceMappingProperty(
                    device_name=volume.device_name,
                    ebs=imagebuilder.CfnImageRecipe.EbsInstanceBlockDeviceSpecificationProperty(
                        delete_on_termination=True,
                        encrypted=False,
                        volume_size=volume.size,
                        volume_type=volume.type)))
        
        components_configurations = []
        for component in ami.components:
            if re.match('^[a-zA-Z]+:component/', component):
                components_configurations.append(
                    imagebuilder.CfnImageRecipe.ComponentConfigurationProperty(
                        component_arn=f'arn:aws:imagebuilder:{region}:{component}'))
            else:
                components_configurations.append(
                    imagebuilder.CfnImageRecipe.ComponentConfigurationProperty(
                        component_arn=f'arn:aws:imagebuilder:{region}:{account}:component/{component}'))
            
        image_recipe = imagebuilder.CfnImageRecipe(self, 'ImageRecipe',
            name = ami.name,
            description=ami.description,
            version = ami.version,
            components = components_configurations,
            parent_image = parent_ami,
            block_device_mappings=block_device_mappings)
        
        for component in self._components:
            image_recipe.add_dependency(component)
            # TBD: need to check that components exists and are compatible with the recipe
        
        ami_dist_conf = imagebuilder.CfnDistributionConfiguration.AmiDistributionConfigurationProperty(
            name="{}{}".format(ami.name, "{{ imagebuilder:buildDate }}"))
        
        distributions = []
        for region in ami.distributions:
            distributions.append(
                imagebuilder.CfnDistributionConfiguration.DistributionProperty(
                    region=region.replace('_','-'),
                    ami_distribution_configuration=ami_dist_conf))
        
        self._amis.append(imagebuilder.CfnImagePipeline(self, 'ImagePipeline', 
            name = ami.name,
            image_recipe_arn = image_recipe.attr_arn,
            infrastructure_configuration_arn = self.attr_arn,
            enhanced_image_metadata_enabled=False, #https://docs.aws.amazon.com/imagebuilder/latest/userguide/troubleshooting.html#ts-ssm-mult-inventory
            distribution_configuration_arn = imagebuilder.CfnDistributionConfiguration(
                self, 'DistributionConfiguration',
                name=ami.name,
                distributions=distributions).attr_arn))

   

