# Scalable Image Import System

## 🚀 Working Site
[[Live Application URL](https://scalable-image-import.onrender.com)]

---

## 📖 Project Overview
This project implements a scalable backend system to import images from a public Google Drive folder and store them in cloud storage. 
Image metadata is saved in PostgreSQL, and a simple frontend displays imported images.

**Tech Stack:**
- Backend: FastAPI
- Frontend: Embedded in FastAPI (HTML + JS)
- Database: PostgreSQL (Neon)
- Storage: Local folder (`storage`)
- Deployment: Render

---

## 📂 Repository Structure
scalable-image-import/
├─ main.py
├─ requirements.txt
├─ .env.sample
├─ storage/ (ignored)
├─ render-build.sh
└─ README.md



---

## ⚙️ Setup Instructions

### 
1. Clone Repository
```bash
git clone https://github.com/kothale/scalable-image-import-assignment.git
cd scalable-image-import-assignment

### 2. Create Virtual Environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

3. Install Dependencies
pip install -r requirements.txt

4. Environment Variables
Create a .env file:
DATABASE_URL=postgresql://<username>:<password>@<host>:<port>/<database>?sslmode=require

5. Run Locally
uvicorn main:app --reload --host 0.0.0.0 --port 8000


🔌 API Documentation
POST /import

Import images from Google Drive.

Request:

{
  "url": "https://drive.google.com/drive/folders/..."
}


Response:

{
  "message": "Imported 5 images successfully"
}

GET /images

Get metadata of all imported images.

Response:

[
  {
    "id": "uuid",
    "name": "image1.jpg",
    "google_drive_id": "fileid",
    "size": 12345,
    "mime_type": "image/jpeg",
    "storage_path": "storage/image1.jpg",
    "imported_at": "2025-09-18T12:00:00"
  }
]

GET /image/{image_id}

Download specific image by ID.

🏗 Architecture & Design

Single FastAPI backend with embedded frontend

PostgreSQL stores metadata

Local storage/ folder for images

Scalable: can add S3 storage, background workers, and Dockerization

📦 Deployment (Render)

Connect GitHub repo to Render → New Web Service

Set Environment Variable: DATABASE_URL

Build Command:

./render-build.sh && pip install -r requirements.txt


Start Command:

uvicorn main:app --host 0.0.0.0 --port $PORT


Deploy → Use public URL

⚡ Notes on Scalability

Supports small to medium imports

For large-scale (10k+ images):

Use cloud storage (S3, MinIO)

Background workers (Celery + Redis)

DB indexing on google_drive_id

Chunked downloads and retries

👨‍💻 Author

GitHub: https://github.com/kothale  



---
