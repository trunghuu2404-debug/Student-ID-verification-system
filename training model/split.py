# import os
# import random
# import shutil
# from pathlib import Path

# # Paths
# base_path = Path("data")
# images_train_path = base_path / "images/train"
# labels_train_path = base_path / "labels/train"
# images_val_path = base_path / "images/val"
# labels_val_path = base_path / "labels/val"

# # Create val folders if they don't exist
# images_val_path.mkdir(parents=True, exist_ok=True)
# labels_val_path.mkdir(parents=True, exist_ok=True)

# # Get all image files
# image_files = list(images_train_path.glob("*.jpg"))
# random.shuffle(image_files)

# # Split 20% for validation
# val_count = int(len(image_files) * 0.2)
# val_images = image_files[:val_count]

# # Move validation images and labels
# for img_path in val_images:
#     label_path = labels_train_path / (img_path.stem + ".txt")

#     shutil.move(str(img_path), images_val_path / img_path.name)
#     if label_path.exists():
#         shutil.move(str(label_path), labels_val_path / label_path.name)

# print(f"Moved {val_count} images to validation set.")
