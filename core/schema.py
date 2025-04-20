# core/schema.py

# --- JSON Schema for OCR ---
CNAM_FORM_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string", "const": "Bulletin de remboursement des frais de soins"},
        "metadata": {
            "type": "object",
            "properties": {
                "identifiant_unique": {"type": "string"},
                "regime": {"type": "array", "items": {"type": "string", "enum": ["CNSS", "CNRPS", "Convention bilatérale"]}}
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