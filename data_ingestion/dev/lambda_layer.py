
import boto3
import subprocess
import zipfile
import os
import shutil
from pathlib import Path

def build_and_publish_layer():
    region = os.environ.get('AWS_REGION', 'us-east-1')
    
    layer_dir = Path("python")
    if layer_dir.exists():
        shutil.rmtree(layer_dir)
    layer_dir.mkdir(exist_ok=True)
    
    subprocess.run([
        "pip", "install", "pandas", "--only-binary=:all:", "-t", str(layer_dir)
    ], check=True)
    
    # Create properly structured ZIP for Lambda layer
    with zipfile.ZipFile("layer.zip", 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk("python"):  # Start from python directory
            for file in files:
                file_path = os.path.join(root, file)
                # Keep the python/ prefix for Lambda layers
                zipf.write(file_path, file_path)
    
    # Check ZIP before upload
    print(f"Layer size: {os.path.getsize('layer.zip') / (1024*1024):.1f} MB")

    # Upload layer
    lambda_client = boto3.client('lambda', region_name=region)
    with open("layer.zip", 'rb') as f:
        response = lambda_client.publish_layer_version(
            LayerName="earthquake-deps",
            Content={'ZipFile': f.read()},
            CompatibleRuntimes=['python3.11']
        )

    print(f"Layer ARN: {response['LayerVersionArn']}")

    # Save to .env file
    with open('.env', 'a') as f:
        f.write(f"LAMBDA_LAYER_ARN_DATA_INGESTION={response['LayerVersionArn']}\n")

    # Cleanup
    shutil.rmtree(layer_dir)
    os.remove("layer.zip")