import boto3
import json
import uuid
import csv
import io
import os

s3 = boto3.client('s3')
BUCKET_NAME = os.environ['BUCKET_NAME']

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        batch = body.get('batch', [])
        
        if not batch:
            return {'statusCode': 400, 'body': 'Empty batch'}

        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        for row in batch:
            writer.writerow([row['ax'], row['ay'], row['az'], row['gx'], row['gy'], row['gz']])

        file_name = f"train/harvest-{uuid.uuid4().hex}.csv"
        s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=csv_buffer.getvalue())

        return {
            'statusCode': 200, 
            'body': json.dumps({'msg': f'Successfully saved {len(batch)} sensor readings'})
        }
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}