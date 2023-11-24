import sys
import re
import yaml
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


def get_dcv_base_ami(region: str) -> str:
    # NICE DCV for Windows (g3, g4 and g5 graphics-intensive instances)
    # https://aws.amazon.com/marketplace/pp/prodview-3hjza2gbnepkg
    _mapping = {
        "af-south-1": "ami-03a28b1d80470d9f1",
        "ap-east-1": "ami-0e018cb29212e3c2c",
        "ap-northeast-1": "ami-0185f9436c63606d6",
        "ap-northeast-2": "ami-018fe3f0c542fec79",
        "ap-south-1": "ami-062e11d3e0f0de270",
        "ap-southeast-1": "ami-0c25850f7aa9d44d4",
        "ap-southeast-2": "ami-05dd820eeb3633632",
        "ca-central-1": "ami-0f39324ccb81a203f",
        "eu-central-1": "ami-040f19c78276862a1",
        "eu-north-1": "ami-04344deb81ca3b0f5",
        "eu-south-1": "ami-0a545a4f9bd3857ce",
        "eu-west-1": "ami-0b15c766ea9a1d61e",
        "eu-west-2": "ami-012276bb2f5e8832e",
        "eu-west-3": "ami-0e104db71d5e790ab",
        "me-south-1": "ami-0f10781a19b675ecc",
        "sa-east-1": "ami-0bfe6221c55cc4dad",
        "us-east-1": "ami-0d0bc8a4d63535f70",
        "us-east-2": "ami-07b97db455511a206",
        "us-west-1": "ami-0e69120f94216db9f",
        "us-west-2": "ami-0373b9a656ee59f1b",
    }
    if not region in _mapping.keys():
        print(f"DCV AMI is not available for region {region} is not supported.")
        sys.exit(1)
    else:
      return _mapping[region]

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
        parent_ami = get_dcv_base_ami(region = region)
        
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
            block_device_mappings=block_device_mappings,
            working_directory="C:\\")
        
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
            distribution_configuration_arn = imagebuilder.CfnDistributionConfiguration(
                self, 'DistributionConfiguration',
                name=ami.name,
                distributions=distributions).attr_arn))

   

