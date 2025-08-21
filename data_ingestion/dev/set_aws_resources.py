# create_s3_emr.py - Simple S3 + EMR setup
import boto3
import json
import time
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path='.env') 

# Configuration
aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
region = os.environ.get("AWS_REGION")
bucket_name = os.environ.get("S3_BUCKET")
cluster_name = os.environ.get("EMR_CLUSTER_NAME") 
region = os.environ.get("AWS_REGION")


# ==============================
# Create S3 bucket
# ==============================

# Initialize clients
s3 = boto3.client('s3', 
                  aws_access_key_id=aws_access_key,
                  aws_secret_access_key=aws_secret_key,
                  region_name=region)

print("Creating S3 bucket...")
try:
    if region == 'us-east-1':
        s3.create_bucket(Bucket=bucket_name)
    else:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': region} # — even if your client is configured with a region, bucket creation region is set separately.
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

# Attach basic managed policies
iam.attach_role_policy(RoleName=role_name, PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess")
iam.attach_role_policy(RoleName=role_name, PolicyArn="arn:aws:iam::aws:policy/AmazonAthenaFullAccess")
iam.attach_role_policy(RoleName=role_name, PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")

# Wait for the role to propagate
time.sleep(10)

role_arn = role['Role']['Arn']
print("Role ARN:", role_arn)


# ==============================
# Create DataIngestion Lambda
# ==============================

lambda_client = boto3.client("lambda")

lambda_name = "ProcessEarthquakeData"

# Minimal Python code for Lambda
lambda_code = """
import boto3
import json
s3 = boto3.client('s3')
bucket_name = '{}'

def lambda_handler(event, context):
    data = [{"id": 1, "mag": 4.5, "lat": 12.3, "lon": 45.6}]
    key = "earthquake_data.json"
    s3.put_object(Bucket=bucket_name, Key=key, Body=json.dumps(data))
    return {"status": "success"}
""".format(bucket_name)

response = lambda_client.create_function(
    FunctionName=lambda_name,
    Runtime="python3.11",
    Role=role_arn,
    Handler="index.lambda_handler",
    Code={"ZipFile": bytes(lambda_code, 'utf-8')},
    Timeout=60
)

print("Lambda ARN:", response['FunctionArn'])


# ==============================
# Setup Athena
# ==============================

athena = boto3.client("athena")

db_name = "earthquakes_db"
s3_results = f"s3://{bucket_name}/athena-results/"

# Create database
athena.start_query_execution(
    QueryString=f"CREATE DATABASE IF NOT EXISTS {db_name}",
    ResultConfiguration={"OutputLocation": s3_results}
)

# Create table pointing to S3 JSON
table_query = f"""
CREATE EXTERNAL TABLE IF NOT EXISTS {db_name}.earthquake_data (
    id INT,
    mag DOUBLE,
    lat DOUBLE,
    lon DOUBLE
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://{bucket_name}/'
"""
athena.start_query_execution(
    QueryString=table_query,
    ResultConfiguration={"OutputLocation": s3_results}
)


# ==============================
# Create QueryLambda
# ==============================

query_lambda_name = "QueryEarthquakeData"

query_lambda_code = f"""
import boto3
import json
athena = boto3.client('athena')
bucket_name = '{bucket_name}'
db_name = '{db_name}'

def lambda_handler(event, context):
    min_mag = event.get("min_mag", 4.0)
    query = f"SELECT * FROM {{db_name}}.earthquake_data WHERE mag >= {{min_mag}}"
    response = athena.start_query_execution(
        QueryString=query,
        ResultConfiguration={{"OutputLocation": f"s3://{{bucket_name}}/athena-results/"}}
    )
    return {{'QueryExecutionId': response['QueryExecutionId']}}
"""

response = lambda_client.create_function(
    FunctionName=query_lambda_name,
    Runtime="python3.11",
    Role=role_arn,
    Handler="index.lambda_handler",
    Code={"ZipFile": bytes(query_lambda_code, 'utf-8')},
    Timeout=60
)

print("Query Lambda ARN:", response['FunctionArn'])


# ==============================
# Enable QueryLambda Function URL
# ==============================

lambda_client = boto3.client("lambda")

lambda_name = "QueryEarthquakeData"  # your query Lambda

response = lambda_client.create_function_url_config(
    FunctionName=lambda_name,
    AuthType="NONE"  # Public endpoint; use "AWS_IAM" for secured access
)

function_url = response['FunctionUrl']
print("Lambda Function URL:", function_url)


