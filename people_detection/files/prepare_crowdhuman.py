import json
import shutil
from pathlib import Path
from PIL import Image
from tqdm import tqdm

RAW_DIR = Path("./crowdhuman_raw")
OUT_DIR = Path("./crowdhuman_yolo")
IMAGES_DIR = RAW_DIR / "Images"

SPLITS = {
    "train": RAW_DIR / "annotation_train.odgt",
    "val": RAW_DIR / "annotation_val.odgt",
}


def convert_split(split_name, odgt_path):
    img_out = OUT_DIR / "images" / split_name
    lbl_out = OUT_DIR / "labels" / split_name
    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)

    with open(odgt_path, "r") as f:
        lines = f.readlines()

    skipped_missing_image = 0
    skipped_bad_box = 0
    total_boxes = 0

    for line in tqdm(lines, desc=f"Converting {split_name}"):
        record = json.loads(line)
        image_id = record["ID"]
        image_path = IMAGES_DIR / f"{image_id}.jpg"

        if not image_path.exists():
            skipped_missing_image += 1
            continue

        try:
            with Image.open(image_path) as im:
                img_w, img_h = im.size
        except Exception:
            skipped_missing_image += 1
            continue

        yolo_lines = []
        for box in record.get("gtboxes", []):
            if box.get("tag") != "person":
                continue
            if box.get("extra", {}).get("ignore", 0) == 1:
                continue

            x, y, w, h = box["fbox"]  
            x1 = max(0.0, x)
            y1 = max(0.0, y)
            x2 = min(float(img_w), x + w)
            y2 = min(float(img_h), y + h)

            if x2 <= x1 or y2 <= y1:
                skipped_bad_box += 1
                continue

            bw, bh = x2 - x1, y2 - y1
            xc, yc = x1 + bw / 2, y1 + bh / 2

            # YOLO format: class x_center y_center width height, normalized 0-1
            yolo_lines.append(
                f"0 {xc / img_w:.6f} {yc / img_h:.6f} {bw / img_w:.6f} {bh / img_h:.6f}"
            )
            total_boxes += 1

        (lbl_out / f"{image_id}.txt").write_text("\n".join(yolo_lines))

        dst = img_out / f"{image_id}.jpg"
        if not dst.exists():
            try:
                dst.symlink_to(image_path.resolve())
            except OSError:
                shutil.copy2(image_path, dst)

    print(f"{split_name}: {total_boxes} boxes written, "
          f"{skipped_missing_image} images missing, {skipped_bad_box} bad boxes skipped")


if __name__ == "__main__":
    for split_name, odgt_path in SPLITS.items():
        if not odgt_path.exists():
            print(f"Skipping {split_name} - {odgt_path} not found. "
                  f"See README_finetune.md for how to download it.")
            continue
        convert_split(split_name, odgt_path)

    print(f"\nDone. YOLO-format dataset at: {OUT_DIR.resolve()}")
