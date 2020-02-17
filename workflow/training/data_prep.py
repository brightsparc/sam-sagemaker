import boto3
from botocore.exceptions import ClientError
import time
import sys

bucket_name = sys.argv[1]
prefix = sys.argv[2]

start = time.time()
print('Data prep started...')

# Based on model monitor example using CSE-CIC-IDS2018 dataset
# see also: https://github.com/aws-samples/reinvent2019-aim362-sagemaker-debugger-model-monitor

s3 = boto3.resource('s3')

source_bucket_name = "sagemaker-ap-southeast-2-691313291965" 
source_bucket_prefix = "aim362/data/"
source_bucket = s3.Bucket(source_bucket_name)

for s3_object in source_bucket.objects.filter(Prefix=source_bucket_prefix):
    target_key = s3_object.key.replace(source_bucket_prefix, prefix+'/data/')
    copy_source = {
        'Bucket': source_bucket_name,
        'Key': s3_object.key
    }
    try:
        obj = s3.Object(bucket_name, target_key).load()
        print('Already Copied {0}'.format(target_key))
    except ClientError as e:    
        print('Copying {0} to {1} ...'.format(s3_object.key, target_key))
        s3.Bucket(bucket_name).copy(copy_source, target_key)

end = time.time()
print('Data prep complete in: {}'.format(end - start))