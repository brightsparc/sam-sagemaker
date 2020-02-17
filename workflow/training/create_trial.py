import boto3
from botocore.exceptions import ClientError
import time
import sys

stack_name = sys.argv[1] 
trial_name = sys.argv[2][:7] # Take the first 8 characters of commit hash

start = time.time()

# Create Experiment and Trial

print('Creating experiment: {} and trial: {}'.format(stack_name, trial_name))

sm = boto3.client('sagemaker')

try:
    response = sm.create_experiment(
        ExperimentName=stack_name,
        DisplayName=stack_name,
        Description='MLOps experiment'
    )
    print("Created experiment: %s" % response)
except ClientError as e:
    if e.response['Error']['Code'] == 'ValidationException':
        print("Experiment %s already exists" % stack_name)
    else:
        print("Unexpected error: %s" % e)

try:
    response = sm.create_trial(
        TrialName=trial_name,
        DisplayName=trial_name,
        ExperimentName=stack_name,
    )
    print("Created trial: %s" % response)
except ClientError as e:
    if e.response['Error']['Code'] == 'ValidationException':
        print("Trial %s already exists" % trial_name)
    else:
        print("Unexpected error: %s" % e)
