import boto3
import json
import time
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_OUTPUT = "s3://earthquake-data-dynamic-dashboard/athena-results/"
DATABASE = "earthquakes_db_dashboard"
TABLE = "earthquake_data"
REGION = "us-east-1"

athena = boto3.client('athena', region_name=REGION)

def lambda_handler(event, context):
    # CORS headers for all responses
    cors_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST, OPTIONS"
    }
    
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Handle preflight OPTIONS request
        http_method = event.get('requestContext', {}).get('http', {}).get('method')
        if http_method == 'OPTIONS':
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": ""
            }
        
        # Lambda Function URL sends POST body as string inside 'body'
        try:
            if 'body' in event:
                body = json.loads(event['body'])
            else:
                body = event  # Direct invocation
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": f"Invalid JSON: {str(e)}"})
            }

        start_date = body.get('start_date')
        end_date = body.get('end_date')
        
        logger.info(f"Query parameters - start_date: {start_date}, end_date: {end_date}")

        if not start_date or not end_date:
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "start_date and end_date required"})
            }

        # More flexible date parsing - try different formats
        query = f"""
            SELECT *
            FROM {DATABASE}.{TABLE}
            WHERE date_parse(event_date, '%Y-%m-%d') 
                BETWEEN DATE('{start_date}') AND DATE('{end_date}')
            ORDER BY full_time
        """
        
        logger.info(f"Executing query: {query}")

        response = athena.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': DATABASE},
            ResultConfiguration={'OutputLocation': S3_OUTPUT}
        )

        query_execution_id = response['QueryExecutionId']
        logger.info(f"Query execution ID: {query_execution_id}")

        # Wait for query to complete with timeout
        max_wait_time = 60  # seconds
        wait_time = 0
        while wait_time < max_wait_time:
            status = athena.get_query_execution(QueryExecutionId=query_execution_id)
            state = status['QueryExecution']['Status']['State']
            
            if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                break
            
            time.sleep(2)
            wait_time += 2

        if wait_time >= max_wait_time:
            return {
                "statusCode": 500,
                "headers": cors_headers,
                "body": json.dumps({"error": "Query timeout"})
            }

        if state != 'SUCCEEDED':
            error_info = status['QueryExecution']['Status']
            logger.error(f"Athena query failed: {error_info}")
            return {
                "statusCode": 500,
                "headers": cors_headers,
                "body": json.dumps({
                    "error": f"Athena query failed: {state}",
                    "details": error_info.get('StateChangeReason', 'No additional details')
                })
            }

        result = athena.get_query_results(QueryExecutionId=query_execution_id)
        
        rows = []
        if 'ResultSet' in result and 'Rows' in result['ResultSet']:
            columns = [col['Label'] for col in result['ResultSet']['ResultSetMetadata']['ColumnInfo']]
            
            # Skip header row if it exists
            data_rows = result['ResultSet']['Rows'][1:] if len(result['ResultSet']['Rows']) > 1 else []
            
            for r in data_rows:
                row_data = [c.get('VarCharValue', None) for c in r['Data']]
                rows.append(dict(zip(columns, row_data)))
        
        logger.info(f"Returning {len(rows)} rows")
        
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({
                "data": rows,
                "count": len(rows),
                "query_execution_id": query_execution_id
            })
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": f"Internal server error: {str(e)}"})
        }