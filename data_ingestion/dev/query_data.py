import boto3
import json
import time

S3_OUTPUT = "s3://earthquake-data-dynamic-dashboard/athena-results/"
DATABASE = "earthquakes_db_dashboard"
TABLE = "earthquake_data"
REGION = "us-east-1"

athena = boto3.client('athena', region_name=REGION)

def lambda_handler(event, context):
    # Lambda Function URL sends POST body as string inside 'body'
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        body = {}

    start_date = body.get('start_date')
    end_date = body.get('end_date')

    if not start_date or not end_date:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "start_date and end_date required"})
        }

    query = f"""
        SELECT *
        FROM {DATABASE}.{TABLE}
        WHERE date_parse(event_date, '%Y-%m-%d') 
              BETWEEN DATE('{start_date}') AND DATE('{end_date}')
        ORDER BY timestamps
    """

    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': DATABASE},
        ResultConfiguration={'OutputLocation': S3_OUTPUT}
    )

    query_execution_id = response['QueryExecutionId']

    # Wait for query to complete
    while True:
        status = athena.get_query_execution(QueryExecutionId=query_execution_id)
        state = status['QueryExecution']['Status']['State']
        if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            break
        time.sleep(1)

    if state != 'SUCCEEDED':
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Athena query failed: {status}"})
        }

    result = athena.get_query_results(QueryExecutionId=query_execution_id)

    rows = []
    columns = [col['Label'] for col in result['ResultSet']['ResultSetMetadata']['ColumnInfo']]
    for r in result['ResultSet']['Rows'][1:]:  # skip header row
        row_data = [c.get('VarCharValue', None) for c in r['Data']]
        rows.append(dict(zip(columns, row_data)))

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(rows)
    }