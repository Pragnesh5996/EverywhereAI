from apps.common.constants import CreativeType
from SF import settings
from PIL import Image
import math
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata


class UploadCreativeHelper:
    """
    This class provides helper functions for uploading creative assets.
    It includes functions for checking the size and type of a creative, and finding the resolution of an image or video.
    """

    @staticmethod
    def check_size(size_bytes):
        """
        This function is convert image or video size to MB.
        The formula for Converting Bytes to Megabytes:-
        1 Byte = 1/1048576 MegaBytes = 0.000000954 MegaBytes
        """
        if size_bytes < 1024000:
            # Convert bytes to kilobytes
            return f"{round(size_bytes / 1024, 2)} kb"
        else:
            # Convert bytes to megabytes
            return f"{round(size_bytes / 1048576, 2)} mb"

    @staticmethod
    def check_video_or_image(creative):
        """
        This fuction is check creative is image or video.
        """
        video_file_extensions = ["mp3", "mp4", "mov", "gif"]
        image_file_extensions = ["jpg", "jpeg", "png", "webp"]
        creative = creative.split(".")[1]
        if creative in video_file_extensions:
            return CreativeType.VIDEO

        if creative in image_file_extensions:
            return CreativeType.IMAGE

        return False

    @staticmethod
    def find_creative_resolution(creative, creative_type, uploadsesid):
        """
        This function is responsible for finding the resolution of a creative,
        which can be either an image or a video. It takes in three parameters: the creative file,
        the type of creative (image or video), and the upload session ID.
        """
        if creative_type == CreativeType.IMAGE:
            try:
                img_url = f"{settings.BASE_DIR}/media/upload_creative/{creative}"
                img = Image.open(img_url)
                wid, hgt = img.size
                return str(wid) + "x" + str(hgt), wid, hgt, True, False

            except Exception:
                return (
                    None,
                    None,
                    None,
                    False,
                    f"The image file '{creative}' is corrupted",
                )

        if creative_type == CreativeType.VIDEO:
            try:
                # Create a parser for the video file
                video_path = f"{settings.BASE_DIR}/media/upload_creative/{creative}"
                parser = createParser(video_path)
                # Extract the metadata from the video file
                metadata = extractMetadata(parser)

                # Get the height and width of the video
                height = metadata.get("height")
                width = metadata.get("width")
                return (
                    f"{width}x{height}",
                    width,
                    height,
                    True,
                    False,
                )
            except Exception:
                return (
                    None,
                    None,
                    None,
                    False,
                    f"The video file '{creative}' is corrupted",
                )

    @staticmethod
    def calculate_ratio(resolution_x, resolution_y):
        ratio = resolution_x / resolution_y
        # round the ratio to 2 decimal places
        ratio = round(ratio, 2)
        # simplify the ratio to the lowest common denominator
        gcd = math.gcd(resolution_x, resolution_y)
        ratio_x = int(resolution_x / gcd)
        ratio_y = int(resolution_y / gcd)
        return f"{ratio_x}:{ratio_y}"
