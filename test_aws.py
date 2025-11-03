import boto3

try:
    s3 = boto3.client('s3')
    response = s3.list_buckets()
    print("✅ AWS credentials working! Here's your buckets:")
    for bucket in response['Buckets']:
        print(" -", bucket['Name'])
except Exception as e:
    print("❌ Error:", e)
