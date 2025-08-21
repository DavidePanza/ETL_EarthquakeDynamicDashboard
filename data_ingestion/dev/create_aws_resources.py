from dotenv import load_dotenv
load_dotenv(dotenv_path='.env') 

from data_ingestion_aws_resources import create_data_ingestion_aws_resources
from lambda_layer import build_and_publish_layer
import click

@click.command()
@click.option("--step", type=str, required=True, help="enter wheter creating resources for data ingestion or queries")
def main(step):
    if step == "ingestion":
        print("Creating resources for data ingestion...")
        print("Building and publishing Lambda layer...")
        #build_and_publish_layer()

        # Reload environment variables
        #load_dotenv(dotenv_path='.env', override=True)  # load the layern_arn

        print("Creating S3 bucket and Lambda function...")
        create_data_ingestion_aws_resources()
        print("Data ingestion resources created successfully.")
    elif step == "query":
        print("Creating resources for data queries...")
    else:
        print("Invalid step. Please enter either 'ingestion' or 'query'.")

if __name__ == "__main__":
    main()