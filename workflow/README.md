# MLOps workflow

This is a sample solution using a SageMaker MLOps Workflow.  

This implementation could be useful for any organization trying to automate their use of Machine Learning.  With an implementation like this, any inference is easy, and can simply be queried through an endpoint to receive the output of the model’s inference, tests can be automatically performed for QA, and ML code can be quickly updated to match needs.


## Pre-Requisites

### Services

You should have some basic experience with:
  - Train/test a ML model
  - [Jupyter Notebook](https://jupyter.org/)
  - [AWS CodePipeline](https://aws.amazon.com/codepipeline/)
  - [AWS CodeCommit](https://aws.amazon.com/codecommit/)
  - [AWS CodeBuild](https://aws.amazon.com/codebuild/)
  - [Amazon SageMaker](https://aws.amazon.com/sagemaker/)
  - [AWS CloudFormation](https://aws.amazon.com/cloudformation/)


Some experience working with the AWS console is helpful as well.

## Deployment Steps
####  Step 1. Prepare an AWS Account
Create your AWS account at [http://aws.amazon.com](http://aws.amazon.com) by following the instructions on the site.

####  Step 2. Create a GitHub OAuth Token
Create your token at [GitHub's Token Settings](https://github.com/settings/tokens), making sure to select scopes of **repo** and **admin:repo_hook**.  After clicking **Generate Token**, make sure to save your OAuth Token in a secure location. The token will not be shown again.

####  Step 3. Launch the Stack
Launch the CloudFormation Stack for [pipeline.yaml] to set up the SageMaker MLOps Pipeline. Before Launching, ensure all architecture, configuration, etc. is set as desired.

```
aws cloudformation create-stack --stack-name <YourStackName> \
    --capabilities CAPABILITY_NAMED_IAM \
    --template-body file://workflow/pipeline.yaml \
    --parameters ParameterKey=GitHubToken,ParameterValue=<YourGitHubToken>
```