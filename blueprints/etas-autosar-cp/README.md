# Model-based design workflow for AUTOSAR Classic Platform

[TBD: ADD DESCRIPTION]

[LINK to ETAS CDW to be included in the description](https://www.etas.com/en/products/continuous-development-workbench.php)

![Architecture](docs/architecture.png)

## Deploy

If you got here from the [main page](../../README.md), access to the newly created [Cloud9 instance](https://console.aws.amazon.com/cloud9/home#), open a terminal, issue the following commands:

```sh
cd ~/environment/asdw
./scripts/deploy etas-autosar-cp
```

The `deploy` script will take about **1 minute** to complete and will print the AWS account ID and NAT gateway address

![First deploy](./docs/output1.png)


With the above information, request the access to the assets and licenses filling [**this form**](https://www.etas.com/en/portfolio/registration-continuous-development-workbench.php).

When you have been granted access from ETAS, you will need to rerun the `deploy` script

```sh
cd ~/environment/asdw
git pull
./scripts/deploy etas-autosar-cp
```

This second `deploy` run will take about **18 minutes**. Afterward, please allow another **10 minutes** before accessing the workbench, clicking the link printed by `deploy`

![Second deploy](./docs/output2.png)

with the following credentials

![Access workbench](./docs/credentials.png)

Follow the video instructions here [TBD: ADD LINK] to experiance the blueprint.

## Cleanup

From [CloudFormation](https://console.aws.amazon.com/cloudformation/home) just delete `project-1-dev-software-factory` and `asdw-cloud9` stacks.
[NOTE: Need to delete also the buckets]