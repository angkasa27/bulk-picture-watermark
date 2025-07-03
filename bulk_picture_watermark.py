import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import piexif
from datetime import datetime

# -----------------------------------
# Configuration
# -----------------------------------

CSV_FILE = "Inside view.csv"
INPUT_DIR = "input"
OUTPUT_DIR = "output_static"

# Which columns to use for watermark lines (zero-indexed)
WATERMARK_COLUMN_RANGE = (5, 8)  # e.g., columns 5 to 7 → STREET NAME, SPAN CGK, SPAN DMT

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"  # Update for Windows/Linux if needed

# -----------------------------------
# Helper Functions
# -----------------------------------

def to_deg(value, ref_positive, ref_negative):
    ref = ref_positive if value >= 0 else ref_negative
    abs_val = abs(value)
    d = int(abs_val)
    m = int((abs_val - d) * 60)
    s = int((abs_val - d - m / 60) * 3600 * 100)
    return ((d, 1), (m, 1), (s, 100)), ref

def draw_text_with_shadow(draw, position, text, font, shadow_offset=(2, 2)):
    x, y = position
    draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill="black")
    draw.text((x, y), text, font=font, fill="white")

def draw_watermark(img, lines, font):
    draw = ImageDraw.Draw(img)
    margin = 20
    line_height = font.getbbox("Hg")[3] + 10
    total_height = line_height * len(lines)
    x_base = img.width - margin
    y = img.height - total_height - margin - 64

    for line in lines:
        text_width = draw.textbbox((0, 0), line, font=font)[2]
        draw_text_with_shadow(draw, (x_base - text_width, y), line, font)
        y += line_height

def parse_lat_lon(longlat_str):
    try:
        lat, lon = map(float, longlat_str.replace("°", "").split())
        return lat, lon
    except:
        return None, None

def update_exif_metadata(exif_data, date_str, lat, lon):
    encoded_date = date_str.encode()
    exif_data["0th"][piexif.ImageIFD.DateTime] = encoded_date
    exif_data["Exif"][piexif.ExifIFD.DateTimeOriginal] = encoded_date
    exif_data["Exif"][piexif.ExifIFD.DateTimeDigitized] = encoded_date

    lat_data, lat_ref = to_deg(lat, b'N', b'S')
    lon_data, lon_ref = to_deg(lon, b'E', b'W')
    exif_data["GPS"] = {
        piexif.GPSIFD.GPSLatitudeRef: lat_ref,
        piexif.GPSIFD.GPSLatitude: lat_data,
        piexif.GPSIFD.GPSLongitudeRef: lon_ref,
        piexif.GPSIFD.GPSLongitude: lon_data,
    }

def add_watermark(image_path, output_path, watermark_lines, date_str, longlat_str):
    try:
        img = Image.open(image_path)
        exif_bytes = img.info.get("exif")
        exif_data = piexif.load(exif_bytes) if exif_bytes else {"0th": {}, "Exif": {}, "GPS": {}}

        lat, lon = parse_lat_lon(longlat_str)
        if lat is not None and lon is not None:
            update_exif_metadata(exif_data, date_str, lat, lon)

        font_size = max(16, int(img.height * 0.03))
        font = ImageFont.truetype(FONT_PATH, font_size)

        draw_watermark(img, watermark_lines, font)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, exif=piexif.dump(exif_data))
        print(f"✅ Watermarked: {output_path}")
    except Exception as e:
        print(f"❌ Error processing {image_path}: {e}")

# -----------------------------------
# Main Logic
# -----------------------------------

def process_images_csv():
    # Load CSV
    df = pd.read_csv(CSV_FILE)
    df = df.dropna(subset=["File Name", "LONGLAT"])  # Ensure required fields

    # Get sorted images
    image_files = sorted([
        f for f in os.listdir(INPUT_DIR)
        if f.lower().endswith((".jpg", ".jpeg"))
    ])

    if len(image_files) > len(df):
        print(f"❌ Error: {len(image_files)} images but only {len(df)} rows in CSV.")
        return

    # Process images matched to rows
    for idx, image_name in enumerate(image_files):
        row = df.iloc[idx]
        new_filename = str(row["File Name"]).strip() + ".jpg"
        longlat = str(row["LONGLAT"]).strip()

        # Handle missing or invalid datetime
        datetime_raw = row.get("Date & Time", None)
        if pd.isna(datetime_raw):
            now = datetime.now()
            exif_datetime = now.strftime("%Y:%m:%d %H:%M:%S")
            display_datetime = now.strftime("%d %b %Y %H:%M:%S")
        else:
            try:
                parsed_date = pd.to_datetime(datetime_raw)
                exif_datetime = parsed_date.strftime("%Y:%m:%d %H:%M:%S")
                display_datetime = parsed_date.strftime("%d %b %Y %H:%M:%S")
            except Exception:
                now = datetime.now()
                exif_datetime = now.strftime("%Y:%m:%d %H:%M:%S")
                display_datetime = now.strftime("%d %b %Y %H:%M:%S")

        # Get dynamic columns from range (e.g., 5 to 8)
        start, end = WATERMARK_COLUMN_RANGE
        col_range = df.columns[start:end]
        dynamic_lines = [str(row[col]).strip() for col in col_range if pd.notna(row[col])]

        watermark_lines = [display_datetime, longlat] + dynamic_lines

        input_path = os.path.join(INPUT_DIR, image_name)
        output_path = os.path.join(OUTPUT_DIR, new_filename)

        add_watermark(input_path, output_path, watermark_lines, exif_datetime, longlat)

# -----------------------------------
# Entry Point
# -----------------------------------

if __name__ == "__main__":
    process_images_csv()