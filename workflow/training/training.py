## TODO: 

import boto3
import time
import sys

# Import sagemaker functions
import sagemaker
from sagemaker.amazon.amazon_estimator import get_image_uri

# AWS Data Science SDK
from stepfunctions import steps
from stepfunctions.inputs import ExecutionInput
from stepfunctions.workflow import Workflow

bucket_name = sys.argv[1]
prefix = sys.argv[2]
sagemaker_execution_role = sys.argv[3]
workflow_execution_role = sys.argv[4]
model_name = sys.argv[5]
commit_id = sys.argv[6]

# Get region from boto3 session
region = boto3.Session().region_name
input_train_path = "s3://{}/{}/data/train".format(bucket_name, prefix)
input_validation_path = "s3://{}/{}/data/validation".format(bucket_name, prefix)
model_output_path =  "s3://{}/{}/model".format(bucket_name, prefix)
job_name = "{}-{}".format(model_name, commit_id) # TODO: Add enviornment?

# SageMaker expects unique names for each job, model and endpoint. 
# If these names are not unique the execution will fail. Pass these
# dynamically for each execution using placeholders.
execution_input = ExecutionInput(schema={
    'ExecutionRoleArn': str,
    'JobName': str, 
    'ModelName': str,
    'EndpointName': str
})

# Create estimator

xgb = sagemaker.estimator.Estimator(
    get_image_uri(region, 'xgboost'),
    execution_input['ExecutionRoleArn'], 
    train_instance_count = 1, 
    train_instance_type = 'ml.m4.4xlarge',
    train_volume_size = 5,
    output_path = model_output_path,
)

xgb.set_hyperparameters(
    objective = 'reg:linear',
    num_round = 50,
    max_depth = 5,
    eta = 0.2,
    gamme = 4,
    min_child_weight = 6,
    subsample = 0.7,
    silent = 0
)

# Create steps

training_step = steps.TrainingStep(
    'Train Step', 
    estimator=xgb,
    data={
        'train': sagemaker.s3_input(input_train_path, content_type='libsvm'),
        'validation': sagemaker.s3_input(input_validation_path, content_type='libsvm')
    },
    job_name=execution_input['JobName']  
)

model_step = steps.ModelStep(
    'Save model',
    model=training_step.get_expected_model(),
    model_name=execution_input['ModelName']  
)

endpoint_config_step = steps.EndpointConfigStep(
    "Create Endpoint Config",
    endpoint_config_name=execution_input['ModelName'],
    model_name=execution_input['ModelName'],
    initial_instance_count=1, # TODO: Parameterize
    instance_type='ml.m5.large' # TODO: Parameterize
)

endpoint_step = steps.EndpointStep(
    "Create Endpoint",
    endpoint_name=execution_input['EndpointName'],
    endpoint_config_name=execution_input['ModelName']
)

workflow_definition = steps.Chain([
    training_step,
    model_step,
    endpoint_config_step,
    endpoint_step
])

workflow = Workflow(
    name=model_name,
    definition=workflow_definition,
    role=workflow_execution_role,
    execution_input=execution_input
)

# Write the cloud formation to execute in pipeline
 
with open('cloud_formation/training_workflow.yaml', 'w') as f:
    f.write(workflow.get_cloudformation_template())

# TEMP: Create or update workflow, and execute
workflow.create()
workflow.update(definition=workflow.definition)

inputs={
    'ExecutionRoleArn': sagemaker_execution_role,
    'JobName': job_name, 
    'ModelName': job_name,
    'EndpointName': job_name
}
execution = workflow.execute(
    inputs=inputs
)

# Write out the step functions ARN
stepfunction_arn = execution.execution_arn

with open( 'cloud_formation/training.vars', 'w' ) as f:
    f.write('export STEPFUNCTION_ARN={}'.format(stepfunction_arn))

print('started', stepfunction_arn)