import boto3
import sys
import time
import json
import os
import sagemaker
from sagemaker.processing import ProcessingJob
from sagemaker.model_monitor import DefaultModelMonitor, BaseliningJob, CronExpressionGenerator

# Load arguments

bucket_name = sys.argv[1]
prefix = sys.argv[2]
execution_role = sys.argv[3]
processing_job_name = os.environ['PROCESSING_JOB_NAME']
endpoint_name = os.environ['ENDPOINT_NAME']

# Upload pre-processor scripts

start = time.time()
print('Loading monitor baseline for job: {}'.format(processing_job_name))

code_prefix = '{}/code'.format(prefix)
s3_code_preprocessor_uri = 's3://{}/{}/{}'.format(bucket_name, code_prefix, 'preprocessor.py')
s3_code_postprocessor_uri = 's3://{}/{}/{}'.format(bucket_name, code_prefix, 'postprocessor.py')
reports_prefix = '{}/reports'.format(prefix)
s3_report_path = 's3://{}/{}'.format(bucket_name, reports_prefix)

print("Report path: {}".format(s3_report_path))
print("Preproc Code path: {}".format(s3_code_preprocessor_uri))
print("Postproc Code path: {}".format(s3_code_postprocessor_uri))

# Load the processing job

processing_job = ProcessingJob.from_processing_name(
    processing_job_name=processing_job_name,
    sagemaker_session=sagemaker.Session())

from sagemaker.model_monitor import BaseliningJob
baseline_job = BaseliningJob.from_processing_job(processing_job)

my_default_monitor = DefaultModelMonitor(
    role=execution_role,
    instance_count=1,
    instance_type='ml.m5.xlarge',
    volume_size_in_gb=20,
    max_runtime_in_seconds=3600,
)

print('Starting monitor schedule for endpoint: {}'.format(endpoint_name))

# First, copy over some test scripts to the S3 bucket so that they can be used for pre and post processing

s3 = boto3.Session().resource('s3')
s3.Bucket(bucket_name).Object(code_prefix+"/preprocessor.py").upload_file('Source/Monitor/preprocessor.py')
s3.Bucket(bucket_name).Object(code_prefix+"/postprocessor.py").upload_file('Source/Monitor/postprocessor.py')

my_default_monitor.create_monitoring_schedule(
    monitor_schedule_name=processing_job_name,
    endpoint_input=endpoint_name,
    #record_preprocessor_script=pre_processor_script,
    post_analytics_processor_script=s3_code_postprocessor_uri,
    output_s3_uri=s3_report_path,
    statistics=baseline_job.baseline_statistics(),
    constraints=baseline_job.suggested_constraints(),
    schedule_cron_expression=CronExpressionGenerator.hourly(),
    enable_cloudwatch_metrics=True
)

# TODO: Save constraints and statistics to output directory?

end = time.time()
print('Monitor schedule complete in: {}'.format(end - start))