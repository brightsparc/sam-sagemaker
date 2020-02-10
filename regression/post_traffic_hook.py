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

    # Implement post traffic handler
    # See: https://awslabs.github.io/serverless-application-model/safe_lambda_deployments.html

    # Print the event
    current_version = os.environ['CURRENT_VERSION']
    endpoint_name = os.environ['ENDPOINT_NAME']
    variant_name = os.environ['VARIANT_NAME']
    print('version: {} endpoint: {}/{} event:'.format(
        current_version, endpoint_name, variant_name, json.dumps(event)))

    # Get boto3 sagemaker client and endpoint
    sm = boto3.client('sagemaker')

    try:
        # First check the endpoint is in service
        response = sm.describe_endpoint(EndpointName='regression-c0a6afb44bb111eaabaaebff58b910ef')
        print(response)
        if response['EndpointStatus'] != "InService":
            return {
                "statusCode": 400,
                "message": "Unable to update endpoint not InService"
            }
        # Return to the minimum instance count
        response = sm.update_endpoint_weights_and_capacities(
            EndpointName=endpoint_name,
            DesiredWeightsAndCapacities=[
                {
                    'VariantName': variant_name,
                    'DesiredInstanceCount': 1
                },
            ]
        )
        print(response)
        return {
            "statusCode": 200
        }
    except ClientError as e:
        # Error attempting to update the cloud formation
        return {
            "statusCode": 500,
            "message": e.response['Error']['Message']            
        }


