import boto3
import json
import time
import io
import zipfile
import os

def create_query_aws_resources():
    # Configuration
    bucket_name = os.environ.get("S3_BUCKET")
    region = os.environ.get("AWS_REGION")

    # ==============================
    # Get IAM role for Lambda
    # ==============================

    iam = boto3.client("iam")
    role_name = "LambdaEarthquakeRole"

    # Just get the existing role
    role = iam.get_role(RoleName=role_name)
    role_arn = role['Role']['Arn']
    print("Using existing role ARN:", role_arn)

    # ==============================
    # Setup Athena (one-time)
    # ==============================

    def setup_athena():
        athena = boto3.client("athena", region_name=region)
        
        # Create database
        db_query = "CREATE DATABASE IF NOT EXISTS earthquakes_db_dashboard"
        db_response = athena.start_query_execution(
            QueryString=db_query,
            ResultConfiguration={"OutputLocation": f"s3://{bucket_name}/athena-results/"}
        )
        db_query_execution_id = db_response['QueryExecutionId']

        # Wait for database creation to complete
        while True:
            status = athena.get_query_execution(QueryExecutionId=db_query_execution_id)
            state = status['QueryExecution']['Status']['State']
            if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                break
            time.sleep(2)

        if state != 'SUCCEEDED':
            raise Exception(f"Athena database creation failed: {status['QueryExecution']['Status']}")


        # Create table for CSV data
        table_query = f"""
        CREATE EXTERNAL TABLE IF NOT EXISTS earthquakes_db_dashboard.earthquake_data (
            time STRING,
            latitude DOUBLE,
            longitude DOUBLE,
            depth DOUBLE,
            mag DOUBLE,
            place STRING,
            id STRING,
            timestamps TIMESTAMP,
            event_date STRING,      -- renamed from "date"
            event_time STRING       -- renamed from "time_only" and use STRING instead of TIME
        )
        ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
        WITH SERDEPROPERTIES ('field.delim' = ',')
        LOCATION 's3://{bucket_name}/data/raw/'
        TBLPROPERTIES ('skip.header.line.count'='1')
        """
        

        table_response = athena.start_query_execution(
            QueryString=table_query,
            ResultConfiguration={"OutputLocation": f"s3://{bucket_name}/athena-results/"}
        )
        table_query_execution_id = table_response['QueryExecutionId']

        # Wait for table creation to complete
        while True:
            status = athena.get_query_execution(QueryExecutionId=table_query_execution_id)
            state = status['QueryExecution']['Status']['State']
            if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                break
            time.sleep(2)

        if state != 'SUCCEEDED':
            raise Exception(f"Athena table creation failed: {status['QueryExecution']['Status']}")

    # Run Athena setup
    setup_athena()
    print("Athena database and table created")

    # ==============================
    # Create QueryLambda
    # ==============================

    lambda_client = boto3.client("lambda", region_name=region)
    query_lambda_name = "QueryEarthquakeData"

    # Create a proper ZIP file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the main Python file
        zip_file.write('query_data.py', 'query_data.py')
        
        # If you have any other files to include, add them here
        # zip_file.write('other_file.py', 'other_file.py')

    zip_buffer.seek(0)

    try:
        response = lambda_client.create_function(
            FunctionName=query_lambda_name,
            Runtime="python3.11",
            Role=role_arn,
            Handler="query_data.lambda_handler",
            Code={"ZipFile": zip_buffer.read()},
            Timeout=300,
        )
        print("Query Lambda ARN:", response['FunctionArn'])
    except lambda_client.exceptions.ResourceConflictException:
        print(f"Lambda function {query_lambda_name} already exists")

    # ==============================
    # Enable QueryLambda Function URL
    # ==============================

    lambda_client = boto3.client("lambda", region_name=region)
    query_lambda_name = "QueryEarthquakeData"

    # Check if Function URL exists
    try:
        response = lambda_client.get_function_url_config(FunctionName=query_lambda_name)
        function_url = response['FunctionUrl']
        print("Function URL already exists:", function_url)
    except lambda_client.exceptions.ResourceNotFoundException:
        response = lambda_client.create_function_url_config(
            FunctionName=query_lambda_name,
            AuthType="NONE"
        )
        function_url = response['FunctionUrl']
        print("Lambda Function URL created:", function_url)

    # ==============================
    # Add public permission for Function URL
    # ==============================
    try:
        lambda_client.add_permission(
            FunctionName=query_lambda_name,
            StatementId="FunctionURLAllowPublicAccess",
            Action="lambda:InvokeFunctionUrl",
            Principal="*",
            FunctionUrlAuthType="NONE"
        )
        print("Public access granted for Lambda Function URL")
    except lambda_client.exceptions.ResourceConflictException:
        print("Permission already exists for Function URL")