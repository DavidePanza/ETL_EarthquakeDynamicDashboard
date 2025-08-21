import data_ingestion_aws_resources
from lambda_layer import build_and_publish_layer
import click

@click.command()
@click.option("--step", type=str, required=True, help="enter wheter creating resources for data ingestion or queries")
def main(step):
    if step == "ingestion":
        print("Creating resources for data ingestion...")
        build_and_publish_layer()

    elif step == "query":
        print("Creating resources for data queries...")
    else:
        print("Invalid step. Please enter either 'ingestion' or 'query'.")

if __name__ == "__main__":
    main()