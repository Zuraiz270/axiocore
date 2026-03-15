import io
from PIL import Image

class ExifStripper:
    @staticmethod
    def strip_metadata(image_bytes: bytes) -> bytes:
        """
        Takes raw image bytes, removes all EXIF and GPS metadata,
        and returns the sanitized image bytes.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # To remove EXIF data, we rebuild the image data without passing the 'exif' kwarg.
                # However, Image.save() on certain formats might automatically persist some chunks.
                # Safe approach is to extract data into a new Image object entirely.
                data = list(img.getdata())
                image_without_exif = Image.new(img.mode, img.size)
                image_without_exif.putdata(data)
                
                output_io = io.BytesIO()
                # Default back to original format, or PNG if not determinable
                out_format = img.format if img.format else 'PNG'
                image_without_exif.save(output_io, format=out_format)
                
                return output_io.getvalue()
        except Exception as e:
            raise RuntimeError(f"Failed to strip EXIF data: {str(e)}")
