import boto3
from botocore.exceptions import ClientError
import json
import os

def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    # Implement pre traffic handler
    # See: https://awslabs.github.io/serverless-application-model/safe_lambda_deployments.html

    # Print the event
    current_version = os.environ['CURRENT_VERSION']
    endpoint_name = os.environ['ENDPOINT_NAME']
    print('version: {} endpoint: {} event: {}'.format(
        current_version, endpoint_name, json.dumps(event)))

    # Get boto3 sagemaker client and endpoint
    sm = boto3.client('sagemaker-runtime')

    # Dummy data
    content_type = 'text/libsvm'
    payload = '1:1 2:0.555 3:0.435 4:0.145 5:0.9205 6:0.404 7:0.2275 8:0.255'
    error_message = None

    # Invoke endpoint
    try:
        response = sm.invoke_endpoint(
            EndpointName=endpoint_name,
            Body=payload,
            ContentType=content_type,
            Accept='application/json'
        )
        predictions = response['Body'].read().decode('utf-8')
        print('predictions', predictions)
        if round(float(predictions))!=9:
            error_message = "Expected predicions to ~= 9"
    except ClientError as e:
        error_message = e.response['Error']['Message']

    # Get boto3 sagemaker client and endpoint
    cd = boto3.client('codedeploy')

    # If error return failure condition, else update to success
    try:
        if error_message:
            response = cd.put_lifecycle_event_hook_execution_status(
                deploymentId=event['DeploymentId'],
                lifecycleEventHookExecutionId=event['LifecycleEventHookExecutionId'],
                status='Failed'
            )
            print('put_lifecycle_failed', response)
            return {
                "statusCode": 400,
                "message": error_message
            }
        else:
            response = cd.put_lifecycle_event_hook_execution_status(
                deploymentId=event['DeploymentId'],
                lifecycleEventHookExecutionId=event['LifecycleEventHookExecutionId'],
                status='Succeeded'
            )
            print('put_lifecycle_succeeded', response)
            return {
                "statusCode": 200,
            }    
    except ClientError as e:
        # Error attempting to update the cloud formation
        return {
            "statusCode": 500,
            "message": e.response['Error']['Message']            
        }
                

