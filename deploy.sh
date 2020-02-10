# Write to file so as to force a new lambda version
echo $1 > regression/commit.txt 
aws cloudformation package --template-file template.yaml --output-template-file packaged.yaml --s3-bucket aws-sam-cli-managed-default-samclisourcebucket-1oij1gwxbc4jd
aws cloudformation deploy --template-file packaged.yaml --capabilities CAPABILITY_IAM --stack-name sam-sagemaker --parameter-overrides \
    CommitId=$1 \
    EndpointName=${2:-regression-c0a6afb44bb111eaabaaebff58b910ef} \
    EndpointName=${3:-regression-fb4528664bd011eaabaaebff58b910ef}
