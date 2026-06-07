# ai-model/scripts/sort_dataset.py
import os
import shutil
from sklearn.model_selection import train_test_split

# Define paths
RAW_DIR = '../dataset'
PROCESSED_DIR = '../dataset/processed'

# Define our Verte mappings
MAPPING = {
    'cardboard': 'compostable',
    'glass': 'recyclable',
    'metal': 'recyclable',
    'paper': 'compostable',
    'plastic': 'recyclable',
    'trash': 'landfill'
}

for raw_class, verte_class in MAPPING.items():
    class_path = os.path.join(RAW_DIR, raw_class)
    if not os.path.exists(class_path):
        continue
        
    # Get all images for this class
    images = [f for f in os.listdir(class_path) if f.endswith(('.jpg', '.jpeg', '.png'))]
    
    # Split 80% for training, 20% for validation
    train_imgs, val_imgs = train_test_split(images, test_size=0.2, random_state=42)
    
    # Helper function to move files safely
    for img in train_imgs:
        dest = os.path.join(PROCESSED_DIR, 'train', verte_class)
        os.makedirs(dest, exist_ok=True)
        shutil.copy(os.path.join(class_path, img), os.path.join(dest, img))
        
    for img in val_imgs:
        dest = os.path.join(PROCESSED_DIR, 'validation', verte_class)
        os.makedirs(dest, exist_ok=True)
        shutil.copy(os.path.join(class_path, img), os.path.join(dest, img))

print("🌱 Dataset successfully split and structured for Verte!")