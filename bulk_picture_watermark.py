import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import piexif
from datetime import datetime
from random import randint

# -----------------------------------
# Configuration
# -----------------------------------

CSV_FILE = "Street view.csv"
INPUT_DIR = "input"
OUTPUT_DIR = "output_static"

WATERMARK_COLUMN_RANGE = (5, 8)  # e.g., columns F to H
FOLDER_COLUMN_RANGE = (2, 4)     # e.g., columns C to D → output folders
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"  # Update if needed

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

def add_watermark(input_path, new_filename, output_folders, watermark_lines, exif_datetime, longlat_str):
    try:
        img = Image.open(input_path)
        exif_bytes = img.info.get("exif")
        exif_data = piexif.load(exif_bytes) if exif_bytes else {"0th": {}, "Exif": {}, "GPS": {}}
        lat, lon = parse_lat_lon(longlat_str)
        if lat is not None and lon is not None:
            update_exif_metadata(exif_data, exif_datetime, lat, lon)

        font_size = max(16, int(img.height * 0.03))
        font = ImageFont.truetype(FONT_PATH, font_size)
        draw_watermark(img, watermark_lines, font)

        for folder in output_folders:
            folder_path = os.path.join(OUTPUT_DIR, folder)
            os.makedirs(folder_path, exist_ok=True)
            output_path = os.path.join(folder_path, new_filename)
            img.save(output_path, exif=piexif.dump(exif_data))
            print(f"✅ Saved to: {output_path}")

    except Exception as e:
        print(f"❌ Error processing {input_path}: {e}")

# -----------------------------------
# Main Logic
# -----------------------------------

def process_images_csv():
    base_datetime = datetime.strptime("2025-07-01 08:00", "%Y-%m-%d %H:%M")
    current_datetime = base_datetime
    WORK_START = 8
    WORK_END = 16

    df = pd.read_csv(CSV_FILE)
    df = df.dropna(subset=["File Name", "Nama Foto", "LONGLAT"])

    for _, row in df.iterrows():
        nama_foto = str(int(float(row["Nama Foto"]))).strip()
        input_path = None

        # Search for .jpg or .jpeg
        for ext in [".jpg", ".jpeg"]:
            candidate = os.path.join(INPUT_DIR,  nama_foto + ext)
            if os.path.exists(candidate):
                input_path = candidate
                break

        if not input_path:
            print(f"⚠️ Skipping: '{nama_foto}' not found")
            continue

        new_filename = str(row["File Name"]).strip() + ".jpg"
        longlat = str(row["LONGLAT"]).strip()

        # Generate randomized datetime
        increment_minutes = randint(8, 36)
        increment_seconds = randint(0, 59)
        current_datetime += pd.Timedelta(minutes=increment_minutes, seconds=increment_seconds)

        if current_datetime.hour >= WORK_END:
            current_datetime = (current_datetime + pd.Timedelta(days=1)).replace(
                hour=WORK_START,
                minute=randint(0, 10),
                second=randint(0, 59),
                microsecond=0
            )

        exif_datetime = current_datetime.strftime("%Y:%m:%d %H:%M:%S")
        display_datetime = current_datetime.strftime("%d %b %Y %H:%M:%S")

        # Get watermark lines
        wm_start, wm_end = WATERMARK_COLUMN_RANGE
        col_range = df.columns[wm_start:wm_end]
        dynamic_lines = [str(row[col]).strip() for col in col_range if pd.notna(row[col])]
        watermark_lines = [display_datetime, longlat] + dynamic_lines

        # Output folder names
        folder_start, folder_end = FOLDER_COLUMN_RANGE
        folder_cols = df.columns[folder_start:folder_end]
        output_folders = [str(row[col]).strip() for col in folder_cols if pd.notna(row[col]) and str(row[col]).strip()]

        add_watermark(
            input_path=input_path,
            new_filename=new_filename,
            output_folders=output_folders,
            watermark_lines=watermark_lines,
            exif_datetime=exif_datetime,
            longlat_str=longlat
        )

# -----------------------------------
# Run Script
# -----------------------------------

if __name__ == "__main__":
    process_images_csv()