import os
import boto3
import pandas as pd
from io import BytesIO
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

    cols_to_keep = ['time', 'latitude', 'longitude', 'depth', 'mag', 'place', 'id']
    df = df_earthquake[cols_to_keep].dropna().round(3)

    df['timestamps'] = pd.to_datetime(df['time']).dt.round('s')
    df['date'] = df['timestamps'].dt.date
    df['time'] = df['timestamps'].dt.floor('s').dt.time
    
    if not df.empty:
        print("Uploading data to S3...")
        buffer = BytesIO()
        df.to_parquet(buffer, index=False)
        s3_client.put_object(
            Bucket=bucket,
            Key=f"data/raw/earthquake_{start_date}.parquet",
            Body=buffer.getvalue()
        )
        print(f"Successfully uploaded data for {start_date}")
    else:
        print(f"No earthquake data for {start_date}")

    return {"status": "done"}