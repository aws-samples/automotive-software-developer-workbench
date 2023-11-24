from constructs import Construct
from pydantic import BaseModel, Field
from typing import Optional, List
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_autoscaling as asc,
    aws_ssm as ssm,
    aws_amazonmq as amq,
    aws_secretsmanager as sm,
    aws_s3 as s3,
    aws_logs as logs,
    aws_codecommit as cc,
)
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

class WorkersModel(BaseModel):
    instance_type: str
    ami: AmiModel
    launch_template_parameter: Optional[str] = None
    max_capacity: int = Field(default=1)
    min_capacity: int = Field(default=1)
    user_data: Optional[List[str]]
    volumes: List[VolumeModel]
    
class Workers(Construct):
    def __init__(self, scope: Construct, id: str, 
                 env_name: str, 
                 project_name: str,
                 config: WorkersModel,
                 vpc: ec2.Vpc,
                 artifact: s3.Bucket):
        super().__init__(scope, id)
        
        # Just allocate an IP for workers to access internet through NAT
        eip = ec2.CfnEIP(self, 'NATGatewayEIP')
        output = CfnOutput(self, 'NATGatewayAddress', 
            description= 'NAT Gateway Public IP Address',
            value=eip.attr_public_ip)
        output.override_logical_id('NATGatewayAddress')

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

        # if there is no AMI ID we don't install anything else
        log_group_name = f'/{project_name}/workers'
        log_group = logs.LogGroup(self, 'LogGroup',
            log_group_name=log_group_name)
        
        self.role = iam.Role(self, "Role",
            description="IAM role assigned to the EC2 Workers",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal(f"ssm.amazonaws.com"),
                iam.ServicePrincipal(f"ec2.amazonaws.com")))
        
        self.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))
        artifact.grant_read_write(self.role)
        log_group.grant_write(self.role)
        # This should be removed after reconfiguring worker log
        self.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess"))
        # -
        self.role.add_to_policy(iam.PolicyStatement(
            actions=['mq:ListBrokers'],
            resources=['*']))
        # This should be removed
        self.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeCommitFullAccess"))
        # -
        
        self.sg = ec2.SecurityGroup(self, "SecurityGroup", vpc=vpc)
        
        block_devices = []
        for volume in config.volumes:
            block_devices.append(
                ec2.BlockDevice(
                    device_name=volume.device_name,
                    volume=ec2.BlockDeviceVolume.ebs(volume.size)))
        
        machine_image = ec2.MachineImage.generic_windows({region: ami_id})
 
        self.launch_template = ec2.LaunchTemplate(self, 'LaunchTemplate',
            launch_template_name=f'{project_name}-{env_name}-workbench',
            associate_public_ip_address=False,
            block_devices=block_devices,
            http_tokens=ec2.LaunchTemplateHttpTokens.REQUIRED,
            instance_type=ec2.InstanceType(config.instance_type),
            machine_image=machine_image,
            require_imdsv2=True,
            role=self.role,
            security_group=self.sg,
            user_data=ec2.UserData.for_windows(persist=True))
        
        if (config.launch_template_parameter):
            ssm.StringParameter(self, "LaunchTemplateID",
                parameter_name=config.launch_template_parameter,
                string_value=self.launch_template.launch_template_id)
                
        self.asc = asc.AutoScalingGroup(self,"ASG",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            min_capacity=config.min_capacity,
            max_capacity=config.max_capacity,
            launch_template=self.launch_template)

        secret_name = f'/{project_name}-{env_name}/broker_credentials'
        self.secret = sm.Secret(self, "Secret",
            secret_name=secret_name,
            generate_secret_string=sm.SecretStringGenerator(
                secret_string_template=json.dumps({"username": "user"}),
                generate_string_key="password",
                exclude_punctuation=True))
        
        self.secret.grant_read(self.role)
        
        broker_name=f"{project_name}-{env_name}"
        self.broker = amq.CfnBroker(self, "Broker",
            auto_minor_version_upgrade=False,
            broker_name=broker_name,
            deployment_mode="SINGLE_INSTANCE",
            engine_type="RABBITMQ",
            engine_version="3.11.20",
            host_instance_type="mq.t3.micro",
            publicly_accessible=False,
            logs=amq.CfnBroker.LogListProperty(
                general=True),
            subnet_ids=[vpc.select_subnets(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnets[0].subnet_id],
            security_groups=[self.sg.security_group_id],
            users=[amq.CfnBroker.UserProperty(
                username=self.secret.secret_value_from_json("username").unsafe_unwrap(),
                password=self.secret.secret_value_from_json("password").unsafe_unwrap())])
        
        # Access to RabbitMQ and its management UI
        self.sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(), 
            connection=ec2.Port.tcp(5671))
        self.sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(), 
            connection=ec2.Port.tcp(443))
        
        region = Stack.of(self).region
        self.launch_template.user_data.add_commands(
            f"[System.Environment]::SetEnvironmentVariable('WORKER_QUEUE_BROKER_NAME', '{broker_name}', 'Machine')")
        self.launch_template.user_data.add_commands(
            f"[System.Environment]::SetEnvironmentVariable('WORKER_QUEUE_SECRET_NAME', '{self.secret.secret_name}', 'Machine')")
        self.launch_template.user_data.add_commands(
            f"[System.Environment]::SetEnvironmentVariable('WORKER_QUEUE_SECRET_REGION', '{region}', 'Machine')")
        self.launch_template.user_data.add_commands(
            f"[System.Environment]::SetEnvironmentVariable('WORKER_LOG_GROUP_NAME', '{log_group_name}', 'Machine')")
        self.launch_template.user_data.add_commands(
            f"[Environment]::SetEnvironmentVariable('AWS_DEFAULT_REGION', '{region}', 'Machine')")
        self.launch_template.user_data.add_commands(
            f"[Environment]::SetEnvironmentVariable('AWS_DEFAULT_REGION', '{region}')")
        self.launch_template.user_data.add_commands(
            f"[Environment]::SetEnvironmentVariable('ARTIFACT_BUCKET_NAME', '{artifact.bucket_name}', 'Machine')")
        self.launch_template.user_data.add_commands(
            f"[Environment]::SetEnvironmentVariable('ARTIFACT_BUCKET_NAME', '{artifact.bucket_name}')")

        for cmd in config.user_data:
            self.launch_template.user_data.add_commands(cmd)
            
        # Workers access Internet with this NAT gateway
        nat_gateway = ec2.CfnNatGateway(self, 'NATGateway', 
            allocation_id=eip.attr_allocation_id,
            subnet_id=vpc.public_subnets[0].subnet_id)
        
        for id, subnet in enumerate(vpc.private_subnets):
            ec2.CfnRoute(self, id = 'NatRoute' + str(id),
                route_table_id=subnet.route_table.route_table_id,
                destination_cidr_block='0.0.0.0/0',
                nat_gateway_id=nat_gateway.ref) 

