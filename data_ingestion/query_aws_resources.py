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
            full_time STRING,      -- YYYY-MM-DD HH:MM:SS
            event_date STRING,     -- YYYY-MM-DD  
            event_time STRING,     -- HH:MM:SS
            latitude DOUBLE,
            longitude DOUBLE,
            depth DOUBLE,
            mag DOUBLE,
            place STRING,
            id STRING
        )
        ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
        WITH SERDEPROPERTIES ('field.delim' = ',')
        LOCATION 's3://earthquake-data-dynamic-dashboard/data/raw/'
        TBLPROPERTIES ('skip.header.line.count'='1');
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

    # This section is only relevant if you want to invoke the Lambda function via a URL (in this case I'll use <API Gateway>)
    # # ==============================
    # # Enable QueryLambda Function URL
    # # ==============================

    # lambda_client = boto3.client("lambda", region_name=region)
    # query_lambda_name = "QueryEarthquakeData"

    # # Check if Function URL exists
    # try:
    #     response = lambda_client.get_function_url_config(FunctionName=query_lambda_name)
    #     function_url = response['FunctionUrl']
    #     print("Function URL already exists:", function_url)
    # except lambda_client.exceptions.ResourceNotFoundException:
    #     response = lambda_client.create_function_url_config(
    #         FunctionName=query_lambda_name,
    #         AuthType="NONE"
    #     )
    #     function_url = response['FunctionUrl']
    #     print("Lambda Function URL created:", function_url)

    # # ==============================
    # # Add public permission for Function URL
    # # ==============================
    # try:
    #     lambda_client.add_permission(
    #         FunctionName=query_lambda_name,
    #         StatementId="FunctionURLAllowPublicAccess",
    #         Action="lambda:InvokeFunctionUrl",
    #         Principal="*",
    #         FunctionUrlAuthType="NONE"
    #     )
    #     print("Public access granted for Lambda Function URL")
    # except lambda_client.exceptions.ResourceConflictException:
    #     print("Permission already exists for Function URL")

    # ==============================
    # Create API Gateway with rate limiting
    # ==============================

    apigateway = boto3.client("apigateway", region_name=region)

    # Create REST API
    api_response = apigateway.create_rest_api(
        name="earthquake-data-api",
        endpointConfiguration={'types': ['REGIONAL']}
    )
    api_id = api_response['id']
    print(f"API Gateway created: {api_id}")

    # Get root resource
    resources = apigateway.get_resources(restApiId=api_id)
    root_id = resources['items'][0]['id']

    # Create resource
    resource_response = apigateway.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='earthquake-data'
    )
    resource_id = resource_response['id']

    # Create POST method
    apigateway.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        authorizationType='NONE',
        apiKeyRequired=True
    )

    # Create integration FIRST
    lambda_arn = f"arn:aws:lambda:{region}:{boto3.client('sts').get_caller_identity()['Account']}:function:{query_lambda_name}"
    integration_uri = f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"

    apigateway.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        type='AWS_PROXY',
        integrationHttpMethod='POST',
        uri=integration_uri
    )

    # THEN add CORS responses
    apigateway.put_method_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Origin': False,
            'method.response.header.Access-Control-Allow-Headers': False,
            'method.response.header.Access-Control-Allow-Methods': False
        }
    )

    apigateway.put_integration_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='POST',
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Origin': "'*'",
            'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Api-Key'",
            'method.response.header.Access-Control-Allow-Methods': "'POST,OPTIONS'"
        }
    )

    # Create OPTIONS method for preflight
    apigateway.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        authorizationType='NONE',
        apiKeyRequired=False
    )

    apigateway.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        type='MOCK',
        requestTemplates={'application/json': '{"statusCode": 200}'}
    )

    apigateway.put_method_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Origin': False,
            'method.response.header.Access-Control-Allow-Headers': False,
            'method.response.header.Access-Control-Allow-Methods': False
        }
    )

    apigateway.put_integration_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod='OPTIONS',
        statusCode='200',
        responseParameters={
            'method.response.header.Access-Control-Allow-Origin': "'*'",
            'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Api-Key'",
            'method.response.header.Access-Control-Allow-Methods': "'POST,OPTIONS'"
        }
    )

    # Add Lambda permission
    try:
        lambda_client.add_permission(
            FunctionName=query_lambda_name,
            StatementId='ApiGatewayInvoke',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f"arn:aws:execute-api:{region}:{boto3.client('sts').get_caller_identity()['Account']}:{api_id}/*/*"
        )
    except lambda_client.exceptions.ResourceConflictException:
        pass

    # Deploy
    deployment = apigateway.create_deployment(
        restApiId=api_id,
        stageName='prod'
    )

    # Create API key
    api_key_response = apigateway.create_api_key(
        name='earthquake-api-key',
        enabled=True
    )
    api_key_id = api_key_response['id']

    # Create usage plan with rate limiting
    usage_plan = apigateway.create_usage_plan(
        name='earthquake-usage-plan',
        throttle={'rateLimit': 5, 'burstLimit': 10},
        quota={'limit': 1000, 'period': 'DAY'},
        apiStages=[{'apiId': api_id, 'stage': 'prod'}]
    )

    # Link API key to usage plan
    apigateway.create_usage_plan_key(
        usagePlanId=usage_plan['id'],
        keyId=api_key_id,
        keyType='API_KEY'
    )

    # Get API key value
    api_key_value = apigateway.get_api_key(apiKey=api_key_id, includeValue=True)['value']

    print(f"API URL: https://{api_id}.execute-api.{region}.amazonaws.com/prod/earthquake-data")
    print(f"API Key: {api_key_value}")