import boto3
from botocore.exceptions import ClientError
import os
import time
import sys
import uuid

# Import Sagemaker and debugger config
import sagemaker
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
workflow_execution_role = sys.argv[4]
exp_name = sys.argv[5]
trial_name = sys.argv[6]
pipeline_name = sys.argv[7]

# Get pipeline execution id as job_name

codepipeline = boto3.client('codepipeline')
response = codepipeline.get_pipeline_state( name=pipeline_name )
job_name = response['stageStates'][0]['latestExecution']['pipelineExecutionId']
print('pipeline execution id: {}'.format(job_name))

# Create Experiment and Trial

start = time.time()
print('Creating experiment: {} and trial: {}'.format(exp_name, trial_name))

sm = boto3.client('sagemaker')

try:
    response = sm.create_experiment(
        ExperimentName=exp_name,
        DisplayName=exp_name,
        Description='MLOps experiment'
    )
    print("Created experiment: %s" % response)
except ClientError as e:
    if e.response['Error']['Code'] == 'ValidationException':
        print("Experiment %s already exists" % exp_name)
    else:
        print("Unexpected error: %s" % e)

try:
    response = sm.create_trial(
        TrialName=trial_name,
        DisplayName=trial_name,
        ExperimentName=exp_name,
    )
    print("Created trial: %s" % response)
except ClientError as e:
    if e.response['Error']['Code'] == 'ValidationException':
        print("Trial %s already exists" % trial_name)
    else:
        print("Unexpected error: %s" % e)

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
    "num_round": "20"
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
    'ExecutionRoleArn': str,
    'JobName': str, 
    'ModelName': str,
    'EndpointName': str
})

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
    initial_instance_count=1, 
    instance_type='ml.m5.large'
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
    name=exp_name,
    definition=workflow_definition,
    role=workflow_execution_role,
    execution_input=execution_input
)

inputs={
    'ExecutionRoleArn': sagemaker_execution_role,
    'JobName': job_name,  
    'ModelName': job_name,
    'EndpointName': job_name
}

workflow.create()
workflow.update(definition=workflow.definition)
execution = workflow.execute(
    inputs=inputs
)

stepfunction_arn = execution.execution_arn
print('Workflow exectuted: {}'.format(stepfunction_arn))

# Export environment variables

if not os.path.exists('cloud_formation'):
    os.makedirs('cloud_formation')

with open('cloud_formation/training.vars', 'w' ) as f:
    f.write('export STEPFUNCTION_ARN={}'.format(stepfunction_arn))

end = time.time()
print('Training launched in: {}'.format(end-start))