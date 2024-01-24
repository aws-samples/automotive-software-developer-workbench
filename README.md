# Welcome to the Automotive Software Developer Workbench

AWS is revolutionizing the way automotive software is being developed, providing automakers with the infrastructure, tools, and partner ecosystem needed to enable software-first development organizations.  
The Automotive Software Developer Workbench aims to provide an holistic overview of how the cloud can help to scale and accelerate automotive software development, showcasing a workbench, a software factory and an AMI factory.
This repository contains the instructions and code that allow you to deploy full end-to-end examples that will give you a sense of what a developer experiences working with various automotive software stacks.

While we currently support only a Model-based design workflow for AUTOSAR Classic Platform based on ETAS toolchain, we plan to implement additional examples in the future.

![Architecture](./docs/architecture.png)

## Getting started

Open an AWS CloudShell shell in one of the supported regions:

[![Launch](https://samdengler.github.io/cloudformation-launch-stack-button-svg/images/us-east-1.svg)](https://us-east-1.console.aws.amazon.com/cloudshell/)

[![Launch](https://samdengler.github.io/cloudformation-launch-stack-button-svg/images/eu-central-1.svg)](https://eu-central-1.console.aws.amazon.com/cloudshell/)

[![Launch](https://samdengler.github.io/cloudformation-launch-stack-button-svg/images/ap-southeast-1.svg)](https://ap-southeast-1.console.aws.amazon.com/cloudshell/)

Issue the following commands:

```sh
git clone https://github.com/aws-samples/automotive-software-developer-workbench.git asdw
cd ~/asdw
```

Choose among the following blueprints below and follow the instructions of the associated section to experience a use-case:

- [Model-based design workflow for AUTOSAR Classic Platform](blueprints/etas-autosar-cp/README.md)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more 
information.

## License

This code is licensed under the MIT-0 License. See the LICENSE file.
