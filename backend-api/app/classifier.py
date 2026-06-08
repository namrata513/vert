import tensorflow as tf
import numpy as np
from PIL import Image

class VerteClassifier:
    def __init__(self, model_path):
        print(f"🧠 Loading AI Model weights from: {model_path}...")
        # Load the model layout safely without compilation snags
        self.model = tf.keras.models.load_model(model_path, compile=False)
        
        # ⚠️ NOTE: Make sure this list order perfectly matches the classes
        # your model was trained on (e.g., check if index 0 is compostable)
        self.labels = ["compostable", "landfill", "recyclable"] 

    def predict(self, image_bytes):
        try:
            # 1. Open the image file bytes with Pillow
            img = Image.open(image_bytes)
            
            # 2. Force conversion to RGB mode (strips alpha channel layers from PNGs)
            if img.mode != "RGB":
                img = img.convert("RGB")
                
            # 3. Downscale or upscale the photo to match MobileNet's 224x224 grid dimension
            img = img.resize((224, 224))
            
            # 4. Turn the visual pixels into a raw mathematical float array
            img_array = tf.keras.preprocessing.image.img_to_array(img)
            
            # 5. Normalize pixel layers (Squash 0-255 numbers to a clear 0.0 - 1.0 range)
            img_array = img_array / 255.0
            
            # 6. Expand the array dimensions to mimic a multi-image batch structure [1, 224, 224, 3]
            img_array = np.expand_dims(img_array, axis=0)
            
            # 7. Feed the prepared array matrix to the deep learning model layers
            predictions = self.model.predict(img_array)
            predicted_class_idx = np.argmax(predictions[0])
            
            # Extract the correct string label mapping index
            final_category = self.labels[predicted_class_idx]
            
            print(f"🎯 AI Inference Complete. Class Index: {predicted_class_idx} -> Label: {final_category}")
            
            return {
                "category": final_category,
                "raw_material": "unknown",
                "confidence": float(predictions[0][predicted_class_idx])
            }
            
        except Exception as e:
            raise RuntimeError(f"Matrix preprocessing crash: {str(e)}")