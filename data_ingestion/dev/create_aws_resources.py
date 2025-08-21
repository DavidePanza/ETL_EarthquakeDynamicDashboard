from dotenv import load_dotenv
load_dotenv(dotenv_path='.env') 

from data_ingestion_aws_resources import create_data_ingestion_aws_resources
from query_aws_resources import create_query_aws_resources
import click

@click.command()
@click.option("--step", type=str, required=True, help="enter wheter creating resources for data ingestion or queries")
def main(step):
    if step == "ingestion":
        print("Creating resources for data ingestion...")
        create_data_ingestion_aws_resources()
        print("Data ingestion resources created successfully.")
    elif step == "query":
        print("Creating resources for data queries...")
        create_query_aws_resources()
        print("Data query resources created successfully.")
    else:
        print("Invalid step. Please enter either 'ingestion' or 'query'.")

if __name__ == "__main__":
    main()