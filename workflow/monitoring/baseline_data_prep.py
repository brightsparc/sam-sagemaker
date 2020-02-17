import boto3
from botocore.exceptions import ClientError
import time
import sys

bucket_name = sys.argv[1]
prefix = sys.argv[2]

start = time.time()
print('Baseline prep started...')

# Creating a copy of validation set for baseline

s3 = boto3.resource('s3')

bucket_key_prefix = prefix + "/data/val/"
bucket = s3.Bucket(bucket_name)

for s3_object in bucket.objects.filter(Prefix=bucket_key_prefix):
    target_key = s3_object.key.replace('data/val/', 'monitoring/baselining/data/').replace('.part', '.csv')
    copy_source = {
        'Bucket': bucket_name,
        'Key': s3_object.key
    }
    try:
        obj = s3.Object(bucket_name, target_key).load()
        print('Already Copied {0}'.format(target_key))
    except ClientError as e:
        print('Copying {0} to {1} ...'.format(s3_object.key, target_key))
        s3.Bucket(bucket_name).copy(copy_source, target_key)
        
end = time.time()
print('Baseline prep complete in: {}'.format(end - start))