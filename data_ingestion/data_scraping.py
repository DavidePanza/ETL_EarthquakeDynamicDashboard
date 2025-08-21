import boto3
import pandas as pd
# from io import BytesIO # when using parquet
from io import StringIO
from datetime import datetime, timedelta

def lambda_handler(event, context):
    bucket = "earthquake-data-dynamic-dashboard"
    s3_client = boto3.client('s3')

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
    df['full_time'] = pd.to_datetime(df['time']).dt.strftime('%Y-%m-%d %H:%M:%S')  # Full datetime
    df['event_date'] = pd.to_datetime(df['time']).dt.strftime('%Y-%m-%d')         # Date only
    df['event_time'] = pd.to_datetime(df['time']).dt.strftime('%H:%M:%S')  
    df.drop(columns=['time'], inplace=True)  # Drop the original 'time' column

    # Reorder columns for better structure
    column_order = ['full_time', 'event_date', 'event_time', 'latitude', 'longitude', 'depth', 'mag', 'place', 'id']
    df = df[column_order]
    
    if not df.empty:
        print("Uploading data to S3...")
        # buffer = BytesIO() # when using parquet
        # df.to_parquet(buffer, index=False)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
    
        if csv_data:
            s3_client.put_object(
                Bucket=bucket,
                Key=f"data/raw/earthquake_{start_date}.csv",
                Body=csv_data
                # Body=buffer.getvalue() # when using parquet
                )
            print(f"Successfully uploaded data for {start_date}")
        else:
            print(f"Generated CSV is empty for {start_date}")
    else:
        print(f"No earthquake data for {start_date}")

    return {"status": "done"}
