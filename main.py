import os
import base64
import json
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ocr_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ocr_app")

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

# Initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    logger.error("OPENAI_API_KEY not set in environment")
    raise ValueError("OPENAI_API_KEY not set in environment")
client = OpenAI(api_key=api_key)

# Path to the blank form template
BLANK_FORM_PATH = os.path.join(os.path.dirname(__file__), 'static', 'blank_cnam_form.png')

# JSON Schema for Structured Outputs
schema = {
    "type": "object",
    "properties": {
        "document_type": {
            "type": "string",
            "const": "Bulletin de remboursement des frais de soins"
        },
        "metadata": {
            "type": "object",
            "properties": {
                "identifiant_unique": {"type": "string"},
                "regime": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["CNSS", "CNRPS", "Convention bilatérale"]}
                }
            },
            "required": ["identifiant_unique", "regime"],
            "additionalProperties": False
        },
        "assure_social": {
            "type": "object",
            "properties": {
                "nom": {"type": "string"},
                "prenom": {"type": "string"},
                "adresse": {
                    "type": "object",
                    "properties": {
                        "ligne_1": {"type": "string"},
                        "ligne_2": {"type": "string"},
                        "code_postal": {"type": "string"}
                    },
                    "required": ["ligne_1", "ligne_2", "code_postal"],
                    "additionalProperties": False
                }
            },
            "required": ["nom", "prenom", "adresse"],
            "additionalProperties": False
        },
        "Le_malade": {
            "type": "object",
            "properties": {
                "type_relation": {"type": "string", "enum": ["assure_social", "conjoint", "enfant", "ascendant"]},
                "prenom": {"type": "string"},
                "nom": {"type": "string"},
                "date_naissance": {"type": "string"},
                "telephone": {"type": "string"},
                "signature": {"type": "string"}
            },
            "required": ["type_relation", "prenom", "nom", "date_naissance", "telephone", "signature"],
            "additionalProperties": False
        }
    },
    "required": ["document_type", "metadata", "assure_social", "Le_malade"],
    "additionalProperties": False
}

# FastAPI application
app = FastAPI()

system_prompt = (
    """
    You are an OCR assistant extracting the handwritten values from a filled CNAM form.
    You will receive two images: the blank template first, then the filled form.
    The blank template helps you identify form fields and understand the structure.
    Only output JSON that strictly conforms to the provided schema.
    """
)

# Load the blank form once at startup
try:
    with open(BLANK_FORM_PATH, "rb") as f:
        BLANK_FORM_DATA = f.read()
        BLANK_FORM_B64 = base64.b64encode(BLANK_FORM_DATA).decode()
    logger.info(f"Successfully loaded blank form from {BLANK_FORM_PATH}")
except FileNotFoundError:
    logger.error(f"Blank form template not found at {BLANK_FORM_PATH}")
    BLANK_FORM_B64 = None

@app.post("/extract")
async def extract(
    filled_form: UploadFile = File(...)
):
    """
    Extract information from a filled CNAM form.
    
    Only requires the filled form to be uploaded.
    The blank template form is automatically included in the request.
    
    Returns a structured JSON with the extracted information.
    """
    request_id = os.urandom(4).hex()  # Generate a simple request ID for tracking
    logger.info(f"[{request_id}] Processing new extraction request for file: {filled_form.filename}")
    
    try:
        # Check if blank form is available
        if BLANK_FORM_B64 is None:
            logger.error(f"[{request_id}] Blank form template not available")
            raise HTTPException(
                status_code=500, 
                detail=f"Blank form template not found. Please ensure it exists at {BLANK_FORM_PATH}"
            )
        
        # Prepare image inputs - always include both forms in order
        inputs = []
        
        # First add the blank form (automatically)
        inputs.append({"type": "input_image", "image_url": f"data:image/png;base64,{BLANK_FORM_B64}"})
        logger.debug(f"[{request_id}] Added blank form to request")
        
        # Then add the filled form
        filled_data = await filled_form.read()
        filled_b64 = base64.b64encode(filled_data).decode()
        inputs.append({"type": "input_image", "image_url": f"data:image/png;base64,{filled_b64}"})
        logger.debug(f"[{request_id}] Added filled form to request (size: {len(filled_data)} bytes)")

        # Call OpenAI Vision API with structured output
        logger.info(f"[{request_id}] Sending request to OpenAI API")
        try:
            response = client.responses.create(
                model="gpt-4o-2024-08-06",
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": inputs}
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "cnam_form",
                        "schema": schema,
                        "strict": True
                    }
                }
            )
            
            # Log the entire response object for debugging
            logger.debug(f"[{request_id}] Raw API response: {response}")
            
            # Check if response has output_text
            if not hasattr(response, 'output_text') or not response.output_text:
                logger.error(f"[{request_id}] Empty output_text in OpenAI response")
                with open(f"error_response_{request_id}.log", "w") as f:
                    f.write(str(response))
                return JSONResponse(
                    status_code=500,
                    content={"error": "Empty response from OpenAI API", "request_id": request_id}
                )
            
            # Log the output text
            logger.info(f"[{request_id}] Received output_text from OpenAI API")
            logger.debug(f"[{request_id}] Response output_text: {response.output_text}")
            
            # Try to parse the JSON response
            try:
                parsed_data = json.loads(response.output_text)
                logger.info(f"[{request_id}] Successfully parsed JSON response")
                return JSONResponse(status_code=200, content=parsed_data)
            except json.JSONDecodeError as json_err:
                logger.error(f"[{request_id}] Failed to parse response as JSON: {str(json_err)}")
                # Save the raw output to a file for debugging
                error_file = f"json_error_{request_id}.log"
                with open(error_file, "w") as f:
                    f.write(response.output_text)
                logger.info(f"[{request_id}] Saved raw output to {error_file}")
                
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Failed to parse OpenAI response as JSON",
                        "details": str(json_err),
                        "request_id": request_id,
                        "raw_output": response.output_text[:1000]  # Include the first 1000 chars for debugging
                    }
                )
                
        except Exception as api_err:
            logger.error(f"[{request_id}] OpenAI API error: {str(api_err)}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "OpenAI API error",
                    "details": str(api_err),
                    "request_id": request_id
                }
            )

    except Exception as e:
        logger.error(f"[{request_id}] Unhandled server error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server error",
                "details": str(e),
                "request_id": request_id
            }
        )

# To run:
# uvicorn main:app --reload