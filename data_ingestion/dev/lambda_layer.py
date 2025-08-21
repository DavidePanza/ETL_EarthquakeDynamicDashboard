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
    
    # Use Docker
    subprocess.run([
        "docker", "build", "-f", "Dockerfile.lambda-layer", "-t", "lambda-layer", "."
    ], check=True)
    
    container_id = subprocess.check_output([
        "docker", "create", "lambda-layer"
    ]).decode().strip()
    
    subprocess.run([
        "docker", "cp", f"{container_id}:/var/task/python", "."
    ], check=True)
    
    subprocess.run(["docker", "rm", container_id], check=True)
    print("Docker build successful")
    
    # Create ZIP (your existing code)
    with zipfile.ZipFile("layer.zip", 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk("python"):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, file_path)
    
    print(f"Layer size: {os.path.getsize('layer.zip') / (1024*1024):.1f} MB")

    # Upload layer (your existing code)
    lambda_client = boto3.client('lambda', region_name=region)
    with open("layer.zip", 'rb') as f:
        response = lambda_client.publish_layer_version(
            LayerName="earthquake-deps",
            Content={'ZipFile': f.read()},
            CompatibleRuntimes=['python3.11']
        )

    print(f"Layer ARN: {response['LayerVersionArn']}")

    # Update .env file (improved to avoid duplicates)
    env_content = ""
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            lines = f.readlines()
        lines = [line for line in lines if not line.startswith('LAMBDA_LAYER_ARN_DATA_INGESTION=')]
        env_content = ''.join(lines)
    
    with open('.env', 'w') as f:
        f.write(env_content)
        f.write(f"LAMBDA_LAYER_ARN_DATA_INGESTION={response['LayerVersionArn']}\n")

    # Cleanup
    shutil.rmtree(layer_dir)
    os.remove("layer.zip")