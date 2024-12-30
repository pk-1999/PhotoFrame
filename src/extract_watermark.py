from posixpath import splitext
from PIL import Image
import numpy as np


'''
Extract watermark from an image
    - requires the backgroud of watermark source image to be about 100% white
    - input_image_path: path to the input image
    - output_image_path: path to save the extracted watermark
    - threshold: threshold to identify the watermark (default 100 / 255)
'''

def extract_watermark(input_image_path, output_image_path, threshold = 100):
    # Open the input image
    image = Image.open(input_image_path).convert("RGBA")
    data = np.array(image)

    # Extract the RGB channels
    r, g, b, a = data.T

    # Define a threshold to identify the watermark
    watermark_area = (r < threshold) & (g < threshold) & (b < threshold)

    # Create a new image with white watermark and transparent background
    new_data = np.zeros_like(data)
    new_data[..., :3] = 255  # Set all pixels to white
    new_data[..., 3] = 0  # Set all pixels to transparent
    new_data[watermark_area.T] = [255, 255, 255, 255]  # Set watermark area to white and opaque

    # Save the new image
    new_image = Image.fromarray(new_data)
    new_image.save(output_image_path, "PNG")

input_image_path = input("Input file name (including extension, support .png, .jpg, .jpeg): ")
output_image_path = splitext(input_image_path)[0] + "_watermark.png"
extract_watermark(input_image_path, output_image_path)