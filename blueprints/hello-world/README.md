# Hello-World

This blueprint aims at giving a basic understanding of the framework concepts that the other blueprints rely on.

It currently showcases how to deploy an AMI Factory that produces an AMI extending the AWS-managed Ubuntu 20.04 base AMI featuring:
- an Amazon-managed Python3 for Linux [ImageBuilder component](https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-components.html)
- a custom [NICE DCV](https://docs.aws.amazon.com/dcv/latest/adminguide/what-is-dcv.html) ImageBuilder component 

This AMI can then be used as a minimalist image for a Workbench.

## Deploy

If you got here from the [main page](../../README.md), resume your [CloudShell session](https://console.aws.amazon.com/cloudshell/home#). Otherwise, please refer to the main [Getting Started](../../README.md#getting-started) section, and come back here. It will only take a few minutes.

Issue the following commands:

```sh
cd ~/asdw
./scripts/deploy hello-world
```

