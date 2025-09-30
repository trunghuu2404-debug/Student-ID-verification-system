# from ultralytics import YOLO
# import torch

# # Load a pretrained YOLO11n model
# model = YOLO("yolo11n.pt")


# # Train the model with early stopping and custom augmentation
# train_results = model.train(
#     data="config.yaml",  # Path to your dataset config
#     epochs=100,  # Max number of epochs
#     patience=10,  # Early stopping: stop after 10 epochs with no improvement
#     imgsz=640,  # Training image size
#     device=(
#         "cuda" if torch.cuda.is_available() else "cpu"
#     ),  # Change to "cuda" if using GPU
#     # Data augmentation parameters
#     degrees=10.0,  # Random rotation
#     translate=0.1,  # Random translation
#     scale=0.5,  # Random scaling
#     shear=2.0,  # Random shear
#     perspective=0.0005,  # Random perspective transform
#     flipud=0.0,  # Vertical flip probability
#     fliplr=0.5,  # Horizontal flip probability
#     mosaic=1.0,  # Enable mosaic augmentation
#     mixup=0.2,  # MixUp augmentation
# )
