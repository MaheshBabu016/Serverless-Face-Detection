from flask import Flask, render_template, request, jsonify
import boto3
import os
from PIL import Image, ImageDraw
import requests
from io import BytesIO

app = Flask(__name__)

# ---------------- CONFIG ----------------
S3_BUCKET = os.getenv("S3_BUCKET", "face-detect-uploads")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "6e0362f946aa5a0198ae7f42ce09951c8fcb60274e628a60d8664e30dc5b6b99")

# AWS clients
s3 = boto3.client("s3")
rekognition = boto3.client("rekognition", region_name=AWS_REGION)

# ---------------- ROUTES ----------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty file name'}), 400

    filename = file.filename
    filepath = os.path.join("static/uploads", filename)
    os.makedirs("static/uploads", exist_ok=True)
    file.save(filepath)

    # Upload to S3
    s3.upload_file(filepath, S3_BUCKET, filename)

    # Call Rekognition
    with open(filepath, "rb") as img:
        response = rekognition.recognize_celebrities(Image={'Bytes': img.read()})

    # Open image for drawing
    image = Image.open(filepath)
    draw = ImageDraw.Draw(image)
    img_width, img_height = image.size

    detected_celebrities = []
    non_celebrity_faces = 0

    # Draw celebrity faces
    for celeb in response['CelebrityFaces']:
        name = celeb['Name']
        box = celeb['Face']['BoundingBox']
        left = img_width * box['Left']
        top = img_height * box['Top']
        width = img_width * box['Width']
        height = img_height * box['Height']

        draw.rectangle([(left, top), (left + width, top + height)], outline="green", width=4)
        draw.text((left, top - 10), name, fill="green")

        detected_celebrities.append(name)

    # Draw non-celebrity faces (Unrecognized)
    for face in response['UnrecognizedFaces']:
        box = face['BoundingBox']
        left = img_width * box['Left']
        top = img_height * box['Top']
        width = img_width * box['Width']
        height = img_height * box['Height']

        draw.rectangle([(left, top), (left + width, top + height)], outline="blue", width=3)
        non_celebrity_faces += 1

    # Save detected image
    detected_path = f"static/uploads/detected_{filename}"
    image.save(detected_path)

    # Fetch related images for celebrities
    celebrity_images = {}
    for celeb_name in detected_celebrities:
        url = f"https://serpapi.com/search.json?q={celeb_name}&tbm=isch&api_key={SERPAPI_KEY}"
        resp = requests.get(url)
        data = resp.json()
        images = [item["thumbnail"] for item in data.get("images_results", [])[:5]]
        celebrity_images[celeb_name] = images

    return jsonify({
        "original": filepath,
        "detected": detected_path,
        "celebrities": celebrity_images,
        "non_celebrity_faces": non_celebrity_faces
    })


if __name__ == '__main__':
    app.run(debug=True)
