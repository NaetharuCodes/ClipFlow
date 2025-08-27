from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from api.clips import router as clips_router
from api.processing import router as processing_router
from api.config import router as config_router

app = FastAPI(title="ClipFlow", description="Video Concatenation Tool", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("output", exist_ok=True)

# Mount uploads directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/output", StaticFiles(directory="output"), name="output")

# Include API routers
app.include_router(clips_router, prefix="/api/clips", tags=["clips"])
app.include_router(processing_router, prefix="/api/process", tags=["processing"])
app.include_router(config_router, prefix="/api/config", tags=["config"])

@app.get("/")
async def root():
    return {"message": "ClipFlow API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}