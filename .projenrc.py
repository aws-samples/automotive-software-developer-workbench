from projen.awscdk import AwsCdkPythonApp


project = AwsCdkPythonApp(
    name="aws-auto-sw-factory",
    description="AWS Automotive Software Factory",
    homepage='https://github.com/aws-samples/aws-auto-sw-factory',
    author_email="salamida@amazon.com",
    author_name="Francesco Salamida",
    license='MIT-0',
    cdk_version="2.99.1",
    module_name="src",
    version="1.0.0",
)

project.add_dev_dependency('pyyaml')
project.add_dev_dependency('pydantic')
project.add_dev_dependency('cdk-ec2-key-pair')
project.add_dev_dependency('boto3')

project.add_git_ignore('cdk.context.json')
project.add_git_ignore('.tmp')
project.add_git_ignore('config.yml')
project.add_git_ignore('download-url.*')
project.add_git_ignore('.DS_Store')
project.add_git_ignore('**/.DS_Store')

project.synth()