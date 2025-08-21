import os
import sys
import boto3
import pandas as pd
from datetime import datetime, timedelta

def lambda_handler(event, context):
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region = os.getenv('AWS_REGION', 'us-east-1')
    bucket = os.getenv('S3_BUCKET')
    
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=region
    )
 
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')    
    url = (
        f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=csv"
        f"&starttime={start_date}&endtime={end_date}&minmagnitude=2"
    )
    
    print(f"Loading earthquake data for {start_date}...")
    df_earthquake = pd.read_csv(url)
    df_earthquake['time'] = pd.to_datetime(df_earthquake['time'])
    
    df_earthquake = df_earthquake
    
    if not df_earthquake.empty:
        print("Uploading data to S3...")
        s3_client.put_object(
            Bucket=bucket,
            Key=f"data/raw/earthquake_{start_date}.parquet",
            Body=df_earthquake.to_parquet()
        )
        print(f"Successfully uploaded data for {start_date}")
    else:
        print(f"No earthquake data for {start_date}")

    return {"status": "done"}