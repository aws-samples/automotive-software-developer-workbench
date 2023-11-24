import os
from constructs import Construct
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_codecommit as cc,
    aws_codebuild as cb,
    aws_codepipeline as cp,
    aws_codepipeline_actions as cp_actions,
    aws_iam as iam,
    aws_s3 as s3,
    aws_ec2 as ec2
)
from pydantic import BaseModel
from typing import Optional, List
from src.workers import Workers, WorkersModel
from src.workbench import Workbench, WorkbenchModel

class RepositoryModel(BaseModel):
    name: str
    code: Optional[str] = None

class VpcModel(BaseModel):
    ip_addresses: str = "10.1.0.0/16"
    
class ActionModel(BaseModel):
    name: str
    buildspec: str
    
class StageModel(BaseModel):
    name: str
    actions: List[ActionModel]

class SoftwareFactoryModel(BaseModel):
    repository: RepositoryModel
    vpc: Optional[VpcModel] = VpcModel()
    workers: Optional[WorkersModel] = None
    stages: Optional[List[StageModel]] = None
    workbench: Optional[WorkbenchModel] = None

class SoftwareFactoryStack(Stack):
  def __init__(self, scope: Construct, construct_id: str, 
        env_name: str, 
        project_name: str, 
        config: SoftwareFactoryModel, 
        **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)
    
    account_id = Stack.of(self).account
    region = Stack.of(self).region
                
    CfnOutput(self, "Account ID", value=account_id, description='Accout ID')

    kargs = { 'repository_name': config.repository.name }
    if config.repository.code:
        kargs['code'] = cc.Code.from_directory(directory_path = os.path.join(
            os.path.dirname(__file__), 
            os.path.join('..', config.repository.code)))
    
    self.repository = cc.Repository(self, 'Repository', **kargs)
    
    self.artifact = s3.Bucket(self, 'ArtifactBucket', 
        bucket_name=f'{project_name}-{env_name}-{account_id}-{region}')
    
    self.vpc = ec2.Vpc(self, 'VPC',
        ip_addresses = ec2.IpAddresses.cidr(config.vpc.ip_addresses),
        enable_dns_hostnames = True,
        enable_dns_support = True,
        max_azs = 1,
        nat_gateways=0,
        subnet_configuration = [
                ec2.SubnetConfiguration(
                    cidr_mask = 24,
                    name = 'Public',
                    subnet_type = ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    cidr_mask=24,
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                )],
        gateway_endpoints={
            "S3": ec2.GatewayVpcEndpointOptions(
                service=ec2.GatewayVpcEndpointAwsService.S3)})
    
    self.vpc.add_interface_endpoint("SSM",
        service=ec2.InterfaceVpcEndpointAwsService.SSM,
        subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS))

    self.vpc.add_interface_endpoint("CC",
        service=ec2.InterfaceVpcEndpointAwsService.CODECOMMIT_GIT ,
        subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS))
    
    self.vpc.add_interface_endpoint("CW",
        service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS ,
        subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS))
        
    cb_role = iam.Role(self, 'CodeBuildRole', 
        assumed_by=iam.ServicePrincipal('codebuild.amazonaws.com'))
    self.artifact.grant_read_write(cb_role)

    if config.workers:
        workers = Workers(self, 'Workers', 
            env_name=env_name, 
            project_name=project_name,
            config=config.workers,
            vpc=self.vpc,
            artifact=self.artifact)
        if hasattr(workers, 'broker'):
            cb_role.add_to_policy(iam.PolicyStatement(
                    actions=['mq:ListBrokers'],
                    resources=['*']))
            workers.secret.grant_read(cb_role)
            self.repository.grant_pull_push(workers.role)


    pipeline = cp.Pipeline(self, 'Pipeline', 
        pipeline_name=f'{project_name}-{env_name}',
        cross_account_keys=False)
    
    source_stage = pipeline.add_stage(stage_name='Source')
    source_artifact = cp.Artifact();

    source_stage.add_action(cp_actions.CodeCommitSourceAction(
        action_name='Source',
        output=source_artifact,
        repository=self.repository,
        branch='main'))
        
    for stage in config.stages:
        actions = []
        for action in stage.actions:
            kargs = {
                'role': cb_role,
                'environment': cb.BuildEnvironment(
                    compute_type=cb.ComputeType.SMALL,
                    build_image=cb.LinuxBuildImage.AMAZON_LINUX_2_5),
                'build_spec': cb.BuildSpec.from_source_filename(f'.cb/{action.buildspec}'),
                'environment_variables': {
                    'ARTIFACT_BUCKET_NAME': cb.BuildEnvironmentVariable(
                        value=f'{self.artifact.bucket_name}'),
                    'WORKER_QUEUE_SECRET_REGION': cb.BuildEnvironmentVariable(
                        value=region)}}
            
            if config.workers and hasattr(workers, 'broker'):
                kargs.update({
                    'vpc': self.vpc,
                    'security_groups': [workers.sg],                    
                    'subnet_selection': ec2.SubnetSelection(
                        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)})
                kargs['environment_variables'].update({
                    'WORKER_QUEUE_BROKER_NAME': cb.BuildEnvironmentVariable(
                        value=workers.broker.broker_name),
                    'WORKER_QUEUE_SECRET_NAME': cb.BuildEnvironmentVariable(
                        value=workers.secret.secret_name)})
            
            actions.append(cp_actions.CodeBuildAction(
                action_name=action.name,
                input=source_artifact,
                project=cb.PipelineProject(self, action.name, **kargs)))
            
        pipeline.add_stage(stage_name=stage.name, actions=actions)
    
    if config.workbench:
        wb=Workbench(self, 'Workbench', 
            env_name=env_name, 
            project_name=project_name,
            config=config.workbench,
            vpc=self.vpc,
            artifact=self.artifact)
        wb.node.add_dependency(workers)
        self.repository.grant_pull_push(wb.role)
        
                

            
    
    
