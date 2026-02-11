"""Gemini API client for invoice extraction.

Handles communication with Google's Gemini 2.0 Flash API for
multi-language invoice/receipt image analysis.
"""

import base64
import json
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from loguru import logger

from src.config import Config


def get_extraction_prompt(target_lang: str, source_lang: str) -> str:
    return f"""You are an expert at reading receipts and invoices.
Analyze this image and extract all information.

IMPORTANT:
- Detect the language of the receipt (Japanese, English, Chinese, etc.)
- Keep original text for store names and item names
- Also provide translated versions in {target_lang} if not already in {target_lang}
- Use 24-hour time format for timestamps
- If you cannot read certain fields clearly, use null

Return the data as a valid JSON object with this exact structure:
{{
  "store_name": "store name in original language",
  "store_name_translated": "store name in {target_lang} (if different, otherwise null)",
  "store_address": "full address if visible, null otherwise",
  "timestamp": "YYYY-MM-DDTHH:MM:SS format, use best estimate for date/time",
  "items": [
    {{
      "name": "item name in original language",
      "name_translated": "item name in {target_lang} (if different)",
      "quantity": 1,
      "unit_price": 100,
      "total_price": 100,
      "category": "food|beverage|transport|lodging|shopping|entertainment|health|other",
      "subcategory": "specific type like meal, snack, coffee, train, hotel, souvenir, etc."
    }}
  ],
  "subtotal": 900,
  "tax": 90,
  "total": 990,
  "currency": "JPY|TWD|USD|EUR|KRW|CNY|GBP|HKD",
  "original_language": "ja|en|zh-TW|zh-CN|ko|other",
  "notes": "any additional observations about the receipt"
}}

Rules:
1. All numeric values should be numbers, not strings
2. If tax is included in prices (内税), try to identify the tax amount. If subtotal is not explicitly listed, use null.
3. If you see 税込 or similar, the total already includes tax
4. Category must be one of: food, beverage, transport, lodging, shopping, entertainment, health, other
5. For Japanese convenience stores (ローソン, セブンイレブン, ファミリーマート), common items:
   - おにぎり = rice ball (food/snack)
   - パン = bread (food/snack)
   - お茶/水 = tea/water (beverage/soft_drink)
   - コーヒー = coffee (beverage/coffee)
6. Return ONLY the JSON, no markdown code blocks or other text
"""


class GeminiClient:
    """Client for Gemini API interactions."""

    # Prompt template for invoice extraction
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini client.

        Args:
            api_key: Gemini API key. If not provided, uses Config.GEMINI_API_KEY
        """
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model_name = Config.GEMINI_MODEL
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        """Lazy initialization of the Gemini client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "Gemini API key not configured. "
                    "Set GEMINI_API_KEY environment variable or pass api_key to constructor."
                )
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def extract_invoice_data(self, image_path: str | Path) -> dict:
        """Extract invoice data from an image.

        Args:
            image_path: Path to the invoice/receipt image

        Returns:
            Dictionary containing extracted invoice data

        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If API key not configured or extraction fails
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        # Determine MIME type
        mime_type = self._get_mime_type(image_path)

        # Create content parts
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(
                        data=base64.standard_b64decode(image_data),
                        mime_type=mime_type,
                    ),
                    types.Part.from_text(
                        text=get_extraction_prompt(
                            Config.PRIMARY_LANGUAGE, Config.DESTINATION_LANGUAGE
                        )
                    ),
                ],
            )
        ]

        # Generate response
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,  # Low temperature for consistent extraction
                max_output_tokens=2048,
            ),
        )

        # Parse JSON response
        return self._parse_response(response.text)

    @staticmethod
    def _get_mime_type(image_path: Path) -> str:
        """Get MIME type for an image file."""
        extension = image_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".heic": "image/heic",
            ".heif": "image/heif",
            ".webp": "image/webp",
        }
        return mime_types.get(extension, "image/jpeg")

    @staticmethod
    def _parse_response(response_text: str) -> dict:
        """Parse JSON response from Gemini.

        Handles potential markdown code blocks or extra text.
        """

        # Clean up response
        text = response_text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Gemini response as JSON: {e}\nResponse: {text}") from e


def test_client():
    """Simple test function for the Gemini client."""
    client = GeminiClient()
    logger.info(f"Client initialized with model: {client.model_name}")
    logger.info(f"API key configured: {bool(client.api_key)}")


if __name__ == "__main__":
    test_client()
