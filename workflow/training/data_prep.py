import boto3
from botocore.exceptions import ClientError
import time
import sys

bucket_name = sys.argv[1]
prefix = sys.argv[2]

start = time.time()
print('Data prep started...')

# Copy abalone files
# see: https://github.com/awslabs/amazon-sagemaker-examples/tree/master/step-functions-data-science-sdk

s3 = boto3.resource('s3')

source_bucket_name = "mlops-ap-southeast-2-691313291965"
source_bucket_prefix = "data/"
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