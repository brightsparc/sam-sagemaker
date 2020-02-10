import json

import pytest

import logging

from regression import pre_traffic_hook, post_traffic_hook

@pytest.fixture()
def code_deploy_event():
    """ Generates Code Deploy event"""
    return {
        "DeploymentId": "d-B8ECPZ0I1",
        "LifecycleEventHookExecutionId": "XXXX"
    }

def test_pre_traffic_hook_handler(code_deploy_event, mocker):
    ret = pre_traffic_hook.lambda_handler(code_deploy_event, "")
    print(ret)
    assert ret["statusCode"] == 200

def test_post_traffic_hook_handler(code_deploy_event, mocker):
    ret = post_traffic_hook.lambda_handler(code_deploy_event, "")
    print(ret)
    assert ret["statusCode"] == 200
