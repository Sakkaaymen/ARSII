import os, base64, json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# 1) Read & encode the filled form
with open("static/test2.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
data_url = f"data:image/png;base64,{b64}"

with open("static/empty_form.png", "rb") as f:
    b64_empty = base64.b64encode(f.read()).decode()
data_url = f"data:image/png;base64,{b64_empty}"


empty_url = f"data:image/png;base64,{b64}"

schema = {
    "type": "object",
    "properties": {
        "document_type": {
            "type": "string",
            "const": "Bulletin de remboursement des frais de soins",
            "description": "Fixed document title"
        },
        "metadata": {
            "type": "object",
            "properties": {
                "identifiant_unique": {
                    "type": "string",
                    "description": "Numéro d'identification de l'assuré"
                },
                "regime": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["CNSS", "CNRPS", "Convention bilatérale"]
                    },
                    "description": "Régime de l'assuré (cases à cocher)"
                }
            },
            "required": ["identifiant_unique", "regime"],
            "additionalProperties": False
        },
        "assure_social": {
            "type": "object",
            "properties": {
                "nom": {
                    "type": "string",
                    "description": "Nom de l'assuré"
                },
                "prenom": {
                    "type": "string",
                    "description": "Prénom de l'assuré"
                },
                "adresse": {
                    "type": "object",
                    "properties": {
                        "ligne_1": {
                            "type": "string",
                            "description": "Adresse ligne 1"
                        },
                        "ligne_2": {
                            "type": "string",
                            "description": "Adresse ligne 2 (localité)"
                        },
                        "code_postal": {
                            "type": "string",
                            "description": "Code postal"
                        }
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
                "type_relation": {
                    "type": "string",
                    "enum": ["assure_social", "conjoint", "enfant", "ascendant"],
                    "description": "Relation du patient désignée par la case cochée"
                },
                "prenom": {
                    "type": "string",
                    "description": "Prénom du malade"
                },
                "nom": {
                    "type": "string",
                    "description": "Nom du malade"
                },
                "date_naissance": {
                    "type": "string",
                    "description": "Date de naissance du malade (JJ‑MM‑AAAA)"
                },
                "telephone": {
                    "type": "string",
                    "description": "Numéro de portable du malade"
                },
                "signature": {
                    "type": "string",
                    "description": "Signature ou marque manuscrite"
                }
            },
            "required": [
                "type_relation",
                "prenom",
                "nom",
                "date_naissance",
                "telephone",
                "signature"
            ],
            "additionalProperties": False
        }
    },
    "required": ["document_type", "metadata", "assure_social", "Le_malade"],
    "additionalProperties": False
}


system_prompt = """
You are an OCR assistant extracting the *handwritten* values from a filled CNAM form.
There is a row of four checkboxes for patient relationship:
  1. L'ascendant
  2. L'enfant
  3. Le conjoint
  4. L'assuré social

Look at exactly where the “X” mark lands in that row.
- If it's in the first box, choose “ascendant”; in the second, “enfant”; third, “conjoint”; fourth, “assure_social”.
"""

response = client.responses.create(
    model="gpt-4o-2024-08-06",
    input=[
        {"role":"system", "content": system_prompt},
        {"role":"user",   "content":[
            {"type":"input_image","image_url":empty_url},
            {"type":"input_image","image_url":data_url,}
        ]}
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
# 3) Print the raw response
# 4) Parse and use
filled = json.loads(response.output_text)
print(json.dumps(filled, indent=2, ensure_ascii=False))

# [L'ascendant (*) L'enfant () Le conjoint L'assuré social]