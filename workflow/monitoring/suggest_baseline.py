import sys
import time
import json
import os
import boto3
from botocore.exceptions import ClientError

# Import SageMaker and model monitor

import sagemaker
from sagemaker.utils import name_from_base
from sagemaker.model_monitor import DefaultModelMonitor
from sagemaker.model_monitor.dataset_format import DatasetFormat

## Arguments ##

bucket_name = sys.argv[1]
prefix = sys.argv[2]
execution_role = sys.argv[3]
stack_name = sys.argv[4]

start = time.time()

## Create baseline

codepipeline = boto3.client('codepipeline')
response = codepipeline.get_pipeline_state( name=stack_name )
execution_id = response['stageStates'][0]['latestExecution']['pipelineExecutionId']
job_name = name_from_base(execution_id)
print('Staring Training job: {}'.format(job_name))

baseline_data_path = 's3://{0}/{1}/monitoring/baselining/data'.format(bucket_name, prefix)
baseline_results_path = 's3://{0}/{1}/monitoring/baselining/results'.format(bucket_name, prefix)

print(baseline_data_path)
print(baseline_results_path)

my_default_monitor = DefaultModelMonitor(
    role=execution_role,
    instance_count=1,
    instance_type='ml.c5.4xlarge',
    volume_size_in_gb=20,
    max_runtime_in_seconds=3600,
)

my_default_monitor.suggest_baseline(
    job_name=job_name, 
    baseline_dataset=baseline_data_path,
    dataset_format=DatasetFormat.csv(header=True),
    output_s3_uri=baseline_results_path,
    logs=False, # Disable to avoid noisy logging, only meaningful when wait=True
    wait=True
)

# save environment variables

with open( './cloud_formation/suggest_baseline.vars', 'w' ) as f:
    f.write("export PROCESSING_JOB_NAME={0}\n".format(job_name))

end = time.time()
print('Monitor baseline complete in: {}'.format(end - start))