import cv2
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor


# adjust brightness of frame image
def adjust_brightness(image, factor):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv = np.array(hsv, dtype=np.float64)
    hsv[:, :, 2] = hsv[:, :, 2] * factor
    hsv[:, :, 2][hsv[:, :, 2] > 255] = 255
    hsv = np.array(hsv, dtype=np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

# create rounded rectangle mask to display inlay image
def create_rounded_rectangle_mask(image, scale=0.04):
    mask = np.zeros_like(image, dtype=np.uint8)
    h, w = image.shape[:2]
    radius = int(min(h, w) * scale)
    cv2.rectangle(mask, (radius, radius), (w - radius, h - radius), (255, 255, 255), -1)
    cv2.rectangle(mask, (0, radius), (radius, h - radius), (255, 255, 255), -1)
    cv2.rectangle(mask, (w - radius, radius), (w, h - radius), (255, 255, 255), -1)
    cv2.rectangle(mask, (radius, 0), (w - radius, radius), (255, 255, 255), -1)
    cv2.rectangle(mask, (radius, h - radius), (w - radius, h), (255, 255, 255), -1)
    cv2.circle(mask, (radius, radius), radius, (255, 255, 255), -1)
    cv2.circle(mask, (w - radius, radius), radius, (255, 255, 255), -1)
    cv2.circle(mask, (radius, h - radius), radius, (255, 255, 255), -1)
    cv2.circle(mask, (w - radius, h - radius), radius, (255, 255, 255), -1)
    return mask

# add shadow to the out side of inlay image
def add_shadow(frame_image, image, mask):
    ksize = 301
    sigma = 1000
    extend_h, extend_w = frame_image.shape[:2]
    h, w = image.shape[:2]
    inlay_h = int(h * 1.05 - ksize)
    inlay_w = int(w * 1.05 - ksize)
    x_offset = int((extend_w - inlay_w) // 2)
    y_offset = int((extend_h - inlay_h) // 2)
    white = np.ones((extend_h, extend_w, 3), dtype=np.uint8) * 255
    black = np.zeros((inlay_h, inlay_w, 3), dtype=np.uint8)
    shadow = white.copy()
    shadow[y_offset:y_offset + inlay_h, x_offset:x_offset + inlay_w] = black
    shadow = cv2.GaussianBlur(shadow, (ksize, ksize), sigma)
    shadow = cv2.boxFilter(shadow, -1, (ksize, ksize))
    x_offset = int((extend_w - w) // 2)
    y_offset = int((extend_h - h) // 2)
    shadow[y_offset:y_offset + h, x_offset:x_offset + w] = np.maximum(
        shadow[y_offset:y_offset + h, x_offset:x_offset + w],
        mask
    )
    return shadow

# add watermark to the bottom of the frame image
def add_watermark(image, scale=0.1, transparency=0.75, extra_mark = ''):
    image_h, image_w, _ = image.shape
    side_length = int(min(image_h, image_w) * scale)
    if extra_mark:
        y_offset = image_h - side_length - 220
    else:
        y_offset = image_h - side_length - 80
    x_offset = (image_w - side_length) // 2
    background = np.average(image[y_offset:y_offset + side_length, x_offset:x_offset + side_length])
    watermark_filename = 'yu-LOGO-b.png' if background > 127 else 'yu-LOGO-w.png'
    watermark = cv2.imread(os.path.join('./src/watermark', watermark_filename), cv2.IMREAD_UNCHANGED)
    watermark = cv2.resize(watermark, (side_length, side_length))
    for c in range(0, 3):
        image[y_offset:y_offset + side_length, x_offset:x_offset + side_length, c] = \
            image[y_offset:y_offset + side_length, x_offset:x_offset + side_length, c] * (1 - transparency * (watermark[:, :, 3] / 255.0)) + \
            watermark[:, :, c] * (transparency * (watermark[:, :, 3] / 255.0))
    if extra_mark:
        extra_mark = cv2.imread(os.path.join('./src/watermark', extra_mark), cv2.IMREAD_UNCHANGED)
        h,w = extra_mark.shape[:2]
        mark_w = int(w * side_length / h)
        mark_h = side_length
        extra_mark = cv2.resize(extra_mark, (mark_w, mark_h))
        x_offset = (image_w - mark_w) // 2
        y_offset = image_h - mark_h - 60
        for c in range(0, 3):
            image[y_offset:y_offset + mark_h, x_offset:x_offset + mark_w, c] = \
                image[y_offset:y_offset + mark_h, x_offset:x_offset + mark_w, c] * (1 - transparency * 0.8 * (extra_mark[:, :, 3] / 255.0)) + \
                extra_mark[:, :, c] * (transparency * 0.8 * (extra_mark[:, :, 3] / 255.0))
    return image

# main function to process image
def process_image(filename, input_folder, output_folder, output_ratio=9/16, resize_bool=False, resize_height=1920):
    image_path = os.path.join(input_folder, filename)
    image = cv2.imread(image_path)
    h, w, _ = image.shape
    # polish inlay image display scale
    if w/h >1 and output_ratio > 1:
        display_scale = 0.8
    elif w/h < 1 and output_ratio < 1:
        display_scale = 0.8
    else:
        display_scale = 0.85
    # frame pixels and inlay pixels
    if w / h > output_ratio:
        new_w = w
        new_h = int(w / output_ratio)
        clip_w = int(h * output_ratio)
        clip_h = h
    else:
        new_w = int(h * output_ratio)
        new_h = h
        clip_w = w
        clip_h = int(w / output_ratio)
    x_start = (w - clip_w) // 2
    y_start = (h - clip_h) // 2
    image_cropped = image[y_start:y_start + clip_h, x_start:x_start + clip_w]
    # blur
    ksize = 301
    sigma = 75
    blurred = cv2.GaussianBlur(image_cropped, (ksize, ksize), sigma)
    blurred = adjust_brightness(cv2.resize(blurred, (new_w, new_h)), 0.75)
    inlay_w = int(w * display_scale)
    inlay_h = int(h * display_scale)
    x_offset = (new_w - inlay_w) // 2
    y_offset = (new_h - inlay_h) // 2
    resized_image = cv2.resize(image, (inlay_w, inlay_h))
    mask = create_rounded_rectangle_mask(resized_image)
    blurred[y_offset:y_offset + inlay_h, x_offset:x_offset + inlay_w] = \
        blurred[y_offset:y_offset + inlay_h, x_offset:x_offset + inlay_w] * (1 - mask / 255) + \
        resized_image * (mask / 255)
    shadow = add_shadow(blurred, resized_image, mask)
    shadowed_image = blurred * (shadow / 255.0)

    if resize_bool:
        output_image = cv2.resize(shadowed_image, (int(resize_height * output_ratio), resize_height))
    else:
        output_image = shadowed_image
    blurred_watermark = add_watermark(output_image, extra_mark='2024.png')

    output_path = os.path.join(output_folder, 'framed_' + filename)
    cv2.imwrite(output_path, blurred_watermark, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

# process all images in the input folder with multi-threading
def process_images(input_folder, output_folder, output_ratio=9/16, resize_bool=False, resize_height=1920):
    with ThreadPoolExecutor() as executor:
        filenames = [f for f in os.listdir(input_folder) if f.endswith(('.jpg', '.jpeg', '.png'))]
        futures = [executor.submit(process_image, filename, input_folder, output_folder, output_ratio, resize_bool, resize_height) for filename in filenames]
        for future in futures:
            try:
                future.result()
            except Exception as e:
                print(f"Error processing file: {e}")

if __name__ == "__main__":
    input_folder = './input'    # input folder
    output_folder = './output'  # output folder
    output_ration = 9/16        # output ratio = width/height: 9/16, 2/3, 3/4, 1, 4/3, 3/2, 16/9...
    resize_bool = True          # resize image to same pixels? (if True, the distance of watermark to bottom in the output image can be fixed)
    resize_height = 3840        # resize height (only work when resize_bool is True): 1440, 1920, 2880, 3840...
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    process_images(input_folder, output_folder, output_ratio=float(output_ration), resize_bool=resize_bool, resize_height=resize_height)