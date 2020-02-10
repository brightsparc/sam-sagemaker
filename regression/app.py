import boto3
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

    # Ensure we have permissions
    # See: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-sagemaker-endpoint.html

    # Get boto3 sagemaker client and endpoint
    client = boto3.client('sagemaker-runtime')
    endpoint_name = os.environ['ENDPOINT_NAME']

    # Print the event
    print('event', json.dumps(event))

    # Get posted body and content type
    content_type = event['headers'].get('Content-Type', 'text/libsvm')
    body = json.loads(event['body'])
    payload = body.get('data')
    print('payload', endpoint_name, content_type, payload)

    # Invoke endpoint
    response = client.invoke_endpoint(
        EndpointName=endpoint_name,
        Body=payload,
        ContentType=content_type,
        Accept='application/json'
    )
    predictions = response['Body'].read().decode('utf-8')

    # Return predictions
    return {
        "statusCode": 200,
        "body": json.dumps({
            "predictions": predictions
        }),
    }
