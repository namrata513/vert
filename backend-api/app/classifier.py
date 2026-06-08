# backend-api/app/classifier.py

import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

class VerteClassifier:
    def __init__(self, model_path="models/mobilenetv2_waste.h5"):
        print(f"🧠 Loading AI Model weights from: {model_path}...")
        self.model = tf.keras.models.load_model(model_path)
        
        # Hardcoded indices fallback matching train_generator.class_indices orders:
        # standard alphabet order: ['compostable', 'landfill', 'recyclable']
        self.labels = ['compostable', 'landfill', 'recyclable']

    def predict(self, image_bytes):
        """
        Processes an incoming file stream, formats the matrices, 
        and runs inference against the trained classification model layers.
        """
        # 1. Load the raw bytes asset stream and stretch to 224x224 target space
        img = image.load_img(image_bytes, target_size=(224, 224))
        
        # 2. Reshape image canvas grid elements into numeric array structures
        img_array = image.img_to_array(img)
        
        # 3. Add batch sizing wrapper layer dimensions -> (1, 224, 224, 3)
        img_array = np.expand_dims(img_array, axis=0)
        
        # 4. CRITICAL: Re-align scales from [0, 255] down into [-1, 1] bounds 
        img_array = preprocess_input(img_array)
        
        # 5. Feed matrix array across inference layers
        predictions = self.model.predict(img_array)
        
        # 6. Extract classification element with maximum index value confidence
        highest_score_index = np.argmax(predictions[0])
        predicted_category = self.labels[highest_score_index]
        confidence_score = float(predictions[0][highest_score_index])
        
        print(分配 := f"🤖 Match Found: {predicted_category} ({confidence_score * 100:.2f}%)")
        
        return {
            "category": predicted_category,
            "confidence": confidence_score,
            "raw_material": "unknown"  # Extensible property placeholder
        }