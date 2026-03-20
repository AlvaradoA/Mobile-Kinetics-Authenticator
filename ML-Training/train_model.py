import boto3
import csv
import json
import os
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# ⚠️ PASTE YOUR STAGE 1 BUCKET NAME HERE
BUCKET_NAME = "mka-data-lake-HEX" 
s3 = boto3.client('s3', region_name='us-east-1')

def train_edge_ml():
    print("🚀 Downloading data from S3 Data Lake...")
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix='train/')
    
    X_train = []
    
    for obj in response.get('Contents', []):
        if obj['Key'].endswith('.csv'):
            csv_obj = s3.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
            lines = csv_obj['Body'].read().decode('utf-8').splitlines()
            reader = csv.reader(lines)
            for row in reader:
                if len(row) == 6:
                    X_train.append([float(x) for x in row])

    if not X_train:
        print("❌ No data found.")
        return

    # Convert to NumPy array so PCA and Matplotlib can process it
    X_train_np = np.array(X_train)

    print(f"🧠 Training K-Means ML Algorithm on {len(X_train_np)} data points...")
    # Group your normal movements into 3 distinct behavioral clusters
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_train_np)

    # ---------------------------------------------------------
    # 3D VISUALIZATION BLOCK for the LaTeX Report
    # ---------------------------------------------------------
    print("📊 Generating 3D PCA Visualization for the report...")
    
    # Squash 6D telemetry down to 3D for plotting
    pca = PCA(n_components=3)
    X_3d = pca.fit_transform(X_train_np)
    centroids_3d = pca.transform(kmeans.cluster_centers_)

    # Set up the 3D plot
    plt.style.use('seaborn-v0_8-whitegrid')
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d') # Creates the 3D axis
    
    # Scatter the actual telemetry data in 3D
    scatter = ax.scatter(X_3d[:, 0], X_3d[:, 1], X_3d[:, 2], 
                         c=labels, cmap='viridis', s=20, alpha=0.5, label='Raw Telemetry')
    
    # Scatter the mathematical centroids as giant red X's
    ax.scatter(centroids_3d[:, 0], centroids_3d[:, 1], centroids_3d[:, 2], 
               s=250, c='#e74c3c', marker='X', edgecolor='black', linewidth=2, label='Behavioral Centroids')

    ax.set_title('K-Means Behavioral Clusters (6D Telemetry Reduced to 3D)', fontweight='bold', fontsize=14)
    ax.set_xlabel('Principal Component 1')
    ax.set_ylabel('Principal Component 2')
    ax.set_zlabel('Principal Component 3')
    
    # Format Legend
    handles, _ = scatter.legend_elements()
    legend_labels = [f"Cluster {i+1}" for i in range(3)]
    ax.legend(handles, legend_labels + ['Centroids'], loc='best', frameon=True, shadow=True)

    plt.tight_layout()
    plt.savefig('kmeans_clusters_3d.png', dpi=300)
    print("🖼️  Saved 3D visualization to 'kmeans_clusters_3d.png'")
    # ---------------------------------------------------------

    print("🔬 Extracting ML Weights for Serverless Edge Deployment...")
    # 1. Extract the center coordinates of your 3 normal behavior clusters
    centroids = kmeans.cluster_centers_.tolist()
    
    # 2. Calculate the "decision boundary" for anomalies (95th percentile distance)
    distances = kmeans.transform(X_train_np)
    min_distances = np.min(distances, axis=1)
    threshold = float(np.percentile(min_distances, 95))

    # Serialize the ML brain into pure JSON
    ml_brain = {
        'centroids': centroids,
        'threshold': threshold
    }

    with open('brain.json', 'w') as f:
        json.dump(ml_brain, f)

    print("☁️ Uploading Edge ML Brain to S3...")
    s3.upload_file('brain.json', BUCKET_NAME, 'output/brain.json')
    
    os.remove('brain.json')
    print(f"✅ EDGE ML TRAINING COMPLETE! Brain saved to s3://{BUCKET_NAME}/output/brain.json")

if __name__ == "__main__":
    train_edge_ml()