# Earthquake Dynamic Dashboard

## Overview

Earthquake Dynamic Dashboard is a React app that allows users to visualize earthquakes by displaying their geographical as well as temporal occurrence on a map of the world. 

In this repo you can find the code to implement data ingestion and cleaning from https://earthquake.usgs.gov as well as to create the React-powered dashboard to display the earthquake data. 

This toy project intentionally aims at exploring options from AWS resources to create an ETL pipeline to carry out the data ingestion/processing.

## Try the App

You can try the app yourself at this link:

[Dynamic Earthquake Dashboard](https://huggingface.co/spaces/davidepanza/Dynamic_Earthquake_Dashboard?logs=container)

Only data from 20.08.2025 onwards are available as this is the date when the scraping cron job started.

## App Hosting and Data

- The React dashboard is hosted on Hugging Face Spaces
- Data are ingested daily through a cron job triggered on GitHub Actions

## Data Flow Overview

The flow of the data scraping backend is the following:
- Lambda (scrapes https://earthquake.usgs.gov) → S3

The query is triggered by the React dashboard with the following flow:
- **Frontend to Backend:** React Frontend → FastAPI Proxy → API Gateway → Lambda → Athena → S3 Data
- **Response Flow:** S3 Data → Athena Results → Lambda Processing → API Gateway → FastAPI Proxy → React Frontend

## Notes

The AWS resources are created using AWS SDK. Terraform or CloudFormation would have been a more elegant way to achieve the same, but I preferred to rely on a more programmatic approach.