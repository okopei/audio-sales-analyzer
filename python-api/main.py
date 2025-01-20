from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    try:
        logger.info(f"Received audio file: {audio.filename}")
        contents = await audio.read()
        logger.info(f"File size: {len(contents)} bytes")
        
        # テスト用に固定の応答を返す
        return {
            "status": "success",
            "original_text": "テスト応答：音声が受信されました",
            "steps": {
                "file_received": True,
                "speech_recognition_completed": True
            }
        }
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error processing audio: {error_message}")
        return {
            "status": "error",
            "error": error_message,
            "steps": {
                "file_received": False,
                "speech_recognition_completed": False
            }
        } 