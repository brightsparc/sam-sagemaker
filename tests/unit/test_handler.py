import json

import pytest

import logging

from regression import app

@pytest.fixture()
def apigw_event():
    """ Generates API GW Event"""

    return {
        "resource": "/regression",
        "path": "/regression/",
        "httpMethod": "POST",
        "headers": {
            "Accept": "*/*",
            "CloudFront-Forwarded-Proto": "https",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-Mobile-Viewer": "false",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Tablet-Viewer": "false",
            "CloudFront-Viewer-Country": "AU",
            "content-type": "application/x-www-form-urlencoded",
            "Host": "656imtvqec.execute-api.ap-southeast-2.amazonaws.com",
            "User-Agent": "curl/7.54.0",
            "Via": "2.0 cab8093de9e922f6aac9f66e51afc0cc.cloudfront.net (CloudFront)",
            "X-Amz-Cf-Id": "IuHtIysArJBHgt866R6Myk2PbPjEIVMyXRvGO-lzJ8NBcEIt1mYM4w==",
            "X-Amzn-Trace-Id": "Root=1-5e40d0cd-938108449ada5506b7976056",
            "X-Forwarded-For": "54.240.193.1, 70.132.29.145",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https"
        },
        "multiValueHeaders": {
            "Accept": [
            "*/*"
            ],
            "CloudFront-Forwarded-Proto": [
            "https"
            ],
            "CloudFront-Is-Desktop-Viewer": [
            "true"
            ],
            "CloudFront-Is-Mobile-Viewer": [
            "false"
            ],
            "CloudFront-Is-SmartTV-Viewer": [
            "false"
            ],
            "CloudFront-Is-Tablet-Viewer": [
            "false"
            ],
            "CloudFront-Viewer-Country": [
            "AU"
            ],
            "content-type": [
            "application/x-www-form-urlencoded"
            ],
            "Host": [
            "656imtvqec.execute-api.ap-southeast-2.amazonaws.com"
            ],
            "User-Agent": [
            "curl/7.54.0"
            ],
            "Via": [
            "2.0 cab8093de9e922f6aac9f66e51afc0cc.cloudfront.net (CloudFront)"
            ],
            "X-Amz-Cf-Id": [
            "IuHtIysArJBHgt866R6Myk2PbPjEIVMyXRvGO-lzJ8NBcEIt1mYM4w=="
            ],
            "X-Amzn-Trace-Id": [
            "Root=1-5e40d0cd-938108449ada5506b7976056"
            ],
            "X-Forwarded-For": [
            "54.240.193.1, 70.132.29.145"
            ],
            "X-Forwarded-Port": [
            "443"
            ],
            "X-Forwarded-Proto": [
            "https"
            ]
        },
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": None,
        "stageVariables": None,
        "requestContext": {
            "resourceId": "lepnfc",
            "resourcePath": "/regression",
            "httpMethod": "POST",
            "extendedRequestId": "HqWQKF3sSwMFtAA=",
            "requestTime": "10/Feb/2020:03:41:01 +0000",
            "path": "/Prod/regression/",
            "accountId": "691313291965",
            "protocol": "HTTP/1.1",
            "stage": "Prod",
            "domainPrefix": "656imtvqec",
            "requestTimeEpoch": 1581306061757,
            "requestId": "f4abfc95-9d11-4041-960a-7f083ef7671d",
            "identity": {
            "cognitoIdentityPoolId": None,
            "accountId": None,
            "cognitoIdentityId": None,
            "caller": None,
            "sourceIp": "54.240.193.1",
            "principalOrgId": None,
            "accessKey": None,
            "cognitoAuthenticationType": None,
            "cognitoAuthenticationProvider": None,
            "userArn": None,
            "userAgent": "curl/7.54.0",
            "user": None
            },
            "domainName": "656imtvqec.execute-api.ap-southeast-2.amazonaws.com",
            "apiId": "656imtvqec"
        },
        "body": "{\"data\":\"1:1 2:0.555 3:0.435 4:0.145 5:0.9205 6:0.404 7:0.2275 8:0.255\"}",
        "isBase64Encoded": False
        }


def test_regression_handler(apigw_event, mocker):

    ret = app.lambda_handler(apigw_event, "")
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert "prediction" in ret["body"]
    # assert "location" in data.dict_keys()
