from constructs import Construct
from pydantic import BaseModel, Field
from typing import Optional, List
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_s3 as s3)
import json
from botocore.exceptions import ClientError
import boto3

        
class AmiIdsModel(BaseModel): 
    af_south_1: Optional[str] = None
    ap_east_1: Optional[str] = None
    ap_northeast_1: Optional[str] = None
    ap_northeast_2: Optional[str] = None
    ap_south_1: Optional[str] = None
    ap_southeast_1: Optional[str] = None
    ap_southeast_2: Optional[str] = None
    ca_central_1: Optional[str] = None
    eu_central_1: Optional[str] = None
    eu_north_1: Optional[str] = None
    eu_south_1: Optional[str] = None
    eu_west_1: Optional[str] = None
    eu_west_2: Optional[str] = None
    eu_west_3: Optional[str] = None
    me_south_1: Optional[str] = None
    sa_east_1: Optional[str] = None
    us_east_1: Optional[str] = None
    us_east_2: Optional[str] = None
    us_west_1: Optional[str] = None
    us_west_2: Optional[str] = None
    
class AmiModel(BaseModel):
    ami_ids: AmiIdsModel

class VolumeModel(BaseModel):
    size: int = Field(gt=8)
    device_name: str

class WorkbenchModel(BaseModel):
    instance_type: str
    ami: AmiModel
    user_data: Optional[List[str]] = []
    volumes: List[VolumeModel]
    
class Workbench(Construct):
    def __init__(self, scope: Construct, id: str, 
                 env_name: str, 
                 project_name: str,
                 config: WorkbenchModel,
                 vpc: ec2.Vpc,
                 artifact: s3.Bucket):
        super().__init__(scope, id)
        
        self.role = iam.Role(self, "Role",
            description="IAM role assigned to the Workbench",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal(f"ssm.amazonaws.com"),
                iam.ServicePrincipal(f"ec2.amazonaws.com")))
        
        self.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))
        artifact.grant_read(self.role)

        # Check that an AMI ID is available in this region
        region = Stack.of(self).region
        ami_id = getattr(config.ami.ami_ids, region.replace('-','_'))
        if ami_id == None:
            print('[ERROR] This project blueprint is not supported in this region')
            exit(1)
        try:
            client = boto3.client('ec2', region)
            ret = client.describe_images(ImageIds=[ami_id])
            if len(ret['Images']) == 0:
                print(f'[WARNING] You don\'t have permission to use {ami_id}')
                return
        except ClientError as e:
            if e.response['Error']['Code'].startswith('InvalidAMIID.'):
                print(f'[ERROR] The project blueprint {ami_id} is invalid')
                return
            raise e
        
        self.sg = ec2.SecurityGroup(self, "SecurityGroup", vpc=vpc)
        # self.sg.add_ingress_rule(
        #     peer=ec2.Peer.any_ipv4(), 
        #     connection=ec2.Port.tcp(3389))
        
        block_devices = []
        for volume in config.volumes:
            block_devices.append(
                ec2.BlockDevice(
                    device_name=volume.device_name,
                    volume=ec2.BlockDeviceVolume.ebs(volume.size)))
        
        machine_image = ec2.MachineImage.generic_windows({region: ami_id})

        self.instance = ec2.Instance(self, 'Instance',
            instance_name=f'{project_name}-{env_name}-workbench',
            instance_type=ec2.InstanceType(config.instance_type),
            machine_image=machine_image,
            role=self.role,
            security_group=self.sg,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            user_data=ec2.UserData.for_windows(persist=False))

        region = Stack.of(self).region
        self.instance.user_data.add_commands(
            f"[Environment]::SetEnvironmentVariable('AWS_DEFAULT_REGION', '{region}', 'Machine')")
        self.instance.user_data.add_commands(
            f"[Environment]::SetEnvironmentVariable('AWS_DEFAULT_REGION', '{region}')")
        self.instance.user_data.add_commands(
            f"[Environment]::SetEnvironmentVariable('ARTIFACT_BUCKET_NAME', '{artifact.bucket_name}', 'Machine')")
        self.instance.user_data.add_commands(
            f"[Environment]::SetEnvironmentVariable('ARTIFACT_BUCKET_NAME', '{artifact.bucket_name}')")
        
        for cmd in config.user_data:
            self.instance.user_data.add_commands(cmd)
        
        url=f'https://{region}.console.aws.amazon.com/systems-manager/managed-instances/rdp-connect?'
        url+=f'instances={self.instance.instance_id}&region={region}#'
        
        output =CfnOutput(self, "RDP", value=url, description='Workbench Remote Access Url')
        output.override_logical_id('WorkbenchRemoteAccessUrl')
