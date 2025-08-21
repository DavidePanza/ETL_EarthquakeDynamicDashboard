import boto3
import subprocess
import zipfile
import os
import shutil
from pathlib import Path

def build_and_publish_layer():
    # Install packages
    layer_dir = Path("python")
    layer_dir.mkdir(exist_ok=True)
    subprocess.run(["pip", "install", "pandas", "pyarrow", "-t", str(layer_dir)], check=True)

    # Create ZIP
    with zipfile.ZipFile("layer.zip", 'w') as zipf:
        for root, dirs, files in os.walk(layer_dir):
            for file in files:
                file_path = Path(root) / file
                zipf.write(file_path, file_path.relative_to(Path(".")))

    # Upload layer
    lambda_client = boto3.client('lambda')
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

# Only run when script is executed directly
if __name__ == "__main__":
    build_and_publish_layer()