import boto3
from botocore.exceptions import ClientError
import json
import os

lb = boto3.client('lambda')
cd = boto3.client('codedeploy')
sm = boto3.client('sagemaker-runtime')

def get_endpoint_variant_config(function_name, qualifier='live'):
    try:
        response = lb.get_function(
            FunctionName=function_name,
            Qualifier=qualifier
        )
        print('lambda get_function', response)
        env_vars = response['Configuration']['Environment']['Variables']
        endpoint_name = env_vars['ENDPOINT_NAME']
        variant_name = env_vars.get('VARIANT_NAME', 'AllTraffic')
        current_version = int(response['Configuration']['Version'])
        print('found endpoint: {}/{} at function {}:{}'.format(
            endpoint_name, variant_name, function_name, current_version))   
        return endpoint_name, variant_name, current_version
    except ClientError as e:
        print('function: {}:{} not found'.format(function_name, qualifier), e)
        return None, None, 0

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
    print('event', json.dumps(event))

    function_name = os.environ['FUNCTION_NAME']
    target_version = os.environ['FUNCTION_VERSION']
    endpoint_name = os.environ['ENDPOINT_NAME']
    variant_name = os.environ['VARIANT_NAME']
    print('function: {}:{} endpoint: {}/{}'.format(
        function_name, target_version, endpoint_name, variant_name))

    error_message = None
    live_endpoint_name = None
    live_variant_name = None

    # Get the previous endpoint/variant to cooldown
    try:
        response = lb.get_function(FunctionName=function_name, Qualifier='live')
        print('lambda get_function', response)
        env_vars = response['Configuration']['Environment']['Variables']
        live_endpoint_name = env_vars['ENDPOINT_NAME']
        live_variant_name = env_vars.get('VARIANT_NAME', 'AllTraffic')
    except ClientError as e:
        # Record error unless function not found
        if not e.response['Error']['Message'].startswith('Function not found'):
            error_message = e.response['Error']['Message']    

    # Check that the target endpoint/variant are different from current
    if live_endpoint_name == endpoint_name and live_variant_name == endpoint_name:
        error_message = 'target endpoint/variant is same as live'
    elif error_message != None:
        try:
            # Test endpoint for valid predictions
            content_type = 'text/libsvm'
            payload = '1:1 2:0.555 3:0.435 4:0.145 5:0.9205 6:0.404 7:0.2275 8:0.255'

            response = sm.invoke_endpoint(
                EndpointName=endpoint_name,
                Body=payload,
                ContentType=content_type,
                Accept='application/json'
            )
            predictions = round(float(response['Body'].read().decode('utf-8')))
            print('predictions', predictions)

            if predictions < 8 or predictions > 10:
                error_message = "expected predicions to ~= 9"
                print(error_message)
        except ClientError as e:
            print('invoke endpoint error', e)
            error_message = e.response['Error']['Message']

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
        print('code deploy error', e)
        return {
            "statusCode": 500,
            "message": e.response['Error']['Message']    
        }
                

