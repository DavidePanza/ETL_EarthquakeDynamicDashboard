# Create AWS resources for ingestion
python create_aws_resources.py --step ingestion

# Invoke Lambda function (test ingestion)
aws lambda invoke --function-name ProcessEarthquakeData --payload '{}' response.json


# Create AWS resources for querying
python create_aws_resources.py --step query

# Invoke Lambda function (test query)
curl -X POST "add-lambda-url/" \
-H "Content-Type: application/json" \
  -d '{"start_date":"2025-08-17","end_date":"2025-08-21"}'