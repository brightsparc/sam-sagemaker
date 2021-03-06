import boto3
from botocore.exceptions import ClientError
import json
import os
import time
import sys

# Import Sagemaker and debugger config
import sagemaker
from sagemaker.utils import name_from_base
from sagemaker.xgboost import XGBoost
from sagemaker.debugger import Rule, rule_configs, DebuggerHookConfig, CollectionConfig

# Import AWS Data Science SDK
from stepfunctions import steps
from stepfunctions.inputs import ExecutionInput
from stepfunctions.workflow import Workflow

# Get Arguments

bucket_name = sys.argv[1]
prefix = sys.argv[2]
sagemaker_execution_role = sys.argv[3]
workflow_arn = sys.argv[4]
stack_name = sys.argv[5] 
trial_name = sys.argv[6][:7] # Take the first 8 characters of commit hash

start = time.time()

# Get pipeline execution id as job_name

codepipeline = boto3.client('codepipeline')
response = codepipeline.get_pipeline_state( name=stack_name )
execution_id = response['stageStates'][0]['latestExecution']['pipelineExecutionId']
job_name = name_from_base(execution_id)
print('Staring Training job: {}'.format(job_name))

# Lookup environment to get live blue/green from current lambda
# TODO: Add a deployment success event to switch the paraemter
# see: https://docs.aws.amazon.com/codedeploy/latest/userguide/monitoring-cloudwatch-events.html

# Attempt to read current live endpoint, if not found default to 'blue/green'
endpoint_name = '{}-{}'.format(stack_name, 'blue')
cooldown_endpoint_name = '{}-{}'.format(stack_name, 'green')
try:
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(Name=stack_name)
    print('get_parameter', response)
    cooldown_endpoint_name = response['Parameter']['Value'] # Set cooldown as current live
    endpoint_env = 'green' if cooldown_endpoint_name.endswith('blue') else 'blue'
    endpoint_name = '{}-{}'.format(stack_name, endpoint_env)
except ClientError as e:
    print('get_parameter error', e)

# Check if the endpoint exists

update_endpoint = False
try:
    sm = boto3.client('sagemaker')
    response = sm.describe_endpoint(EndpointName=endpoint_name)
    print('describe_endpoint', response)
    update_endpoint = True
except ClientError as e:
    print('endpoint error', e)

# Create Estimator with debug hooks

input_train_path = "s3://{}/{}/data/train".format(bucket_name, prefix)
input_validation_path = "s3://{}/{}/data/val".format(bucket_name, prefix)
model_output_path =  "s3://{}/{}/model".format(bucket_name, prefix)
debug_output_path = 's3://{0}/{1}/model/debug'.format(bucket_name, prefix)
model_code_location = 's3://{0}/{1}/code'.format(bucket_name, prefix)
entry_point='train_xgboost.py'
source_dir='workflow/training/'

# TODO: Upload source files here given we are not calling fit

debug_hook_config = DebuggerHookConfig(
    s3_output_path=debug_output_path,
    hook_parameters={
        "save_interval": "1"
    },
    collection_configs=[
        CollectionConfig("hyperparameters"),
        CollectionConfig("metrics"),
        CollectionConfig("predictions"),
        CollectionConfig("labels"),
        CollectionConfig("feature_importance")
    ]
)

debug_rules = [Rule.sagemaker(rule_configs.confusion(),
    rule_parameters={
        "category_no": "15",
        "min_diag": "0.7",
        "max_off_diag": "0.3",
        "start_step": "17",
        "end_step": "19"}
)]

hyperparameters = {
    "max_depth": "10",
    "eta": "0.2",
    "gamma": "1",
    "min_child_weight": "6",
    "silent": "0",
    "objective": "multi:softmax",
    "num_class": "15",
    "num_round": "1" # TEMP: Hack to make faster
}

xgb = XGBoost(
    entry_point=entry_point,
    source_dir=source_dir,
    output_path=model_output_path,
    code_location=model_code_location,
    hyperparameters=hyperparameters,
    train_instance_type="ml.m5.4xlarge",
    train_instance_count=1,
    framework_version="0.90-2",
    py_version="py3",
    role=sagemaker_execution_role,
    debugger_hook_config=debug_hook_config,
    rules=debug_rules
)

# Upload model code to s3

xgb.prepare_workflow_for_training(job_name)
print('uploaded code to: {}'.format(xgb.uploaded_code.s3_prefix))

# Create Workflow steps

execution_input = ExecutionInput(schema={
    'TrainLocation': str,
    'ValidationLocation': str,
    'EndpointName': str
})
execution_params = {
    'TrainLocation': input_train_path,
    'ValidationLocation': input_validation_path,
    'EndpointName': endpoint_name
}

training_step = steps.TrainingStep(
    'Train Step', 
    estimator=xgb,
    data={
        'train': sagemaker.s3_input(execution_input['TrainLocation'], content_type='libsvm'),
        'validation': sagemaker.s3_input(execution_input['ValidationLocation'], content_type='libsvm')
    },
    job_name=job_name # Require embedding this to job_name matches uploaded code
)

model_step = steps.ModelStep(
    'Save model',
    model=training_step.get_expected_model(),
    model_name=job_name
)

endpoint_config_step = steps.EndpointConfigStep(
    "Create Endpoint Config",
    endpoint_config_name=job_name,
    model_name=job_name,
    initial_instance_count=1, 
    instance_type='ml.m5.large'
)

endpoint_step = steps.EndpointStep(
    "Create or Update Endpoint",
    endpoint_name=execution_input['EndpointName'],
    endpoint_config_name=job_name,
    update=update_endpoint
)

workflow_definition = steps.Chain([
    training_step,
    model_step,
    endpoint_config_step,
    endpoint_step
])

# Update the workflow that is already created 

workflow = Workflow.attach(workflow_arn)
workflow.update(definition=workflow_definition)
print('Workflow updated: {}'.format(workflow_arn))

# Sleep for 5 seconds then execute after this is applied
time.sleep(5)

execution = workflow.execute(
    inputs=execution_params
)
stepfunction_arn = execution.execution_arn
print('Workflow exectuted: {}'.format(stepfunction_arn))

# Export environment variables

if not os.path.exists('cloud_formation'):
    os.makedirs('cloud_formation')

with open('cloud_formation/training.vars', 'w' ) as f:
    f.write('export TRAINING_JOB_NAME={}\nexport ENDPOINT_NAME={}\nexport STEPFUNCTION_ARN={}'.format(
        job_name, endpoint_name, stepfunction_arn))

# Write deployment parameters

params_deploy = {
    "Parameters": {
        "CommitId": trial_name,
        "EndpointName": endpoint_name,
        "EndpointVariant": "AllTraffic",
        "CoolDownEndpointName": cooldown_endpoint_name, 
        "CoolDownVariant": "AllTraffic",
    }
}
with open('cloud_formation/deploy.json', 'w' ) as f:
    f.write(json.dumps(params_deploy))

end = time.time()
print('Training launched in: {}'.format(end-start))