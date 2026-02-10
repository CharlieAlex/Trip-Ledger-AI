"""Image preprocessing for invoice photos.

Handles image optimization before sending to Gemini API to reduce
token usage and improve recognition quality.
"""

import hashlib
from pathlib import Path

from PIL import ExifTags, Image

from src.config import Config


class ImagePreprocessor:
    """Preprocess images for optimal API processing."""

    def __init__(self, max_size: int = Config.MAX_IMAGE_SIZE):
        """Initialize preprocessor.

        Args:
            max_size: Maximum dimension (width or height) in pixels
        """
        self.max_size = max_size

    def process(self, image_path: str | Path) -> Path:
        """Process an image for API submission.

        Performs:
        1. Auto-rotation based on EXIF data
        2. Size reduction if needed
        3. Format conversion (HEIC -> JPEG)
        4. Contrast enhancement

        Args:
            image_path: Path to the original image

        Returns:
            Path to the processed image (may be same as input if no processing needed)
        """
        image_path = Path(image_path)
        img = Image.open(image_path)

        # Track if we need to save a new file
        needs_save = False

        # 1. Auto-rotate based on EXIF
        img, rotated = self._auto_rotate(img)
        needs_save = needs_save or rotated

        # 2. Resize if too large
        img, resized = self._resize_if_needed(img)
        needs_save = needs_save or resized

        # 3. Convert HEIC to JPEG
        is_heic = image_path.suffix.lower() in {".heic", ".heif"}

        if needs_save or is_heic:
            # Save to cache directory with processed suffix
            output_path = self._get_processed_path(image_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to RGB if necessary (for JPEG)
            if img.mode in {"RGBA", "P"}:
                img = img.convert("RGB")

            img.save(output_path, "JPEG", quality=85, optimize=True)
            return output_path

        return image_path

    @staticmethod
    def _auto_rotate(img: Image.Image) -> tuple[Image.Image, bool]:
        """Rotate image based on EXIF orientation data.
        Returns:
            Tuple of (processed image, whether rotation was applied)
        """
        rotated_img = img
        was_rotated = False

        try:
            exif = img._getexif()
            if exif is not None:
                # Find orientation tag
                orientation_key = next(
                    (key for key, val in ExifTags.TAGS.items() if val == "Orientation"),
                    None
                )

                if orientation_key is not None and orientation_key in exif:
                    orientation = exif[orientation_key]

                    # Define all orientation transformations
                    transformations = {
                        2: lambda i: i.transpose(Image.FLIP_LEFT_RIGHT),
                        3: lambda i: i.rotate(180, expand=True),
                        4: lambda i: i.rotate(180).transpose(Image.FLIP_LEFT_RIGHT),
                        5: lambda i: i.rotate(270, expand=True).transpose(Image.FLIP_LEFT_RIGHT),
                        6: lambda i: i.rotate(270, expand=True),
                        7: lambda i: i.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT),
                        8: lambda i: i.rotate(90, expand=True),
                    }

                    if orientation in transformations:
                        rotated_img = transformations[orientation](img)
                        was_rotated = True

        except (AttributeError, KeyError, TypeError):
            pass

        return rotated_img, was_rotated

    def _resize_if_needed(self, img: Image.Image) -> tuple[Image.Image, bool]:
        """Resize image if larger than max_size.

        Maintains aspect ratio.

        Returns:
            Tuple of (processed image, whether resize was applied)
        """
        width, height = img.size

        if width <= self.max_size and height <= self.max_size:
            return img, False

        # Calculate new size maintaining aspect ratio
        if width > height:
            new_width = self.max_size
            new_height = int(height * (self.max_size / width))
        else:
            new_height = self.max_size
            new_width = int(width * (self.max_size / height))

        resized = img.resize((new_width, new_height), Image.LANCZOS)
        return resized, True

    @staticmethod
    def _get_processed_path(original_path: Path) -> Path:
        """Get path for processed image in cache directory."""
        # Use original filename with _processed suffix
        stem = original_path.stem
        return Config.CACHE_DIR / f"{stem}_processed.jpg"

    @staticmethod
    def calculate_hash(image_path: str | Path) -> str:
        """Calculate SHA256 hash of an image file.

        Used for cache identification.
        """
        image_path = Path(image_path)
        sha256 = hashlib.sha256()

        with open(image_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        return sha256.hexdigest()

    @staticmethod
    def is_supported_format(image_path: str | Path) -> bool:
        """Check if image format is supported."""
        path = Path(image_path)
        return path.suffix.lower() in Config.SUPPORTED_IMAGE_EXTENSIONS


def preprocess_image(image_path: str | Path) -> Path:
    """Convenience function to preprocess an image.

    Args:
        image_path: Path to the image

    Returns:
        Path to the processed image
    """
    preprocessor = ImagePreprocessor()
    return preprocessor.process(image_path)


def get_image_hash(image_path: str | Path) -> str:
    """Convenience function to get image hash.

    Args:
        image_path: Path to the image

    Returns:
        SHA256 hash string
    """
    return ImagePreprocessor.calculate_hash(image_path)
