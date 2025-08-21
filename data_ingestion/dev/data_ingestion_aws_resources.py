import boto3
import json
import time
from dotenv import load_dotenv
import os

def main():
    load_dotenv(dotenv_path='.env') 

    region = os.environ.get("AWS_REGION")
    bucket_name = os.environ.get("S3_BUCKET")
    cluster_name = os.environ.get("EMR_CLUSTER_NAME") 
    layer_arn = os.environ.get("LAMBDA_LAYER_ARN_DATA_INGESTION")

    # ==============================
    # Create S3 bucket
    # ==============================
    s3 = boto3.client('s3', region_name=region)

    print("Creating S3 bucket...")
    try:
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(f"Created bucket {bucket_name}")
    except Exception as e:
        if 'BucketAlreadyOwnedByYou' in str(e):
            print(f"Bucket {bucket_name} already exists")
        else:
            raise e

    # ==============================
    # Create IAM role for Lambda
    # ==============================
    iam = boto3.client("iam")
    role_name = "LambdaEarthquakeRole"
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }

    try:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy)
        )
    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=role_name)

    iam.attach_role_policy(RoleName=role_name, PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess")
    iam.attach_role_policy(RoleName=role_name, PolicyArn="arn:aws:iam::aws:policy/AmazonAthenaFullAccess")
    iam.attach_role_policy(RoleName=role_name, PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")

    time.sleep(10)
    role_arn = role['Role']['Arn']
    print("Role ARN:", role_arn)

    # ==============================
    # Create DataIngestion Lambda
    # ==============================
    lambda_client = boto3.client("lambda")
    lambda_name = "ProcessEarthquakeData"

    with open('data_scraping.py', 'r') as f:
        lambda_code = f.read()

    response = lambda_client.create_function(
        FunctionName=lambda_name,
        Runtime="python3.11",
        Role=role_arn,
        Handler="data_scraping.lambda_handler",
        Code={"ZipFile": bytes(lambda_code, 'utf-8')},
        Timeout=300,
        Layers=[layer_arn]
    )

    print("Lambda ARN:", response['FunctionArn'])


if __name__ == "__main__":
    main()