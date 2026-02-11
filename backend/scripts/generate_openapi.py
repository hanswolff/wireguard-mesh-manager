#!/usr/bin/env python3
"""Generate OpenAPI specification from the FastAPI app."""

import json
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


def generate_openapi():
    """Generate and save OpenAPI specification."""
    try:
        # Generate OpenAPI schema
        openapi_schema = app.openapi()

        # Save to file
        output_path = Path(__file__).parent.parent / "openapi.json"
        with output_path.open("w") as f:
            json.dump(openapi_schema, f, indent=2)

        print(f"OpenAPI specification generated successfully: {output_path}")
        print(f"Generated {len(openapi_schema.get('paths', {}))} API endpoints")

    except Exception as e:
        print(f"Error generating OpenAPI spec: {e}")
        sys.exit(1)


if __name__ == "__main__":
    generate_openapi()
