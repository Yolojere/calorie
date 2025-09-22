# Memory-Optimized Nutrition Label Scanner
# Optimized for 512MB Render.com memory limit

import easyocr
import cv2
import numpy as np
import re
import json
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import io
import base64
import logging
import time
import os
import gc
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple

# Configure minimal logging for production
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Global EasyOCR reader instance (shared across requests)
_global_reader = None

def get_global_reader():
    """Get or create global EasyOCR reader instance"""
    global _global_reader
    if _global_reader is None:
        print("🚀 Initializing global EasyOCR reader...")
        _global_reader = easyocr.Reader(['en'], gpu=False)
        print("✅ Global EasyOCR reader initialized")
    return _global_reader

@dataclass
class NutritionValue:
    """Lightweight nutrition value container"""
    field_type: str
    value: float
    unit: str
    confidence: float
    source_text: str
    x_pos: float
    y_pos: float
    is_claimed: bool = False
    column_type: str = 'unknown'

class MemoryOptimizedScanner:
    """
    MEMORY-OPTIMIZED v20.0 - Designed for 512MB memory limit
    """

    def __init__(self, debug=False):
        self.debug = debug
        print("🚀 Initializing MEMORY-OPTIMIZED v20.0 Scanner...")
        
        # Use global reader instead of creating new instance
        self.easy_reader = get_global_reader()
        self.easyocr_available = True
        
        # Simplified field definitions
        self.nutrition_fields = {
            'calories': {
                'keywords': ['energia', 'energi', 'energy'],
                'expected_range': (50, 600),
                'priority': 1
            },
            'fats': {
                'keywords': ['rasva', 'rasvaa', 'fett', 'fat', 'rasvad'],
                'exclude_keywords': ['tyydytt', 'mättat', 'saturated'],
                'expected_range': (0, 100),
                'priority': 2
            },
            'saturated_fats': {
                'keywords': ['tyydytt', 'mättat', 'saturated'],
                'context_keywords': ['josta', 'varav', 'millest', 'of which'],
                'expected_range': (0, 50),
                'priority': 4
            },
            'carbs': {
                'keywords': ['hiilihydraat', 'kolhydrat', 'carb'],
                'expected_range': (0, 120),
                'priority': 3
            },
            'proteins': {
                'keywords': ['proteiini', 'protein'],
                'expected_range': (0, 85),
                'priority': 3
            },
            'sugars': {
                'keywords': ['sokeri', 'socker', 'sugar'],
                'context_keywords': ['josta', 'varav', 'millest', 'of which'],
                'expected_range': (0, 80),
                'priority': 6
            },
            'salt': {
                'keywords': ['suola', 'salt'],
                'expected_range': (0, 5),
                'priority': 7
            }
        }

    def preprocess_memory_efficient(self, image):
        """Memory-efficient preprocessing - SMALLER images"""
        if isinstance(image, str):
            if image.startswith('data:'):
                image = image.split(',')[1]
            image_bytes = base64.b64decode(image)
            pil_image = Image.open(io.BytesIO(image_bytes))
        else:
            pil_image = image.copy()

        # MEMORY OPTIMIZATION: Reduce image size instead of increasing it
        width, height = pil_image.size
        max_height = 800  # Reduced from 1300 to save memory
        max_width = 1200
        
        if height > max_height or width > max_width:
            # Calculate scale factor
            scale_factor = min(max_height / height, max_width / width)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)

        # Minimal enhancement to save memory
        enhancer = ImageEnhance.Contrast(pil_image)
        pil_image = enhancer.enhance(1.2)  # Reduced enhancement

        return pil_image

    def log_debug(self, message):
        if self.debug:
            print(f"🔍 {message}")

    def extract_text_memory_efficient(self, image_data):
        """Memory-efficient OCR extraction"""
        try:
            image = None
            if isinstance(image_data, str):
                if image_data.startswith('data:'):
                    image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
            elif isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_bytes))
            else:
                image = image_data

            if image is None:
                return []

            # Memory-efficient preprocessing
            preprocessed_image = self.preprocess_memory_efficient(image)
            image_array = np.array(preprocessed_image)
            
            # Clear original image from memory
            if hasattr(image, 'close'):
                image.close()
            del image
            
            # Clear preprocessed image
            preprocessed_image.close()
            del preprocessed_image
            
            try:
                ocr_results = self.easy_reader.readtext(image_array)
                
                # Clear image array immediately
                del image_array
                gc.collect()  # Force garbage collection
                
                # Process results with memory efficiency
                processed_results = []
                for bbox, text, confidence in ocr_results:
                    if confidence >= 0.4:  # Slightly higher threshold to reduce data
                        processed_results.append({
                            'text': text,
                            'confidence': confidence,
                            'x': bbox[0][0],
                            'y': bbox[0][1],
                        })

                # Clear original OCR results
                del ocr_results
                
                processed_results.sort(key=lambda x: (x['y'], x['x']))
                self.log_debug(f"Memory-efficient OCR extracted {len(processed_results)} items")
                return processed_results

            except Exception as e:
                self.log_debug(f"❌ EasyOCR failed: {e}")
                return []

        except Exception as e:
            self.log_debug(f"❌ OCR extraction error: {e}")
            return []
        finally:
            # Ensure cleanup
            gc.collect()

    def extract_numbers_efficient(self, text: str) -> List[Tuple[float, str]]:
        """Efficient number extraction with reduced complexity"""
        text = text.strip()
        found_numbers = []

        # Simplified patterns for memory efficiency
        patterns = [
            r'(\\d+),(\\d+)\\s*g\\b',       # Finnish decimal
            r'(\\d+)\\.(\\d+)\\s*g\\b',      # English decimal
            r'(\\d+(?:[.,]\\d+)?)\\s*kcal\\b', # Calories
            r'(\\d+(?:[.,]\\d+)?)\\s*g\\b',   # General grams
            r'\\b(\\d+(?:[.,]\\d+)?)(?=\\s|$)', # Standalone numbers
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match.groups()) >= 2 and ',' in match.group(0):
                        value = float(f"{match.group(1)}.{match.group(2)}")
                    else:
                        value = float(match.group(1).replace(',', '.'))
                    
                    if 'kcal' in match.group(0).lower():
                        found_numbers.append((value, 'kcal'))
                    else:
                        found_numbers.append((value, 'g'))
                except ValueError:
                    continue

        return found_numbers

    def find_nutrition_values_efficient(self, extracted_text) -> Dict[str, List[NutritionValue]]:
        """Memory-efficient value finding"""
        nutrition_values = {field: [] for field in self.nutrition_fields.keys()}
        
        self.log_debug(f"\\n🔥 MEMORY-EFFICIENT PARSING: Processing {len(extracted_text)} items")
        
        # Process items efficiently
        for i, item in enumerate(extracted_text):
            text_lower = item['text'].lower()
            
            if len(text_lower.strip()) < 2:
                continue
                
            for field_name, field_config in self.nutrition_fields.items():
                keywords = field_config['keywords']
                exclude_keywords = field_config.get('exclude_keywords', [])
                
                # Quick keyword check
                if not any(kw in text_lower for kw in keywords):
                    continue
                
                if any(ex_kw in text_lower for ex_kw in exclude_keywords):
                    continue
                
                # Look for numbers nearby
                search_candidates = []
                
                # Check same item first
                numbers_in_text = self.extract_numbers_efficient(item['text'])
                for value, unit in numbers_in_text:
                    if self._is_reasonable_value(field_name, value, unit):
                        search_candidates.append((value, unit, 0, item['confidence']))
                
                # Check nearby items if needed
                if not search_candidates:
                    for j, candidate_item in enumerate(extracted_text[max(0, i-3):min(len(extracted_text), i+4)]):
                        if abs(candidate_item['y'] - item['y']) <= 50:  # Nearby
                            numbers = self.extract_numbers_efficient(candidate_item['text'])
                            for value, unit in numbers:
                                if self._is_reasonable_value(field_name, value, unit):
                                    distance = abs(candidate_item['x'] - item['x'])
                                    search_candidates.append((value, unit, distance, candidate_item['confidence']))
                
                if search_candidates:
                    # Pick best candidate
                    search_candidates.sort(key=lambda x: (-x[3], x[2]))  # Best confidence, closest
                    value, unit, distance, confidence = search_candidates[0]
                    
                    nutrition_value = NutritionValue(
                        field_type=field_name,
                        value=value,
                        unit=unit,
                        confidence=confidence,
                        source_text=item['text'][:50],  # Truncate to save memory
                        x_pos=item['x'],
                        y_pos=item['y']
                    )
                    
                    nutrition_values[field_name].append(nutrition_value)
                    break  # Found value for this item, move on
        
        return nutrition_values

    def _is_reasonable_value(self, field_name, value, unit='g'):
        """Simplified value validation"""
        if field_name not in self.nutrition_fields:
            return False

        final_value = value
        if field_name == 'calories' and unit == 'kj':
            final_value = value / 4.184
        elif field_name == 'salt' and unit == 'mg':
            final_value = value / 1000

        min_val, max_val = self.nutrition_fields[field_name]['expected_range']
        return min_val <= final_value <= max_val or final_value == 0

    def select_best_values_efficient(self, nutrition_values: Dict[str, List[NutritionValue]]) -> Dict[str, NutritionValue]:
        """Memory-efficient value selection"""
        selected_values = {}
        
        field_priorities = [
            ('calories', 1), ('fats', 2), ('carbs', 3), ('proteins', 3),
            ('saturated_fats', 4), ('sugars', 6), ('salt', 7)
        ]
        
        for field_name, priority in field_priorities:
            if field_name not in nutrition_values or not nutrition_values[field_name]:
                continue
            
            # Simple selection: highest confidence
            available_values = nutrition_values[field_name]
            available_values.sort(key=lambda x: -x.confidence)
            best_value = available_values[0]
            
            selected_values[field_name] = best_value
        
        return selected_values

    def scan_nutrition_label(self, image_data):
        """MEMORY-OPTIMIZED main scanning function"""
        try:
            self.log_debug("🚀 Starting MEMORY-OPTIMIZED v20.0 Scanner...")

            # Input normalization
            img = None
            if isinstance(image_data, str):
                if os.path.exists(image_data):
                    img = Image.open(image_data)
                else:
                    try:
                        decoded = base64.b64decode(image_data)
                        img = Image.open(io.BytesIO(decoded))
                    except Exception as e:
                        raise ValueError(f"Invalid base64 string: {e}")
            elif isinstance(image_data, bytes):
                img = Image.open(io.BytesIO(image_data))
            elif hasattr(image_data, "read"):
                img = Image.open(image_data)

            if img is None:
                raise ValueError("Unsupported input type for image_data")

            # Memory-efficient OCR
            extracted_text = self.extract_text_memory_efficient(img)
            
            # Clear image from memory
            if hasattr(img, 'close'):
                img.close()
            del img

            if not extracted_text:
                return {'error': 'No text detected', 'success': False}

            # Memory-efficient parsing
            nutrition_values = self.find_nutrition_values_efficient(extracted_text)
            selected_values = self.select_best_values_efficient(nutrition_values)
            
            # Clear intermediate data
            del nutrition_values
            
            # Build final results
            validated_results = {}
            confidence_scores = {}
            
            for field_name, nutrition_value in selected_values.items():
                validated_results[field_name] = round(nutrition_value.value, 1)
                confidence_scores[field_name] = nutrition_value.confidence

            # Clear remaining data
            del selected_values
            gc.collect()  # Force cleanup

            # Check for per 100g
            full_text = ' '.join([item['text'] for item in extracted_text[:10]])  # Limit text checked
            is_per_100g = any(pattern in full_text.lower() 
                             for pattern in ['100g', '100 g', 'per 100'])

            response = {
                'success': True,
                'nutrition_data': validated_results,
                'per_100g': is_per_100g,
                'debug_info': {
                    'fields_found': list(validated_results.keys()),
                    'confidence_scores': confidence_scores,
                    'version': 'v20.0_memory_optimized'
                }
            }

            self.log_debug(f"\\n📊 MEMORY-OPTIMIZED RESULTS: {len(validated_results)} fields found")
            
            return response

        except Exception as e:
            self.log_debug(f"❌ Error: {e}")
            return {'error': str(e), 'success': False}
        finally:
            # Final cleanup
            gc.collect()

# Singleton pattern for global scanner instance
_global_scanner = None

def get_global_scanner():
    """Get or create global scanner instance"""
    global _global_scanner
    if _global_scanner is None:
        _global_scanner = MemoryOptimizedScanner(debug=False)
    return _global_scanner

# Example usage for Flask app
def scan_nutrition_label_api(image_data):
    """API endpoint function using global scanner"""
    scanner = get_global_scanner()
    return scanner.scan_nutrition_label(image_data)

print("✅ MEMORY-OPTIMIZED v20.0 ready with:")
print("   • Global EasyOCR reader instance (saves ~200-300MB per request)")
print("   • Reduced image preprocessing (800px max height vs 1300px)")
print("   • Explicit memory cleanup with gc.collect()")
print("   • Simplified data structures")
print("   • Optimized for 512MB Render.com limit")
print("   • Expected memory usage: ~200-300MB peak per request")
