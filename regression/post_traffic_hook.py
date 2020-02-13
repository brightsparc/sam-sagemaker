import boto3
from botocore.exceptions import ClientError
import json
import os

lb = boto3.client('lambda')
cd = boto3.client('codedeploy')
sm = boto3.client('sagemaker')

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

    # Implement post traffic handler
    # See: https://awslabs.github.io/serverless-application-model/safe_lambda_deployments.html
    print('event', json.dumps(event))

    # Print arguments
    function_name = os.environ['FUNCTION_NAME']
    function_version = os.environ['FUNCTION_VERSION']
    instance_count = int(os.environ['INSTANCE_COUNT'])
    print('function: {}:{} target instance count: {}'.format(
        function_name, function_version, instance_count))

    error_message = None
    live_endpoint_name = None
    live_variant_name = None
    live_version = 0

    # Get the previous endpoint/variant to cooldown
    try:
        response = lb.get_function(FunctionName=function_name, Qualifier='live')
        print('lambda get_function', response)
        env_vars = response['Configuration']['Environment']['Variables']
        live_endpoint_name = env_vars['ENDPOINT_NAME']
        live_variant_name = env_vars.get('VARIANT_NAME', 'AllTraffic')
        live_version = int(response['Configuration']['Version'])
    except ClientError as e:
        # Record error unless function not found
        if not e.response['Error']['Message'].startswith('Function not found'):
            error_message = e.response['Error']['Message']

    # Check that the current function is not yet live
    if function_version == live_version:
        error_message = 'function {}:{} is already live'.format(function_name, function_version)
    elif live_endpoint_name != None:
        try:
            # First check the endpoint is in service
            response = sm.describe_endpoint(EndpointName=live_endpoint_name)
            print('describe_endpoint', response)
            if instance_count == 0:
                # Delete the endpoint and config
                endpoint_config_name = response['EndpointConfigName']
                response = sm.delete_endpoint(EndpointName=live_endpoint_name)
                print('delete_endpoint', response)
                response = sm.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
                print('delete_endpoint_config', response)
            elif response['EndpointStatus'] == "InService":
                # Return to the minimum instance count
                response = sm.update_endpoint_weights_and_capacities(
                    EndpointName=live_endpoint_name,
                    DesiredWeightsAndCapacities=[
                        {
                            'VariantName': live_variant_name,
                            'DesiredInstanceCount': instance_count
                        },
                    ]
                )
                print('update_endpoint_weights_and_capacities', response)
            else:
                print('endpoint not in service')
                error_message = "Unable to update endpoint not InService"
        except ClientError as e:
            print('endpoint error', e)
            error_message = e.response['Error']['Message']

    try:
        if error_message and not error_message.startswith('Could not find endpoint'):
            # Write failure if endpoint exists and unable to be updated 
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
                "statusCode": 200
            }
    except ClientError as e:
        # Error attempting to update the cloud formation
        print('code deploy error', e)
        return {
            "statusCode": 500,
            "message": e.response['Error']['Message']            
        }
