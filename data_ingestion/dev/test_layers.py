import boto3
import os

def test_aws_layer_access():
    """Test if we can access AWS managed layers"""
    
    region = os.environ.get('AWS_REGION', 'us-east-1')
    print(f"Testing AWS layer access in region: {region}")
    
    # Test layer ARNs for different regions
    test_layers = {
        'us-east-1': 'arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python311:13',
        'us-west-2': 'arn:aws:lambda:us-west-2:336392948345:layer:AWSSDKPandas-Python311:13',
        'eu-west-1': 'arn:aws:lambda:eu-west-1:336392948345:layer:AWSSDKPandas-Python311:13',
    }
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Test 1: List layers (should work if basic access is available)
    try:
        print("\n1. Testing basic layer listing...")
        response = lambda_client.list_layers()
        print(f"   SUCCESS: Can list layers. Found {len(response.get('Layers', []))} layers")
    except Exception as e:
        print(f"   FAILED: Cannot list layers - {e}")
        return False
    
    # Test 2: Try to get layer version info for your region
    layer_arn = test_layers.get(region)
    if not layer_arn:
        print(f"\n2. No test layer defined for region {region}")
        print(f"   Available test regions: {list(test_layers.keys())}")
        return False
    
    try:
        print(f"\n2. Testing access to AWS managed layer...")
        print(f"   Layer ARN: {layer_arn}")
        
        # Extract layer name and version from ARN
        layer_name = layer_arn.split(':')[-2]
        layer_version = int(layer_arn.split(':')[-1])
        
        response = lambda_client.get_layer_version(
            LayerName=layer_name,
            VersionNumber=layer_version
        )
        print(f"   SUCCESS: Can access AWS managed layer")
        print(f"   Layer size: {response.get('Content', {}).get('CodeSize', 'Unknown')} bytes")
        print(f"   Compatible runtimes: {response.get('CompatibleRuntimes', [])}")
        return True
        
    except Exception as e:
        print(f"   FAILED: Cannot access AWS managed layer - {e}")
        
        # Test 3: Try accessing a public layer by account ID
        try:
            print(f"\n3. Testing alternative access method...")
            response = lambda_client.list_layer_versions(
                LayerName=f"arn:aws:lambda:{region}:336392948345:layer:AWSSDKPandas-Python311"
            )
            if response.get('LayerVersions'):
                print(f"   SUCCESS: Found {len(response['LayerVersions'])} versions of the layer")
                latest_version = response['LayerVersions'][0]['Version']
                print(f"   Latest version: {latest_version}")
                return True
            else:
                print(f"   FAILED: No layer versions found")
        except Exception as e2:
            print(f"   FAILED: Alternative access also failed - {e2}")
        
        return False

def check_permissions():
    """Check what Lambda permissions we have"""
    print("\n=== Checking Lambda Permissions ===")
    
    region = os.environ.get('AWS_REGION', 'us-east-1')
    lambda_client = boto3.client('lambda', region_name=region)
    
    permissions_tests = [
        ('list_functions', 'List Lambda functions'),
        ('list_layers', 'List Lambda layers'),
    ]
    
    for action, description in permissions_tests:
        try:
            getattr(lambda_client, action)()
            print(f"✓ {description}: ALLOWED")
        except Exception as e:
            print(f"✗ {description}: DENIED - {e}")

if __name__ == "__main__":
    print("=== AWS Lambda Layer Access Test ===")
    
    # Check basic AWS connection
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"AWS Account: {identity.get('Account')}")
        print(f"User/Role: {identity.get('Arn')}")
    except Exception as e:
        print(f"AWS connection failed: {e}")
        exit(1)
    
    # Check permissions
    check_permissions()
    
    # Test layer access
    print(f"\n=== Testing Layer Access ===")
    success = test_aws_layer_access()
    
    if success:
        print("\n✓ AWS managed layers are accessible!")
        print("You can proceed with using AWS managed layers.")
    else:
        print("\n✗ Cannot access AWS managed layers.")
        print("You'll need to build a custom layer or use a different approach.")