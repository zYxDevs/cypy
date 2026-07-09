import os
import cv2
import time
import json
import re
import fitz
import zipfile
import shutil
import concurrent.futures
import threading
import uuid
import numpy as np
try:
    import rarfile
except ImportError:
    rarfile = None
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from cypy.core.yolo_onnx import YOLOONNX as YOLO

import cypy.core.config as config
from cypy.core.utils import (
    bersihkan_json_dari_gemini,
    buang_kotak_raksasa_palsu,
    gabung_kotak_tumpang_tindih, buang_kotak_ngawur, buang_kotak_sfx_dan_gambar,
    buat_crop_lega_tapi_tidak_nyamber, mask_luar_box_utama, tulis_teks_di_balon
)


def _get_lang_code(target_language):
    """Get language code from target language name."""
    return config.LANG_CODES.get(target_language.lower(), target_language[:2].lower() if target_language else "tr")


def _make_output_path(input_path, target_language, output_ext=".png"):
    """Generate output path with language-code subfolder.
    
    Example: manga/page1.png -> manga/ID/page1.png
    """
    lang_code = _get_lang_code(target_language)
    lang_code_upper = lang_code.upper()
    
    dir_name = os.path.dirname(input_path)
    base_name = os.path.basename(input_path)
    name_without_ext = os.path.splitext(base_name)[0]
    
    output_dir = os.path.join(dir_name, lang_code_upper)
    os.makedirs(output_dir, exist_ok=True)
    
    return os.path.join(output_dir, f"{name_without_ext}{output_ext}")


yolo_lock = threading.Lock()

def translate_mosaic(mosaic_image_pil, provider, target_language="Indonesian", max_retry=3):
    """Sends a single mosaic image to the LLM provider for translation."""
    for attempt in range(max_retry):
        try:
            if not provider.validate_api_key():
                print(f"\n[!] API key for {provider.provider_name} is missing or empty!")
                return {}

            examples = {
                "english": ("Hello!", "Mother... wait..."),
                "indonesian": ("Cepat bangun!", "Ibu... tunggu..."),
                "japanese": ("早く起きて！", "お母さん…待って…"),
                "mandarin": ("快点起床！", "妈妈……等等……"),
                "spanish": ("¡Despierta rápido!", "Madre... espera..."),
                "portuguese": ("Acorde rápido!", "Mãe... espere..."),
                "javanese": ("Ndang tangi!", "Ibu... enteni..."),
            }
            lang_key = target_language.lower()
            example_val_1, example_val_3 = examples.get(lang_key, (examples["english"][0], examples["english"][1]))

            prompt = (
                f"You are an accurate, literal manga translator from its original language to {target_language}. "
                "The image contains several speech bubbles arranged vertically. "
                "Each bubble is prefixed with a LARGE RED NUMBER on its left as its ID. \n\n"

                "MAIN TASK:\n"
                f"Read the text in each bubble, then translate it into {target_language}, faithfully preserving the original meaning. \n\n"

                "VERTICAL READING RULES:\n"
                "1. Read vertical text from top to bottom. \n"
                "2. If there are multiple vertical columns, read the rightmost column first, then move left. \n"
                "3. Do not reverse column orders. \n"
                "4. Do not mix text between bubbles. \n\n"

                "TRANSLATION RULES:\n"
                "1. Translate literally and accurately. Do not make it overly polite, do not summarize, and do not invent content. \n"
                "2. Do not add subjects or objects not present in the original text. \n"
                "3. Do not alter the relationships between characters. \n"
                "4. If the text is rude, explicit, teasing, degrading, bashful, or begging, maintain that exact tone. \n"
                f"5. If the text contains a question, the {target_language} output must also be a question. \n"
                "6. Do not create new sentences that sound unnatural if they are not in the original text. \n"
                "7. For long sentences, keep all parts of the meaning. Do not truncate. \n"
                "8. If unsure about some text, use [?] for that part. \n"
                "9. If the bubble only contains SFX, scribbles, is empty, or is background art and not a meaningful dialogue, reply with 'SKIP'. \n\n"

                "HONORIFICS RULE:\n"
                "1. If the original text contains Japanese honorifics (san, kun, chan, sama, senpai, sensei, etc.), "
                "keep them as-is in the translation. Do NOT translate honorifics. \n"
                "2. Examples: -san stays as -san, -kun stays as -kun, -chan stays as -chan. \n"
                "3. This applies even when translating to non-Japanese languages. \n\n"

                "SFX RULE:\n"
                "1. If a bubble contains ONLY sound effects (SFX) with no dialogue, reply with 'SKIP'. \n"
                "2. SFX examples: ドドド, ゴゴゴ, バキ, ギュウ, キラキラ, etc. \n"
                "3. If a bubble has BOTH dialogue and SFX, translate only the dialogue part. \n\n"

                "RETURN ALL IDs RULE:\n"
                "1. You MUST return a JSON entry for EVERY red ID number visible in the image. \n"
                "2. Do NOT skip any ID numbers. If ID 1, 2, 3, 4, 5 are visible, your JSON must contain all 5 keys. \n"
                "3. For IDs you cannot read or translate, use 'SKIP' as the value. \n"
                "4. This is critical - missing IDs will cause errors. \n\n"

                "OUTPUT FORMAT:\n"
                "Provide the response ONLY in valid JSON without markdown formatting. \n"
                "Keys must be the red ID numbers as strings. \n"
                f"Values must be the {target_language} translation or 'SKIP'. \n"
                f'Example output: {{"1": "{example_val_1}", "2": "SKIP", "3": "{example_val_3}", "4": "SKIP", "5": "{example_val_1}"}}'
            )

            response_text = provider.translate_image(mosaic_image_pil, prompt)

            text_json = bersihkan_json_dari_gemini(response_text)
            result = json.loads(text_json)

            return result

        except ValueError as ve:
            if str(ve) == "API_KEY_ERROR":
                print(f"\n[!] API key for {provider.provider_name} is expired or invalid.")
                return {}
            raise ve
        except Exception as e:
            err_str = str(e).lower()
            if "api key expired" in err_str or "api_key_invalid" in err_str or "api key" in err_str or "api_key" in err_str:
                print(f"\n[!] API key for {provider.provider_name} is expired or invalid.")
                return {}
                
            if "429" in err_str or "too many requests" in err_str or "rate limit" in err_str:
                wait_time = 5 * (2 ** attempt)
                print(f"\n[!] Rate limit hit for {provider.provider_name}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue

            print(f"\n[!] {provider.provider_name} error (Attempt {attempt + 1}/{max_retry}).")

            if attempt < max_retry - 1:
                time.sleep(10)
            else:
                print(f"  [!] Failed to connect to {provider.provider_name}.")
                return {}


def shrink_crop_list_if_mosaic_too_tall(
    crop_list,
    max_mosaic_height=6000,
    crop_spacing=10,
    padding_top_bottom=20
):
    """
    Shrinks panels before constructing the mosaic if it exceeds the max height limit.
    Red IDs are drawn post-resize so they remain perfectly clear.
    """
    if not crop_list:
        return crop_list

    crop_count = len(crop_list)
    total_image_height = sum(p.height for _, p in crop_list)
    total_space_height = crop_count * crop_spacing + padding_top_bottom
    initial_mosaic_height = total_image_height + total_space_height

    if initial_mosaic_height <= max_mosaic_height:
        return crop_list

    target_image_height = max(1, max_mosaic_height - total_space_height)
    ratio = target_image_height / float(total_image_height)

    new_list = []

    for num, crop in crop_list:
        new_width = max(1, int(crop.width * ratio))
        new_height = max(1, int(crop.height * ratio))

        new_crop = crop.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS
        )

        new_list.append((num, new_crop))

    return new_list



def process_single_image(image_path, yolo_model, provider, target_language="Indonesian"):
    """Processes a single manga page. Splits landscape images into two pages automatically."""
    img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        print("[!] Image file is corrupt or unreadable.")
        return None
        
    img_height, img_width = img.shape[:2]
    
    ratio = img_width / img_height
    
    # Auto-Split Landscape (two or more pages)
    if ratio > 1.2:
        # Determine how many pages.
        # Standard manga page aspect ratio is usually around 0.7 to 0.75
        num_splits = max(2, round(ratio / 0.71))
        
        print(f"  [Auto-Split] Wide image detected (ratio {ratio:.2f}). Splitting into {num_splits} parts...")
        
        split_width = img_width // num_splits
        
        # Manga is usually read from right to left, so the rightmost part is Page 1.
        splits = []
        for i in range(num_splits):
            # Calculate from right to left
            x_end = img_width - (i * split_width)
            x_start = x_end - split_width
            if i == num_splits - 1: # Last split (leftmost) takes the remainder
                x_start = 0
                
            img_part = img[:, x_start:x_end]
            part_path = image_path.rsplit(".", 1)[0] + f"_split{i+1}.png"
            cv2.imwrite(part_path, img_part)
            
            print(f"  Translating Part {i+1} (Right-to-Left)...")
            res_path = _process_single_image_core(part_path, yolo_model, provider, target_language)
            splits.append((res_path, part_path))
            
        # Recombine
        valid_res = [res for res, _ in splits if res]
        if len(valid_res) == num_splits:
            # Load all result images
            img_results = [cv2.imdecode(np.fromfile(res, dtype=np.uint8), cv2.IMREAD_COLOR) for res in valid_res]
            
            # Order is right to left. Reverse visual order from left to right for hconcat.
            img_results.reverse()
            
            # Ensure heights are the same for merging.
            target_h = max(img.shape[0] for img in img_results)
            for i in range(len(img_results)):
                h, w = img_results[i].shape[:2]
                if h != target_h:
                    img_results[i] = cv2.resize(img_results[i], (int(w * target_h / h), target_h))
            
            combined = cv2.hconcat(img_results)
            
            output_path = _make_output_path(image_path, target_language)
            
            cv2.imwrite(output_path, combined)
            
            # Clean up split results
            for res_path, part_path in splits:
                try: os.remove(res_path)
                except: pass
                try: os.remove(part_path)
                except: pass
                
            return output_path
            
    # If not a landscape image, process as usual
    return _process_single_image_core(image_path, yolo_model, provider, target_language)

def _process_single_image_core(image_path, yolo_model, provider, target_language="Indonesian"):
    """Core processing function for a single manga page."""

    print(f"\nTranslating: {os.path.basename(image_path)}")

    img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)

    if img is None:
        print("[!] Image file is corrupt or unreadable.")
        return None

    main_image_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    main_draw = ImageDraw.Draw(main_image_pil)

    img_height, img_width = img.shape[:2]

    prediction_stages = [
        {"conf": 0.28, "iou": 0.45},
        {"conf": 0.18, "iou": 0.55},
        {"conf": 0.10, "iou": 0.65}
    ]

    raw_boxes = []

    for stage in prediction_stages:
        with yolo_lock:
            temp_results = yolo_model.predict(
                source=img,
                conf=stage["conf"],
                iou=stage["iou"],
                verbose=False
            )

        for box in temp_results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            raw_boxes.append([x1, y1, x2, y2])

    filtered_boxes = buang_kotak_raksasa_palsu(raw_boxes)
    filtered_boxes = gabung_kotak_tumpang_tindih(filtered_boxes)
    filtered_boxes = buang_kotak_ngawur(filtered_boxes, img_width, img_height)
    filtered_boxes = buang_kotak_sfx_dan_gambar(
        img=img,
        boxes=filtered_boxes,
        image_name=image_path
    )

    crop_list = []
    coordinate_map = {}

    for order, (x1, y1, x2, y2) in enumerate(filtered_boxes, start=1):
        box_w = max(1, x2 - x1)
        box_h = max(1, y2 - y1)

        pad_x = max(config.MIN_PAD, int(box_w * config.PAD_X_RATIO))
        pad_y = max(config.MIN_PAD, int(box_h * config.PAD_Y_RATIO))

        crop_x1, crop_y1, crop_x2, crop_y2 = buat_crop_lega_tapi_tidak_nyamber(
            [x1, y1, x2, y2],
            filtered_boxes,
            img_width,
            img_height,
            pad_x,
            pad_y
        )

        crop = img[crop_y1:crop_y2, crop_x1:crop_x2].copy()

        if crop.size == 0:
            continue

        crop = mask_luar_box_utama(
            crop,
            crop_x1,
            crop_y1,
            x1,
            y1,
            x2,
            y2
        )

        crop_pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))

        if config.SKALA_POTONGAN_MOSAIK != 1:
            new_size = (
                max(1, int(crop_pil.width * config.SKALA_POTONGAN_MOSAIK)),
                max(1, int(crop_pil.height * config.SKALA_POTONGAN_MOSAIK))
            )

            crop_pil = crop_pil.resize(
                new_size,
                Image.Resampling.LANCZOS
            )

        crop_list.append((str(order), crop_pil))
        coordinate_map[str(order)] = (x1, y1, x2, y2)

    total_bubbles = len(crop_list)

    if total_bubbles == 0:
        print("  No text bubbles found.")

        output_path = _make_output_path(image_path, target_language)
        main_image_pil.save(output_path)

        return output_path

    print(f"  Found {total_bubbles} speech bubbles...")

    left_number_margin = config.MARGIN_KIRI_NOMOR
    right_margin = config.MARGIN_KANAN
    crop_spacing = config.JARAK_ANTAR_POTONGAN

    crop_list = shrink_crop_list_if_mosaic_too_tall(
        crop_list,
        max_mosaic_height=config.MAX_TINGGI_MOSAIK,
        crop_spacing=crop_spacing,
        padding_top_bottom=20
    )

    mosaic_width = max(
        config.LEBAR_MOSAIK_MIN,
        max([p.width for _, p in crop_list]) + left_number_margin + right_margin
    )

    mosaic_height = (
        sum([p.height for _, p in crop_list])
        + (total_bubbles * crop_spacing)
        + 20
    )

    mosaic_canvas = Image.new(
        "RGB",
        (mosaic_width, mosaic_height),
        color=(255, 255, 255)
    )

    mosaic_draw = ImageDraw.Draw(mosaic_canvas)

    y_offset = 10

    number_font = ImageFont.load_default()

    try:
        number_font = ImageFont.truetype(config.FONT_MANGA, 40)
    except Exception:
        pass

    for num, crop in crop_list:
        mosaic_draw.text(
            (5, y_offset + (crop.height // 2) - 20),
            num,
            fill=(255, 0, 0),
            font=number_font
        )

        mosaic_canvas.paste(crop, (left_number_margin, y_offset))

        y_offset += crop.height + crop_spacing

    temp_mosaic_dir = os.path.join(config.DATA_DIR, "cypy_cache")
    os.makedirs(temp_mosaic_dir, exist_ok=True)

    mosaic_path = os.path.join(
        temp_mosaic_dir,
        f"mosaic_preview_{os.path.basename(image_path)}"
    )

    mosaic_canvas.save(mosaic_path)

    print(f"  Translating with {provider.provider_name} ({provider.model_name})...")

    translation_result = translate_mosaic(mosaic_canvas, provider=provider, target_language=target_language)

    if not translation_result:
        print("  [!] Translation failed.")
        return None

    if config.MANUAL_TRANSLATION_OVERRIDE:
        translation_result.update(config.MANUAL_TRANSLATION_OVERRIDE)

    for num, text in translation_result.items():
        if num in coordinate_map:
            if text.upper() != "SKIP" and text.strip() != "":
                x1, y1, x2, y2 = coordinate_map[num]

                w = max(1, x2 - x1)
                h = max(1, y2 - y1)
                ratio = w / float(h)
                area_ratio = (w * h) / float(max(1, img_width * img_height))

                if ratio >= 3.2 and w >= img_width * 0.35:
                    continue

                if area_ratio >= 0.035 and ratio >= 2.8:
                    continue

                suspicious_flat_box = (
                    ratio >= config.RASIO_BOX_GEPENG
                    and w >= img_width * config.LEBAR_BOX_GEPENG_RATIO
                    and h <= img_height * config.TINGGI_BOX_GEPENG_RATIO
                )

                if config.PAKAI_PATCH_UNTUK_BOX_GEPENG and suspicious_flat_box:
                    tulis_teks_di_balon(
                        main_draw,
                        text,
                        x1,
                        y1,
                        x2,
                        y2,
                        background_patch=True,
                        target_language=target_language
                    )

                else:
                    margin_x = int((x2 - x1) * config.MASK_MARGIN_RATIO)
                    margin_y = int((y2 - y1) * config.MASK_MARGIN_RATIO)

                    overlay = Image.new(
                        "RGBA",
                        main_image_pil.size,
                        (255, 255, 255, 0)
                    )

                    draw_overlay = ImageDraw.Draw(overlay)

                    draw_overlay.ellipse(
                        [
                            x1 + margin_x,
                            y1 + margin_y,
                            x2 - margin_x,
                            y2 - margin_y
                        ],
                        fill=(255, 255, 255, 255)
                    )

                    overlay_blurred = overlay.filter(ImageFilter.GaussianBlur(radius=8))

                    main_image_pil.paste(overlay_blurred, (0, 0), overlay_blurred)

                    tulis_teks_di_balon(
                        main_draw,
                        text,
                        x1,
                        y1,
                        x2,
                        y2,
                        background_patch=False,
                        target_language=target_language
                    )

    output_path = _make_output_path(image_path, target_language)

    main_image_pil.save(output_path)

    return output_path


def process_folder(folder_path, yolo_model, provider, target_language="Indonesian"):
    """Processes all supported images in a folder in parallel."""
    supported = config.SUPPORTED_IMAGE_EXTENSIONS
    files = sorted([
        f for f in os.listdir(folder_path)
        if f.lower().endswith(supported)
    ])

    if not files:
        print(f"  [!] No supported image files found in: {folder_path}")
        return

    total = len(files)
    print(f"\n[Batch] Found {total} images in folder.")

    success = 0
    failed = 0
    failed_files = []
    
    def process_file(filename, idx):
        file_path = os.path.join(folder_path, filename)
        
        # Resume Check
        expected_output = _make_output_path(file_path, target_language)
        
        if os.path.exists(expected_output):
            print(f"\n[{idx}/{total}] Skipping {filename} (Already translated).")
            return True, filename

        print(f"\n[{idx}/{total}] Processing {filename}...")
        result = process_single_image(file_path, yolo_model, provider=provider, target_language=target_language)
        return bool(result), filename

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(process_file, f, idx): f for idx, f in enumerate(files, start=1)}
        for future in concurrent.futures.as_completed(futures):
            try:
                result, filename = future.result()
                if result:
                    success += 1
                else:
                    failed += 1
                    failed_files.append(filename)
            except Exception as e:
                failed += 1
                failed_files.append(f"{futures[future]} ({e})")

    print(f"\n[Batch] Completed! Success: {success}, Failed: {failed}, Total: {total}")
    
    if failed_files:
        print(f"\n[Batch] Failed files:")
        for f in failed_files:
            print(f"  - {f}")


def process_pdf(pdf_path, yolo_model, provider, target_language="Indonesian"):
    """Processes a PDF page-by-page concurrently, and binds them back together."""
    print(f"\nProcessing PDF: {os.path.basename(pdf_path)}")

    doc = fitz.open(pdf_path)

    temp_dir = os.path.join(config.DATA_DIR, "cypy_cache", f"pdf_temp_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_dir, exist_ok=True)

    translated_images_paths = [None] * len(doc)
    total_pages = len(doc)
    
    # Save all pages first
    print("Extracting PDF pages...")
    page_paths = []
    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=300)
        img_path = os.path.join(temp_dir, f"page_{page_num:04d}.png")
        pix.save(img_path)
        page_paths.append((page_num, img_path))
        
    def process_pdf_page(page_num, img_path):
        expected_output = _make_output_path(img_path, target_language)
        if os.path.exists(expected_output):
            print(f"\n[PDF {page_num + 1}/{total_pages}] Skipping (Already translated).")
            return page_num, expected_output, True
            
        print(f"\n[PDF {page_num + 1}/{total_pages}] Translating...")
        result_path = process_single_image(img_path, yolo_model, provider=provider, target_language=target_language)
        return page_num, result_path, bool(result_path)

    print("Translating pages...")
    success = 0
    failed = 0
    failed_pages = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(process_pdf_page, p_num, p_path): p_num for p_num, p_path in page_paths}
        for future in concurrent.futures.as_completed(futures):
            try:
                p_num, res_path, is_success = future.result()
                translated_images_paths[p_num] = res_path
                if is_success:
                    success += 1
                else:
                    failed += 1
                    failed_pages.append(f"Page {p_num + 1}")
            except Exception as e:
                failed += 1
                failed_pages.append(f"Page {futures[future] + 1} ({e})")

    valid_paths = [p for p in translated_images_paths if p]
    if valid_paths:
        print("Saving final PDF...")
        images = [Image.open(img).convert("RGB") for img in valid_paths]
        output_pdf_path = _make_output_path(pdf_path, target_language, output_ext=".pdf")
        images[0].save(output_pdf_path, save_all=True, append_images=images[1:])
        print(f"Done! Saved at: {output_pdf_path}")
    
    print(f"\n[PDF] Completed! Success: {success}, Failed: {failed}, Total: {total_pages}")
    
    if failed_pages:
        print(f"\n[PDF] Failed pages:")
        for p in failed_pages:
            print(f"  - {p}")

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def setup_rarfile():
    if rarfile is None:
        return False
    import shutil
    import platform
    if shutil.which('unrar') or shutil.which('unrar.exe'):
        return True
    
    os_name = platform.system()
    
    if os_name == "Windows":
        common_paths = [
            r"C:\Program Files\WinRAR\UnRAR.exe",
            r"C:\Program Files\WinRAR\WinRAR.exe",
            r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
            r"C:\Program Files (x86)\WinRAR\WinRAR.exe",
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
        ]
    elif os_name == "Darwin":
        common_paths = [
            "/usr/local/bin/unrar",
            "/opt/homebrew/bin/unrar"
        ]
    else:
        common_paths = [
            "/usr/bin/unrar",
            "/usr/local/bin/unrar"
        ]

    for p in common_paths:
        if os.path.exists(p):
            rarfile.UNRAR_TOOL = p
            return True
    return False

def process_archive(archive_path, yolo_model, provider, target_language="Indonesian"):
    """Processes CBZ/ZIP/CBR/RAR archives."""
    print(f"\nProcessing Archive: {os.path.basename(archive_path)}")
    
    is_rar = archive_path.lower().endswith(('.rar', '.cbr'))
    if is_rar and not setup_rarfile():
        print("\n[!] Error: 'rarfile' module is not installed or 'unrar' is missing.")
        print("Please ensure you have WinRAR or 7-Zip installed (or add unrar to PATH).")
        print("If you just ran the update, please RESTART cypy for the module to load.")
        return
        
    if is_rar:
        print("[Info] Archive detected. Output will be saved as .pdf")

    temp_dir = os.path.join(config.DATA_DIR, "cypy_cache", f"archive_temp_{uuid.uuid4().hex[:8]}")
    os.makedirs(temp_dir, exist_ok=True)
    
    print("Extracting archive...")
    try:
        if is_rar:
            with rarfile.RarFile(archive_path) as rf:
                rf.extractall(temp_dir)
        else:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extractall(temp_dir)
    except Exception as e:
        print(f"[!] Extraction failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return

    # Find all images recursively
    image_paths = []
    for root, _, files in os.walk(temp_dir):
        for f in files:
            if f.lower().endswith(config.SUPPORTED_IMAGE_EXTENSIONS):
                image_paths.append(os.path.join(root, f))
                
    def natural_page_key(path):
        return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", os.path.basename(path))]

    image_paths.sort(key=natural_page_key)
    total = len(image_paths)
    
    if total == 0:
        print("[!] No images found in archive.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return
        
    print(f"Found {total} images. Starting translation...")
    
    translated_paths = []
    failed_files = []
    success = 0
    failed = 0

    def process_arch_file(img_path, idx):
        expected_output = _make_output_path(img_path, target_language)
        if os.path.exists(expected_output):
            print(f"\n[{idx}/{total}] Skipping (Already translated).")
            return idx, expected_output, img_path, True
            
        print(f"\n[{idx}/{total}] Translating {os.path.basename(img_path)}...")
        res = process_single_image(img_path, yolo_model, provider=provider, target_language=target_language)
        return idx, (res if res else img_path), img_path, bool(res)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(process_arch_file, p, i): (i, p) for i, p in enumerate(image_paths, start=1)}
        for future in concurrent.futures.as_completed(futures):
            try:
                idx, result, img_path, is_success = future.result()
                translated_paths.append((idx, result))
                if is_success:
                    success += 1
                else:
                    failed += 1
                    failed_files.append(os.path.basename(img_path))
            except Exception as e:
                idx, img_path = futures[future]
                translated_paths.append((idx, img_path))
                failed += 1
                failed_files.append(f"{os.path.basename(img_path)} ({e})")
            
    # Repack into PDF
    valid_paths = [p for _, p in sorted(translated_paths) if p and os.path.exists(p)]
    if valid_paths:
        output_pdf_path = _make_output_path(archive_path, target_language, output_ext=".pdf")
        print(f"\nCombining translated images into PDF...")
        images = [Image.open(img).convert("RGB") for img in valid_paths]
        images[0].save(output_pdf_path, save_all=True, append_images=images[1:])
        print(f"Done! Saved at: {output_pdf_path}")
    
    print(f"\n[Archive] Completed! Success: {success}, Failed: {failed}, Total: {total}")
    
    if failed_files:
        print(f"\n[Archive] Failed files:")
        for f in failed_files:
            print(f"  - {f}")
                
    shutil.rmtree(temp_dir, ignore_errors=True)
