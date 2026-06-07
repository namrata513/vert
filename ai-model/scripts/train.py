# ai-model/scripts/train.py

import os
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

# 1. Configuration Constants
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 10
TRAIN_DIR = '../dataset/processed/train'
VAL_DIR = '../dataset/processed/validation'
MODEL_OUTPUT_PATH = '../models/mobilenetv2_waste.h5'

# 2. Data Augmentation & Loading Pipelines
print("🔄 Preparing data generators with MobileNetV2 preprocessing...")
train_datagen = ImageDataGenerator(
    preprocessing_function=preprocess_input,
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    horizontal_flip=True,
    zoom_range=0.15
)

# Cleaned up: No duplicate rescaling line to corrupt validation images
val_datagen = ImageDataGenerator(
    preprocessing_function=preprocess_input
)

print("🔄 Loading dataset splits...")
train_generator = train_datagen.flow_from_directory(
    TRAIN_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical'
)

val_generator = val_datagen.flow_from_directory(
    VAL_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode='categorical'
)

# Extract the number of classes automatically (Should be 3)
num_classes = train_generator.num_classes
print("Class indices mapping:", train_generator.class_indices)

# 3. Construct the Transfer Learning Architecture
print("🏗️ Building MobileNetV2 network structure...")
base_model = MobileNetV2(input_shape=(224, 224, 3), include_top=False, weights='imagenet')

# Freeze the base model layers to protect existing ImageNet feature weights
base_model.trainable = False

# Create the custom classification head for Verte
model = tf.keras.Sequential([
    base_model,
    tf.keras.layers.GlobalAveragePooling2D(),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.Dense(3, activation='softmax')
])

# 4. Compile the Model
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001), # Smooth learning rate
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

model.summary()

# 5. Train the Model Layer Head
print("🚀 Training the custom classification layers...")
history = model.fit(
    train_generator,
    epochs=EPOCHS,
    validation_data=val_generator,
    verbose=1
)

# 6. Export the Model Weights
os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)
model.save(MODEL_OUTPUT_PATH)
print(f"🎉 Model training complete! Saved to: {MODEL_OUTPUT_PATH}")