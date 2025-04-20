# api/routes/ocr.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from db.models import OcrLogCreate, OcrLogRead
from api.dependencies import get_ocr_repository
from core.ocr import OcrProcessor
from config import logger

def get_ocr_processor():
    return OcrProcessor()

router = APIRouter()

@router.post("/extract", response_model=OcrLogRead)
async def extract(
    filled_form: UploadFile = File(...),
    ocr_processor = Depends(get_ocr_processor),
    ocr_repository = Depends(get_ocr_repository)
):
    try:
        # Process the form
        filename, extracted_data = await ocr_processor.process_form(filled_form)
        
        # Create log entry
        log_entry = OcrLogCreate(file_name=filename, extracted_data=extracted_data)
        
        # Save to database
        result = await ocr_repository.create(log_entry)
        return result
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in extract endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")