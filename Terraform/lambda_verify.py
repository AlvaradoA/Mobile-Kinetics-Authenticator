import boto3
import json
import os
import math

s3 = boto3.client('s3')
BUCKET_NAME = os.environ['BUCKET_NAME']
ml_brain = None

def calculate_distance(p1, p2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))

def lambda_handler(event, context):
    global ml_brain
    try:
        # Load the ML Centroids from S3 into memory
        if ml_brain is None:
            print("🧠 Cold Start: Loading ML Brain from S3...")
            obj = s3.get_object(Bucket=BUCKET_NAME, Key='output/brain.json')
            ml_brain = json.loads(obj['Body'].read().decode('utf-8'))

        # Parse live data from the React Native app
        body = json.loads(event['body'])
        features_str = body['features'].split(',')
        live_point = [
            float(features_str[0]), float(features_str[1]), float(features_str[2]), 
            float(features_str[3]), float(features_str[4]), float(features_str[5])
        ]
        
        print(f"📡 Received Live Sensor Data: {live_point}")

        # Find the distance to the nearest normal behavior cluster
        min_distance = float('inf')
        for centroid in ml_brain['centroids']:
            dist = calculate_distance(live_point, centroid)
            if dist < min_distance:
                min_distance = dist

        # ⚠️ STRICT LEVER: Only allow 40% variance from normal behavior
        strict_threshold = ml_brain['threshold'] * 0.4
        
        is_locked = True if min_distance > strict_threshold else False

        # --- CLOUDWATCH PRINTED FEEDBACK ---
        print("-" * 40)
        print(f"📏 Calculated Distance: {min_distance:.4f}")
        print(f"🛑 Strict Threshold:    {strict_threshold:.4f}")
        print(f"🔒 Final Decision:      {'LOCKED' if is_locked else 'OK'}")
        print("-" * 40)

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'anomaly_score': round(min_distance, 3),
                'status': 'LOCKED' if is_locked else 'OK'
            })
        }
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}