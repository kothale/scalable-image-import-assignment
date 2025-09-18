from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import datetime
import gdown
import shutil
import magic
import uuid
import logging
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Mount storage folder
if not os.path.exists("storage"):
    os.makedirs("storage")
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# DB connection
def get_db_connection():
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PostgreSQL connection failed: {str(e)}")

# Create table if not exists
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS images (
    id TEXT PRIMARY KEY,
    name TEXT,
    google_drive_id TEXT,
    size BIGINT,
    mime_type TEXT,
    storage_path TEXT,
    imported_at TIMESTAMP
)
""")
conn.commit()
cursor.close()
conn.close()

# Request model
class ImportRequest(BaseModel):
    url: str

# Import images from Google Drive
@app.post("/import")
async def import_images(req: ImportRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        temp_dir = "downloads"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        logger.info(f"Downloading from {req.url} to {temp_dir}")
        output = gdown.download_folder(req.url, output=temp_dir, quiet=False, remaining_ok=True)

        if output is None:
            logger.error("Download failed: Invalid public Google Drive folder URL")
            raise HTTPException(status_code=400, detail="Invalid public Google Drive folder URL")

        imported_count = 0
        valid_extensions = ('.jpg', '.png', '.gif', '.jpeg')
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if not file.lower().endswith(valid_extensions):
                    continue
                src_path = os.path.join(root, file)
                dest_path = os.path.join("storage", file)
                if os.path.exists(dest_path):
                    continue

                try:
                    file_size = os.path.getsize(src_path)
                    mime_type = magic.from_file(src_path, mime=True)
                    if not mime_type.startswith('image/'):
                        continue

                    gdrive_id = file  # placeholder
                    image_id = str(uuid.uuid4())
                    shutil.move(src_path, dest_path)

                    cursor.execute("""
                        INSERT INTO images (id, name, google_drive_id, size, mime_type, storage_path, imported_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (image_id, file, gdrive_id, file_size, mime_type, dest_path, datetime.datetime.now()))
                    conn.commit()
                    imported_count += 1
                except Exception as e:
                    logger.error(f"Error processing {file}: {str(e)}")
                    continue

        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"message": f"Imported {imported_count} images successfully"}

    except Exception as e:
        logger.error(f"Import error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# List images API
@app.get("/images")
async def list_images():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM images')
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# Get image file
@app.get("/image/{image_id}")
async def get_image(image_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT name, storage_path, mime_type FROM images WHERE id = %s', (image_id,))
        row = cursor.fetchone()
        if row:
            return FileResponse(row[1], media_type=row[2], filename=row[0])
        raise HTTPException(status_code=404, detail="Image not found")
    finally:
        cursor.close()
        conn.close()

# Frontend HTML
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Image Importer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; }
        h1, h2 { color: #333; }
        .form-container { margin-bottom: 20px; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        input[type="text"] { padding: 10px; width: 400px; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background-color: #45a049; }
        #import-status { color: #555; font-style: italic; }
        .image-list { list-style: none; padding: 0; }
        .image-list li { margin: 10px 0; padding: 10px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .image-list a { color: #0066cc; text-decoration: none; }
        .image-list a:hover { text-decoration: underline; }
        .image-list img { margin-top: 10px; max-width: 100px; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>Image Importer</h1>
    <div class="form-container">
        <h2>Import Images from Google Drive Folder</h2>
        <input type="text" id="url" placeholder="Public Google Drive Folder URL">
        <button onclick="importImages()">Import</button>
        <p id="import-status"></p>
    </div>
    <h2>Imported Images</h2>
    <ul class="image-list" id="image-list"></ul>
    <script>
        async function importImages() {
            const url = document.getElementById('url').value;
            const status = document.getElementById('import-status');
            status.textContent = 'Importing...';
            try {
                const res = await fetch('/import', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url})
                });
                const data = await res.json();
                status.textContent = data.message || 'Import completed';
                loadImages();
            } catch (err) {
                status.textContent = 'Error: ' + err.message;
            }
        }

        async function loadImages() {
            const list = document.getElementById('image-list');
            list.innerHTML = '';
            try {
                const res = await fetch('/images');
                const images = await res.json();
                if (!images.length) list.innerHTML = '<li>No images found.</li>';
                images.forEach(img => {
                    const li = document.createElement('li');
                    li.innerHTML = `
                        <strong>${img.name}</strong><br>
                        Size: ${img.size} bytes, Type: ${img.mime_type}<br>
                        <a href="/storage/${img.name}" target="_blank">View Image</a><br>
                        <img src="/storage/${img.name}" alt="${img.name}">
                    `;
                    list.appendChild(li);
                });
            } catch (err) {
                list.innerHTML = `<li class="error">Error loading images: ${err.message}</li>`;
            }
        }
        loadImages();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return html_content
