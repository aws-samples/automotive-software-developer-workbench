# Welcome to the Automotive Software Developer Workbench

AWS is revolutionizing the way automotive software is being developed, providing automakers with the infrastructure, tools, and partner ecosystem needed to enable software-first development organizations.  
The Automotive Software Developer Workbench aim to provide a holistic overview of how the cloud can help to scale and accelerate automotive software development, showcasing a workbench, a software and an AMI factory.
This repository contains the instructions and code that allows you to deploy a full end-to-end example that will let you experiance what a developer experiance for various automotive software stack would look like.
While we currently support only a Model-based design workflow for AUTOSAR Classic Platform based on ETAS toolchain but we plan additional examples in the coming future.

![Architecture](./docs/architecture.png)

## Getting started

Deploy Cloud 9 in one of the supported regions

[![Launch](https://samdengler.github.io/cloudformation-launch-stack-button-svg/images/us-east-1.svg)](https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/review?stackName=asdw-cloud9&templateURL=https://automotive-software-developer-workbench-us-east-1.s3.us-east-1.amazonaws.com/cloud9-env.template.json)

[![Launch](https://samdengler.github.io/cloudformation-launch-stack-button-svg/images/eu-central-1.svg)](https://eu-central-1.console.aws.amazon.com/cloudformation/home?region=eu-central-1#/stacks/create/review?stackName=asdw-cloud9&templateURL=https://automotive-software-developer-workbench-eu-central-1.s3.us-east-1.amazonaws.com/cloud9-env.template.json)

[![Launch](https://samdengler.github.io/cloudformation-launch-stack-button-svg/images/ap-southeast-1.svg)](https://ap-southeast-1.console.aws.amazon.com/cloudformation/home?region=ap-southeast-1#/stacks/create/review?stackName=asdw-cloud9&templateURL=https://automotive-software-developer-workbench-ap-southeast-1.s3.us-east-1.amazonaws.com/cloud9-env.template.json)

Acknowledge the creation of the stack and press the button **Create stack** on the bottom right. 

![Create Stack](docs/createstack.png)

The [AWS Cloud9](https://aws.amazon.com/pm/cloud9) IDE instance will take about **3 minutes** to be created.

Choose among the blueprints below and follow the instruction shown in the associated section

- [Model-based design workflow for AUTOSAR Classic Platform](blueprints/etas-autosar-cp/README.md)


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more 
information.

## License

This code is licensed under the MIT-0 License. See the LICENSE file.
