import json
import requests
from jsonschema import validate, ValidationError

# Configuration
# SCHEMA_URL = "https://example.com/path/to/model_descriptor_schema.json"
SCHEMA_URL = "model_card_schema.json"
DOCUMENT_PATH = "example.json"

def validate_json(schema_url, document_path):
    try:
        # Fetch the schema if url or load the schema
        if schema_url.startswith("http"):
            schema = requests.get(schema_url).json()
        else:
            with open(schema_url) as schema_file:
                schema = json.load(schema_file)

        # Load the JSON document
        with open(document_path) as doc_file:
            document = json.load(doc_file)

        # Validate the document
        validate(instance=document, schema=schema)
        print("JSON document is valid.")
    except ValidationError as e:
        print(f"Validation error: {e.message}")
    except Exception as e:
        print(f"Error: {e}")

# Run the validation
if __name__ == "__main__":
    validate_json(SCHEMA_URL, DOCUMENT_PATH)
