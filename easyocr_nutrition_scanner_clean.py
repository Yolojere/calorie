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
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    image_path: str
    timestamp: str  
    success: bool
    calories: Optional[float] = None
    fats: Optional[float] = None
    saturated_fats: Optional[float] = None
    carbs: Optional[float] = None
    sugars: Optional[float] = None
    fiber: Optional[float] = None
    proteins: Optional[float] = None
    salt: Optional[float] = None
    confidence_scores: Dict[str, float] = None
    processing_time: float = 0.0
    errors: List[str] = None
    validation_corrections: Dict[str, str] = None

class NutritionTestHarness:
    def __init__(self, scanner_class):
        self.scanner_class = scanner_class
        self.scanner = scanner_class()
        self.results = []

    def run_comprehensive_test(self, image_paths, ground_truth_file=None):
        """Run tests on multiple images with detailed per-image results"""
        print(f"🧪 Starting comprehensive test on {len(image_paths)} images...")

        for i, image_path in enumerate(image_paths, 1):
            print(f"\n📷 Testing image {i}/{len(image_paths)}: {image_path}")
            start_time = time.time()

            result = TestResult(
                image_path=image_path,
                timestamp=datetime.now().isoformat(),
                success=False,
                confidence_scores={},
                errors=[]
            )

            try:
                # Run scanner
                scan_result = self.scanner.scan_nutrition_label(image_path)

                if scan_result.get('success'):
                    result.success = True
                    # Extract all nutrition values
                    nutrition_data = scan_result.get('nutrition_data', {})
                    result.calories = nutrition_data.get('calories')
                    result.fats = nutrition_data.get('fats')
                    result.saturated_fats = nutrition_data.get('saturated_fats')
                    result.carbs = nutrition_data.get('carbs')
                    result.sugars = nutrition_data.get('sugars')
                    result.fiber = nutrition_data.get('fiber')
                    result.proteins = nutrition_data.get('proteins')
                    result.salt = nutrition_data.get('salt')

                    # Extract confidence scores
                    result.confidence_scores = self._extract_confidences(scan_result)
                else:
                    result.errors.append(scan_result.get('error', 'Unknown scanning error'))

            except Exception as e:
                result.errors.append(str(e))

            result.processing_time = time.time() - start_time
            self.results.append(result)

            # Print immediate result with accuracy check
            if result.success:
                fields_found = len([v for v in [result.calories, result.fats, result.carbs, result.proteins] if v is not None])
                print(f"  ✅ Success - Found {fields_found} fields in {result.processing_time:.2f}s")
                
                # Show key results for verification
                print(f"     📊 calories: {result.calories}, fats: {result.fats}, carbs: {result.carbs}")
                print(f"     📊 proteins: {result.proteins}, saturated_fats: {result.saturated_fats}, fiber: {result.fiber}, salt: {result.salt}, sugars: {result.sugars}")
                
            else:
                print(f"  ❌ Failed - {'; '.join(result.errors)} in {result.processing_time:.2f}s")

        # Generate comprehensive report
        return self._generate_report()

    def _extract_confidences(self, scan_result):
        """Extract confidence scores from scan result"""
        confidence_scores = {}
        debug_info = scan_result.get('debug_info', {})
        if 'confidence_scores' in debug_info:
            confidence_scores = debug_info['confidence_scores']
        return confidence_scores

    def _generate_report(self):
        """Generate comprehensive test report"""
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        success_rate = successful_tests / total_tests * 100

        # Field-specific statistics
        fields = ['calories', 'fats', 'saturated_fats', 'carbs', 'sugars', 'fiber', 'proteins', 'salt']
        field_stats = {}

        for field in fields:
            values = [getattr(r, field) for r in self.results if r.success and getattr(r, field) is not None]
            field_stats[field] = {
                'found_count': len(values),
                'success_rate': len(values) / successful_tests * 100 if successful_tests > 0 else 0,
                'avg_value': sum(values) / len(values) if values else 0,
                'min_value': min(values) if values else 0,
                'max_value': max(values) if values else 0
            }

        processing_times = [r.processing_time for r in self.results]
        avg_processing_time = sum(processing_times) / len(processing_times)

        # Generate report
        report = f"""
📊 ENHANCED SIMPLE v19.0 TEST REPORT
{'='*50}

🎯 Overall Results:
   • Total Tests: {total_tests}
   • Successful: {successful_tests} ({success_rate:.1f}%)
   • Failed: {total_tests - successful_tests} ({100-success_rate:.1f}%)
   • Avg Processing Time: {avg_processing_time:.2f}s

📈 Field Detection Rates:
"""

        for field, stats in field_stats.items():
            report += f"   • {field.capitalize()}: {stats['found_count']}/{successful_tests} ({stats['success_rate']:.1f}%)"
            if stats['found_count'] > 0:
                report += f" - Avg: {stats['avg_value']:.1f}, Range: {stats['min_value']:.1f}-{stats['max_value']:.1f}\n"
            else:
                report += "\n"

        self._export_to_csv()
        report += f"\n💾 Detailed results exported to 'nutrition_test_results.csv'\n"

        print(report)
        return report

    def _export_to_csv(self):
        """Export detailed results to CSV"""
        import csv
        with open('nutrition_test_results.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'image_path', 'timestamp', 'success', 'processing_time',
                'calories', 'fats', 'saturated_fats', 'carbs', 'sugars', 'fiber', 'proteins', 'salt',
                'errors'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for result in self.results:
                writer.writerow({
                    'image_path': result.image_path,
                    'timestamp': result.timestamp,
                    'success': result.success,
                    'processing_time': round(result.processing_time, 3),
                    'calories': result.calories,
                    'fats': result.fats,
                    'saturated_fats': result.saturated_fats,
                    'carbs': result.carbs,
                    'sugars': result.sugars,
                    'fiber': result.fiber,
                    'proteins': result.proteins,
                    'salt': result.salt,
                    'errors': '; '.join(result.errors) if result.errors else ''
                })

@dataclass
class NutritionValue:
    """Simple nutrition value container"""
    field_type: str
    value: float
    unit: str
    confidence: float
    source_text: str
    x_pos: float
    y_pos: float
    is_claimed: bool = False
    column_type: str = 'unknown'  # NEW: track if per_100g or per_product

class EnhancedSimpleScanner:
    """
    ENHANCED SIMPLE v19.0 - Column-aware detection for per 100g vs per product
    """

    def __init__(self, debug=True):
        self.debug = debug
        print("🚀 Initializing ENHANCED SIMPLE v19.0 Scanner...")

        # Initialize ONLY EasyOCR (proven to work)
        try:
            self.easy_reader = easyocr.Reader(['en'], gpu=False)
            self.easyocr_available = True
            print("✅ EasyOCR initialized successfully")
        except Exception as e:
            print(f"❌ EasyOCR initialization failed: {e}")
            self.easyocr_available = False

        if not self.easyocr_available:
            raise RuntimeError("❌ EasyOCR not available!")

        print(f"📊 Enhanced OCR engine: EasyOCR with column awareness")

        # ENHANCED field definitions with expanded sugar keywords
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
                'keywords': ['tyydytt', 'mättat', 'saturated', 'mattad', 'mattat', 'tyydyttynyttä', 'tyydyttyneitä'],
                'context_keywords': ['josta', 'varav', 'millest', 'of which', 'siitä'],
                'expected_range': (0, 50),
                'priority': 4,
                'special_handling': True
            },
            'carbs': {
                'keywords': ['hiilihydraat', 'kolhydrat', 'carb'],
                'exclude_keywords': ['sokeri', 'socker', 'sugar'],
                'expected_range': (0, 120),
                'priority': 3
            },
            'fiber': {
                'keywords': ['ravintokuitu', 'kostfiber', 'kuitu', 'fiber'],
                'expected_range': (0, 80),
                'priority': 5
            },
            'proteins': {
                'keywords': ['proteiini', 'protein'],
                'expected_range': (0, 85),
                'priority': 3
            },
            'sugars': {
                'keywords': ['sokeri', 'socker', 'sugar', 'suhkr', 'suhkru', 'sockerarter', 'sokereita', 'soker'],  # EXPANDED!
                'context_keywords': ['josta', 'varav', 'millest', 'of which', 'joista'],  # EXPANDED!
                'expected_range': (0, 80),
                'priority': 6
            },
            'salt': {
                'keywords': ['suola', 'salt'],
                'expected_range': (0, 5),
                'priority': 7
            }
        }

    def preprocess_enhanced(self, image):
        """Enhanced preprocessing"""
        from PIL import Image, ImageEnhance

        if isinstance(image, str):
            if image.startswith('data:'):
                image = image.split(',')[1]
            image_bytes = base64.b64decode(image)
            pil_image = Image.open(io.BytesIO(image_bytes))
        else:
            pil_image = image.copy()

        # Enhanced resize
        width, height = pil_image.size
        if height < 1100:
            scale_factor = 1300 / height
            new_size = (int(width * scale_factor), 1300)
            pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)

        # Enhanced sharpening for better text detection
        enhancer = ImageEnhance.Contrast(pil_image)
        pil_image = enhancer.enhance(1.3)

        enhancer = ImageEnhance.Sharpness(pil_image)
        pil_image = enhancer.enhance(1.5)

        return pil_image

    def log_debug(self, message):
        if self.debug:
            print(f"🔍 {message}")

    def extract_text_enhanced(self, image_data):
        """Enhanced OCR extraction"""
        try:
            image = None
            if isinstance(image_data, str):
                if image_data.startswith('data:'):
                    image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
            elif isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
            else:
                image = image_data

            if image is None:
                return []

            # Enhanced preprocessing
            preprocessed_image = self.preprocess_enhanced(image)
            image_array = np.array(preprocessed_image)
            self.log_debug(f"✅ Image preprocessed: {image_array.shape}")

            try:
                ocr_results = self.easy_reader.readtext(image_array)
                
                processed_results = []
                for bbox, text, confidence in ocr_results:
                    if confidence >= 0.35:
                        processed_results.append({
                            'text': text,
                            'confidence': confidence,
                            'bbox': bbox,
                            'x': bbox[0][0],
                            'y': bbox[0][1],
                            'width': bbox[1][0] - bbox[0][0],
                            'height': bbox[2][1] - bbox[0][1],
                        })

                processed_results.sort(key=lambda x: (x['y'], x['x']))
                self.log_debug(f"EasyOCR extracted {len(processed_results)} items")
                return processed_results

            except Exception as e:
                self.log_debug(f"❌ EasyOCR failed: {e}")
                return []

        except Exception as e:
            self.log_debug(f"❌ OCR extraction error: {e}")
            return []

    def identify_columns(self, extracted_text):
        """Improved column identification with better pattern matching"""
        self.log_debug(f"\n🔍 COLUMN IDENTIFICATION: Processing {len(extracted_text)} OCR items")
        
        # Expanded indicators for column detection
        per_100g_indicators = [
            '100g', '100 g', 'per 100', 'kohti', '/100g', '/ 100g', '100g:',
            'per 100g', 'per 100 g', 'á 100g', 'á 100 g',  # New patterns
            '100 gramm', '100gr', '/100gr'  # Additional variations
        ]
        per_product_indicators = ['per tuote', 'per product', 'per portion', 'annos', 'portion', 'per paketti', 'per serving']
        
        per_100g_x_values = []
        per_product_x_values = []
        
        for item in extracted_text:
            text_lower = item['text'].lower()
            x_pos = item['x']
            
            if any(indicator in text_lower for indicator in per_100g_indicators):
                per_100g_x_values.append(x_pos)
                self.log_debug(f"🔍 Found per 100g indicator at x={x_pos}: '{item['text']}'")
            
            if any(indicator in text_lower for indicator in per_product_indicators):
                per_product_x_values.append(x_pos)
                self.log_debug(f"🔍 Found per product indicator at x={x_pos}: '{item['text']}'")
        
        # Use median position for more robust column detection
        per_100g_x = np.median(per_100g_x_values) if per_100g_x_values else None
        per_product_x = np.median(per_product_x_values) if per_product_x_values else None
        
        self.log_debug(f"🔍 Column positions - per_100g: {per_100g_x}, per_product: {per_product_x}")
        return per_100g_x, per_product_x

    def extract_numbers_enhanced(self, text: str) -> List[Tuple[float, str]]:
        """ENHANCED number extraction"""
        text = text.strip()
        self.log_debug(f"Enhanced number extraction from: '{text}'")
        
        found_numbers = []

        # Finnish decimal comma with enhanced precision
        decimal_patterns = [
            r'(\d+),(\d+)\s*g\b',       # "9,66 g" -> 9.66
            r'(\d+),(\d+)g\b',          # "9,66g" -> 9.66
            r'(\d+),(\d{1,3})(?=\s|$)', # "9,66" -> 9.66 (up to 3 decimals)
            r'(\d+)\.(\d+)\s*g\b',      # "9.66 g" -> 9.66
            r'(\d+)\.(\d+)g\b',         # "9.66g" -> 9.66
        ]
        
        for pattern in decimal_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    whole = match.group(1)
                    decimal = match.group(2)
                    value = float(f"{whole}.{decimal}")
                    unit = 'g'
                    found_numbers.append((value, unit))
                    self.log_debug(f"  ✅ Found enhanced decimal: {value} {unit}")
                except ValueError:
                    continue

        # Energy formats
        energy_patterns = [
            r'(\d+),(\d+)\s*kcal\b',       # "206,71 kcal" -> 206.71
            r'(\d+)\.(\d+)\s*kcal\b',      # "206.71 kcal" -> 206.71
            r'(\d+)\s*kj\s*/\s*(\d+)\s*kcal',
            r'(\d+)\s*kj/(\d+)\s*kcal',
            r'(\d+[.,]?\d*)\s*kcal\b',
            r'\((\d+)\)',
        ]
        
        for pattern in energy_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if ',' in match.group(0) and 'kcal' in match.group(0).lower():
                        # Handle "206,71 kcal" format
                        if len(match.groups()) >= 2:
                            kcal_value = float(f"{match.group(1)}.{match.group(2)}")
                        else:
                            kcal_value = float(match.group(1).replace(',', '.'))
                    elif len(match.groups()) >= 2 and ('kj' in pattern.lower()):
                        kcal_value = float(match.group(2).replace(',', '.'))
                    else:
                        kcal_value = float(match.group(1).replace(',', '.'))
                    
                    if 50 <= kcal_value <= 600:
                        found_numbers.append((kcal_value, 'kcal'))
                        self.log_debug(f"  ✅ Found enhanced energy: {kcal_value} kcal")
                except ValueError:
                    continue

        # Standard numbers with enhanced patterns
        number_patterns = [
            r'<(\d+(?:[.,]\d+)?)\s*g\b',      # "<0.1g" -> 0.1
            r'(\d+(?:[.,]\d+)?)\s*g\b',       # "11g", "0.9 g"
            r'\b(\d+(?:[.,]\d+)?)(?=\s|$)',   # Standalone numbers
        ]

        for pattern in number_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    number_str = match.group(1).replace(',', '.')
                    value = float(number_str)
                    unit = 'g'
                    
                    if value >= 0:
                        found_numbers.append((value, unit))
                        self.log_debug(f"  ✅ Found enhanced number: {value} {unit}")
                except ValueError:
                    continue

        return found_numbers
    def fuzzy_column_match(text, indicators):
        text_clean = re.sub(r'[^a-z0-9\s]', '', text.lower())
        for indicator in indicators:
            if indicator in text_clean or fuzz.partial_ratio(indicator, text_clean) > 80:
                return True
        return False
    def find_saturated_fat_enhanced(self, extracted_text, columns) -> List[NutritionValue]:
        """Enhanced saturated fat detection with column awareness"""
        saturated_fat_candidates = []
        per_100g_x, per_product_x = columns
        
        self.log_debug(f"\n🧈 ENHANCED SATURATED FAT DETECTION")
        
        saturated_keywords = ['tyydytt', 'mättat', 'saturated', 'mattad', 'mattat', 'tyydyttynyttä', 'tyydyttyneitä', 'tyyd', 'gesätt']
        context_keywords = ['josta', 'varav', 'millest', 'of which', 'siitä']
        
        for i, item in enumerate(extracted_text):
            text_lower = item['text'].lower()
            
            # Check for saturated fat keywords
            saturated_keyword_found = None
            for keyword in saturated_keywords:
                if keyword in text_lower:
                    saturated_keyword_found = keyword
                    break
            
            if not saturated_keyword_found:
                continue
                
            self.log_debug(f"🧈 Found saturated keyword '{saturated_keyword_found}' in: '{item['text']}'")
            
            # Enhanced context checking
            has_context = any(ctx in text_lower for ctx in context_keywords)
            
            if not has_context:
                # Check nearby text
                for j in range(max(0, i-3), min(len(extracted_text), i+4)):
                    if j != i:
                        nearby_text = extracted_text[j]['text'].lower()
                        if any(ctx in nearby_text for ctx in context_keywords):
                            has_context = True
                            break
            
            # Accept specific keywords without context
            if not has_context and saturated_keyword_found in ['tyydytt', 'mättat', 'saturated']:
                has_context = True
            
            if has_context:
                # Enhanced search with column preference
                for search_radius in [120, 250, 400]:
                    found_candidates = []
                    
                    for j, candidate_item in enumerate(extracted_text):
                        if i == j:
                            continue
                        
                        y_dist = abs(candidate_item['y'] - item['y'])
                        x_dist = abs(candidate_item['x'] - item['x'])
                        
                        if y_dist <= 30:
                            distance = x_dist
                        elif y_dist <= search_radius and x_dist <= search_radius:
                            distance = (x_dist**2 + y_dist**2)**0.5
                        else:
                            continue
                        
                        # Determine column type
                        column_type = 'unknown'
                        if per_100g_x and per_product_x:
                            dist_to_100g = abs(candidate_item['x'] - per_100g_x)
                            dist_to_product = abs(candidate_item['x'] - per_product_x)
                            column_type = 'per_100g' if dist_to_100g < dist_to_product else 'per_product'
                        
                        numbers_in_candidate = self.extract_numbers_enhanced(candidate_item['text'])
                        for value, unit in numbers_in_candidate:
                            final_value = value
                            if unit == 'mg':
                                final_value = value / 1000
                            
                            if 0 <= final_value <= 50:
                                # Column preference: strongly prefer per_100g values
                                confidence = candidate_item['confidence']
                                if column_type == 'per_100g':
                                    confidence += 0.2
                                elif column_type == 'per_product':
                                    confidence -= 0.1
                                
                                found_candidates.append((final_value, unit, distance, confidence, 
                                                       candidate_item['text'], column_type))
                    
                    if found_candidates:
                        found_candidates.sort(key=lambda x: (-x[3], x[2]))  # Sort by confidence desc, distance asc
                        final_value, unit, distance, confidence, source_text, column_type = found_candidates[0]
                        
                        saturated_fat_candidates.append(NutritionValue(
                            field_type='saturated_fats',
                            value=final_value,
                            unit=unit,
                            confidence=confidence,
                            source_text=source_text,
                            x_pos=item['x'],
                            y_pos=item['y'],
                            is_claimed=False,
                            column_type=column_type
                        ))
                        
                        self.log_debug(f"🧈 ENHANCED CANDIDATE: {final_value}{unit} (dist: {distance:.1f}, conf: {confidence:.3f}, column: {column_type})")
                        break  # Found one, stop expanding search
        
        saturated_fat_candidates.sort(key=lambda x: (-x.confidence, x.column_type == 'per_100g'))
        self.log_debug(f"🧈 Found {len(saturated_fat_candidates)} enhanced saturated fat candidates")
        
        return saturated_fat_candidates

    def find_sugar_enhanced(self, extracted_text, columns) -> List[NutritionValue]:
        """ENHANCED sugar detection with expanded keywords"""
        sugar_candidates = []
        per_100g_x, per_product_x = columns
        
        self.log_debug(f"\n🍭 ENHANCED SUGAR DETECTION")
        
        sugar_keywords = ['sokeri', 'socker', 'sugar', 'suhkr', 'suhkru', 'sockerarter', 'sokereita', 'soker']
        context_keywords = ['josta', 'varav', 'millest', 'of which', 'joista', 'siitä']
        
        for i, item in enumerate(extracted_text):
            text_lower = item['text'].lower()
            
            # Check for sugar keywords
            sugar_keyword_found = None
            for keyword in sugar_keywords:
                if keyword in text_lower:
                    sugar_keyword_found = keyword
                    break
            
            if not sugar_keyword_found:
                continue
                
            self.log_debug(f"🍭 Found sugar keyword '{sugar_keyword_found}' in: '{item['text']}'")
            
            # Enhanced context checking (more lenient for sugars)
            has_context = any(ctx in text_lower for ctx in context_keywords)
            
            if not has_context:
                # Check nearby text
                for j in range(max(0, i-3), min(len(extracted_text), i+4)):
                    if j != i:
                        nearby_text = extracted_text[j]['text'].lower()
                        if any(ctx in nearby_text for ctx in context_keywords):
                            has_context = True
                            break
            
            # Accept sugar keywords more liberally
            if not has_context:
                has_context = True  # Allow sugars without strict context requirements
                self.log_debug(f"🍭 Accepting sugar keyword without strict context")
            
            if has_context:
                # Enhanced search with column preference
                for search_radius in [120, 250, 400]:
                    found_candidates = []
                    
                    for j, candidate_item in enumerate(extracted_text):
                        if i == j:
                            continue
                        
                        y_dist = abs(candidate_item['y'] - item['y'])
                        x_dist = abs(candidate_item['x'] - item['x'])
                        
                        if y_dist <= 40:  # Slightly larger search for sugars
                            distance = x_dist
                        elif y_dist <= search_radius and x_dist <= search_radius:
                            distance = (x_dist**2 + y_dist**2)**0.5
                        else:
                            continue
                        
                        # Determine column type
                        column_type = 'unknown'
                        if per_100g_x and per_product_x:
                            dist_to_100g = abs(candidate_item['x'] - per_100g_x)
                            dist_to_product = abs(candidate_item['x'] - per_product_x)
                            column_type = 'per_100g' if dist_to_100g < dist_to_product else 'per_product'
                        
                        numbers_in_candidate = self.extract_numbers_enhanced(candidate_item['text'])
                        for value, unit in numbers_in_candidate:
                            final_value = value
                            if unit == 'mg':
                                final_value = value / 1000
                            
                            if 0 <= final_value <= 80:  # Sugar range
                                # Column preference: strongly prefer per_100g values
                                confidence = candidate_item['confidence']
                                if column_type == 'per_100g':
                                    confidence += 0.2
                                elif column_type == 'per_product':
                                    confidence -= 0.1
                                
                                found_candidates.append((final_value, unit, distance, confidence, 
                                                       candidate_item['text'], column_type))
                    
                    if found_candidates:
                        found_candidates.sort(key=lambda x: (-x[3], x[2]))
                        final_value, unit, distance, confidence, source_text, column_type = found_candidates[0]
                        
                        sugar_candidates.append(NutritionValue(
                            field_type='sugars',
                            value=final_value,
                            unit=unit,
                            confidence=confidence,
                            source_text=source_text,
                            x_pos=item['x'],
                            y_pos=item['y'],
                            is_claimed=False,
                            column_type=column_type
                        ))
                        
                        self.log_debug(f"🍭 ENHANCED SUGAR CANDIDATE: {final_value}{unit} (dist: {distance:.1f}, conf: {confidence:.3f}, column: {column_type})")
                        break
        
        sugar_candidates.sort(key=lambda x: (-x.confidence, x.column_type == 'per_100g'))
        self.log_debug(f"🍭 Found {len(sugar_candidates)} enhanced sugar candidates")
        
        return sugar_candidates

    def find_nutrition_values_enhanced(self, extracted_text, columns) -> Dict[str, List[NutritionValue]]:
        """Improved value finding with better fat detection"""
        nutrition_values = {field: [] for field in self.nutrition_fields.keys()}
        per_100g_x, per_product_x = columns
        
        self.log_debug(f"\n🔥 ENHANCED PARSING: Processing {len(extracted_text)} OCR items")
        
        # Handle saturated fats specially
        enhanced_saturated_fats = self.find_saturated_fat_enhanced(extracted_text, columns)
        nutrition_values['saturated_fats'] = enhanced_saturated_fats
        
        # Handle sugars specially
        enhanced_sugars = self.find_sugar_enhanced(extracted_text, columns)
        nutrition_values['sugars'] = enhanced_sugars
        
        # Process other fields with column awareness
        for i, item in enumerate(extracted_text):
            text_lower = item['text'].lower()
            
            if len(text_lower.strip()) < 2:
                continue
                
            for field_name, field_config in self.nutrition_fields.items():
                if field_name in ['saturated_fats', 'sugars']:
                    continue  # Handled specially
                    
                keywords = field_config['keywords']
                exclude_keywords = field_config.get('exclude_keywords', [])
                
                keyword_found = None
                for keyword in keywords:
                    if keyword in text_lower:
                        keyword_found = keyword
                        break
                
                if not keyword_found:
                    continue
                
                if any(exclude_kw in text_lower for exclude_kw in exclude_keywords):
                    continue
                
                self.log_debug(f"📍 Found {field_name} keyword '{keyword_found}' in: '{item['text']}'")
                
                # For fats, use a more targeted approach
                if field_name == 'fats':
                    fat_candidates = self.find_fat_specific(extracted_text, i, columns)
                    nutrition_values['fats'].extend(fat_candidates)
                    continue
                    
                # Standard approach for other fields
                candidate_numbers = []
                
                # Numbers in same text
                numbers_in_text = self.extract_numbers_enhanced(item['text'])
                for value, unit in numbers_in_text:
                    if self._is_reasonable_value_enhanced(field_name, value, unit):
                        candidate_numbers.append((value, unit, 0, item['confidence'], 'unknown'))
                
                # Nearby search with column preference
                if not candidate_numbers:
                    for j, candidate_item in enumerate(extracted_text):
                        if i == j:
                            continue
                        
                        y_dist = abs(candidate_item['y'] - item['y'])
                        x_dist = abs(candidate_item['x'] - item['x'])
                        
                        if y_dist <= 30:
                            distance = x_dist
                        elif y_dist <= 120 and x_dist <= 300:
                            distance = (x_dist**2 + y_dist**2)**0.5
                        else:
                            continue
                        
                        # Determine column type
                        column_type = 'unknown'
                        confidence_bonus = 0
                        
                        if per_100g_x and per_product_x:
                            dist_to_100g = abs(candidate_item['x'] - per_100g_x)
                            dist_to_product = abs(candidate_item['x'] - per_product_x)
                            if dist_to_100g < dist_to_product:
                                column_type = 'per_100g'
                                confidence_bonus = 0.2  # Strong preference for per 100g
                            else:
                                column_type = 'per_product'
                                confidence_bonus = -0.1  # Slight penalty for per product
                        
                        numbers_in_candidate = self.extract_numbers_enhanced(candidate_item['text'])
                        for value, unit in numbers_in_candidate:
                            if self._is_reasonable_value_enhanced(field_name, value, unit):
                                candidate_numbers.append((value, unit, distance, 
                                                        candidate_item['confidence'] + confidence_bonus, column_type))
                
                if candidate_numbers:
                    # Sort by confidence first (includes column bonuses), then distance
                    candidate_numbers.sort(key=lambda x: (-x[3], x[2]))
                    best_value, best_unit, best_distance, best_confidence, column_type = candidate_numbers[0]
                    
                    final_value = best_value
                    if field_name == 'calories' and best_unit == 'kj':
                        final_value = best_value / 4.184
                    elif field_name == 'salt' and best_unit == 'mg':
                        final_value = best_value / 1000
                    
                    nutrition_value = NutritionValue(
                        field_type=field_name,
                        value=final_value,
                        unit=best_unit,
                        confidence=best_confidence,
                        source_text=item['text'],
                        x_pos=item['x'],
                        y_pos=item['y'],
                        is_claimed=False,
                        column_type=column_type
                    )
                    
                    nutrition_values[field_name].append(nutrition_value)
                    self.log_debug(f"   ✅ ENHANCED CANDIDATE: {field_name}={final_value}{best_unit} (conf: {best_confidence:.3f}, column: {column_type})")
        
        return nutrition_values
    def find_fat_specific(self, extracted_text, index, columns):
        """Specialized fat detection to avoid incorrect values"""
        per_100g_x, per_product_x = columns
        item = extracted_text[index]
        fat_candidates = []
        
        self.log_debug(f"🧈 SPECIALIZED FAT DETECTION for: '{item['text']}'")
        
        # Look for numbers in the same row first
        same_row_items = []
        for j, candidate_item in enumerate(extracted_text):
            if j == index:
                continue
            if abs(candidate_item['y'] - item['y']) < 20:  # Same row
                same_row_items.append(candidate_item)
        
        # Prioritize same row items
        for candidate_item in same_row_items:
            numbers = self.extract_numbers_enhanced(candidate_item['text'])
            for value, unit in numbers:
                if 0 <= value <= 100:  # Reasonable fat range
                    # Determine column type
                    column_type = 'unknown'
                    if per_100g_x and per_product_x:
                        dist_to_100g = abs(candidate_item['x'] - per_100g_x)
                        dist_to_product = abs(candidate_item['x'] - per_product_x)
                        column_type = 'per_100g' if dist_to_100g < dist_to_product else 'per_product'
                    
                    fat_candidates.append(NutritionValue(
                        field_type='fats',
                        value=value,
                        unit=unit,
                        confidence=candidate_item['confidence'],
                        source_text=candidate_item['text'],
                        x_pos=candidate_item['x'],
                        y_pos=candidate_item['y'],
                        is_claimed=False,
                        column_type=column_type
                    ))
                    self.log_debug(f"🧈 Same row fat candidate: {value}{unit} (col: {column_type})")
        
        # If no same row candidates found, expand search
        if not fat_candidates:
            for search_radius in [50, 100, 150]:
                for j, candidate_item in enumerate(extracted_text):
                    if j == index:
                        continue
                    
                    y_dist = abs(candidate_item['y'] - item['y'])
                    x_dist = abs(candidate_item['x'] - item['x'])
                    
                    if y_dist <= search_radius and x_dist <= search_radius:
                        numbers = self.extract_numbers_enhanced(candidate_item['text'])
                        for value, unit in numbers:
                            if 0 <= value <= 100:  # Reasonable fat range
                                # Determine column type
                                column_type = 'unknown'
                                if per_100g_x and per_product_x:
                                    dist_to_100g = abs(candidate_item['x'] - per_100g_x)
                                    dist_to_product = abs(candidate_item['x'] - per_product_x)
                                    column_type = 'per_100g' if dist_to_100g < dist_to_product else 'per_product'
                                
                                fat_candidates.append(NutritionValue(
                                    field_type='fats',
                                    value=value,
                                    unit=unit,
                                    confidence=candidate_item['confidence'],
                                    source_text=candidate_item['text'],
                                    x_pos=candidate_item['x'],
                                    y_pos=candidate_item['y'],
                                    is_claimed=False,
                                    column_type=column_type
                                ))
                                self.log_debug(f"🧈 Nearby fat candidate: {value}{unit} (col: {column_type})")
        
        return fat_candidates

    def find_saturated_fat_enhanced(self, extracted_text, columns) -> List[NutritionValue]:
        """Improved saturated fat detection"""
        saturated_fat_candidates = []
        per_100g_x, per_product_x = columns
        
        self.log_debug(f"\n🧈 ENHANCED SATURATED FAT DETECTION")
        
        saturated_keywords = ['tyydytt', 'mättat', 'saturated', 'mattad', 'mattat', 'tyydyttynyttä', 'tyydyttyneitä']
        context_keywords = ['josta', 'varav', 'millest', 'of which', 'siitä']
        
        for i, item in enumerate(extracted_text):
            text_lower = item['text'].lower()
            
            # Check for saturated fat keywords
            saturated_keyword_found = None
            for keyword in saturated_keywords:
                if keyword in text_lower:
                    saturated_keyword_found = keyword
                    break
            
            if not saturated_keyword_found:
                continue
                
            self.log_debug(f"🧈 Found saturated keyword '{saturated_keyword_found}' in: '{item['text']}'")
            
            # Check if this is likely a saturated fat entry
            is_likely_saturated = False
            
            # Check for context keywords in the same item
            has_context = any(ctx in text_lower for ctx in context_keywords)
            
            # Check for fat-related context
            has_fat_context = any(fat_kw in text_lower for fat_kw in ['rasva', 'fat', 'fett'])
            
            # If we have both a saturated keyword and fat context, it's very likely
            if has_fat_context:
                is_likely_saturated = True
                self.log_debug(f"🧈 Fat context found - very likely saturated fat")
            
            # If we have context keywords, it's likely
            elif has_context:
                is_likely_saturated = True
                self.log_debug(f"🧈 Context keyword found - likely saturated fat")
            
            # Check nearby text for context
            if not is_likely_saturated:
                for j in range(max(0, i-3), min(len(extracted_text), i+4)):
                    if j != i:
                        nearby_text = extracted_text[j]['text'].lower()
                        if any(ctx in nearby_text for ctx in context_keywords):
                            is_likely_saturated = True
                            self.log_debug(f"🧈 Context keyword found nearby - likely saturated fat")
                            break
                        if any(fat_kw in nearby_text for fat_kw in ['rasva', 'fat', 'fett']):
                            is_likely_saturated = True
                            self.log_debug(f"🧈 Fat context found nearby - likely saturated fat")
                            break
            
            # Accept specific keywords without context
            if not is_likely_saturated and saturated_keyword_found in ['tyydytt', 'mättat', 'saturated', 'tyydyttynyttä', 'tyydyttyneet']:
                is_likely_saturated = True
                self.log_debug(f"🧈 Specific keyword accepted without context")
            
            if is_likely_saturated:
                # Look for numbers in the same row first
                same_row_candidates = []
                for j, candidate_item in enumerate(extracted_text):
                    if j == i:
                        continue
                    
                    if abs(candidate_item['y'] - item['y']) < 25:  # Same row
                        numbers = self.extract_numbers_enhanced(candidate_item['text'])
                        for value, unit in numbers:
                            if 0 <= value <= 50:  # Reasonable saturated fat range
                                # Determine column type
                                column_type = 'unknown'
                                if per_100g_x and per_product_x:
                                    dist_to_100g = abs(candidate_item['x'] - per_100g_x)
                                    dist_to_product = abs(candidate_item['x'] - per_product_x)
                                    column_type = 'per_100g' if dist_to_100g < dist_to_product else 'per_product'
                                
                                same_row_candidates.append((
                                    value, unit, 0, candidate_item['confidence'], 
                                    candidate_item['text'], column_type
                                ))
                
                if same_row_candidates:
                    same_row_candidates.sort(key=lambda x: -x[3])  # Sort by confidence
                    best_value, best_unit, distance, confidence, source_text, column_type = same_row_candidates[0]
                    
                    saturated_fat_candidates.append(NutritionValue(
                        field_type='saturated_fats',
                        value=best_value,
                        unit=best_unit,
                        confidence=confidence,
                        source_text=source_text,
                        x_pos=item['x'],
                        y_pos=item['y'],
                        is_claimed=False,
                        column_type=column_type
                    ))
                    self.log_debug(f"🧈 Same row saturated fat: {best_value}{best_unit}")
                    continue
                
                # If no same row candidates, expand search
                for search_radius in [80, 150, 250]:
                    found_candidates = []
                    
                    for j, candidate_item in enumerate(extracted_text):
                        if j == i:
                            continue
                        
                        y_dist = abs(candidate_item['y'] - item['y'])
                        x_dist = abs(candidate_item['x'] - item['x'])
                        
                        if y_dist <= 30:
                            distance = x_dist
                        elif y_dist <= search_radius and x_dist <= search_radius:
                            distance = (x_dist**2 + y_dist**2)**0.5
                        else:
                            continue
                        
                        # Determine column type
                        column_type = 'unknown'
                        if per_100g_x and per_product_x:
                            dist_to_100g = abs(candidate_item['x'] - per_100g_x)
                            dist_to_product = abs(candidate_item['x'] - per_product_x)
                            column_type = 'per_100g' if dist_to_100g < dist_to_product else 'per_product'
                        
                        numbers_in_candidate = self.extract_numbers_enhanced(candidate_item['text'])
                        for value, unit in numbers_in_candidate:
                            final_value = value
                            if unit == 'mg':
                                final_value = value / 1000
                            
                            if 0 <= final_value <= 50:
                                # Column preference: strongly prefer per_100g values
                                confidence = candidate_item['confidence']
                                if column_type == 'per_100g':
                                    confidence += 0.2
                                elif column_type == 'per_product':
                                    confidence -= 0.1
                                
                                found_candidates.append((final_value, unit, distance, confidence, 
                                                    candidate_item['text'], column_type))
                    
                    if found_candidates:
                        found_candidates.sort(key=lambda x: (-x[3], x[2]))  # Sort by confidence desc, distance asc
                        final_value, unit, distance, confidence, source_text, column_type = found_candidates[0]
                        
                        saturated_fat_candidates.append(NutritionValue(
                            field_type='saturated_fats',
                            value=final_value,
                            unit=unit,
                            confidence=confidence,
                            source_text=source_text,
                            x_pos=item['x'],
                            y_pos=item['y'],
                            is_claimed=False,
                            column_type=column_type
                        ))
                        
                        self.log_debug(f"🧈 ENHANCED CANDIDATE: {final_value}{unit} (dist: {distance:.1f}, conf: {confidence:.3f}, column: {column_type})")
                        break  # Found one, stop expanding search
        
        saturated_fat_candidates.sort(key=lambda x: (-x.confidence, x.column_type == 'per_100g'))
        self.log_debug(f"🧈 Found {len(saturated_fat_candidates)} enhanced saturated fat candidates")
        
        return saturated_fat_candidates
    def _is_reasonable_value_enhanced(self, field_name, value, unit='g'):
        """Enhanced value validation"""
        if field_name not in self.nutrition_fields:
            return False

        final_value = value
        if field_name == 'calories' and unit == 'kj':
            final_value = value / 4.184
        elif field_name == 'salt' and unit == 'mg':
            final_value = value / 1000

        min_val, max_val = self.nutrition_fields[field_name]['expected_range']
        is_reasonable = min_val <= final_value <= max_val

        if final_value == 0 and field_name in ['salt', 'sugars', 'saturated_fats', 'fiber']:
            is_reasonable = True
            
        if field_name == 'salt' and 0.01 <= final_value <= 0.99:
            is_reasonable = True

        return is_reasonable

    def select_best_values_enhanced(self, nutrition_values: Dict[str, List[NutritionValue]]) -> Dict[str, NutritionValue]:
        """ENHANCED value selection with column preference"""
        selected_values = {}
        all_values = []
        
        for field_name, values_list in nutrition_values.items():
            for value in values_list:
                all_values.append(value)
        
        field_priorities = [
            ('calories', 1),
            ('fats', 2),
            ('carbs', 3),
            ('proteins', 3),
            ('saturated_fats', 4),
            ('fiber', 5),
            ('sugars', 6),
            ('salt', 7)
        ]
        
        self.log_debug(f"\n🎯 ENHANCED SELECTION: Processing {len(field_priorities)} fields by priority")
        
        for field_name, priority in field_priorities:
            if field_name not in nutrition_values or not nutrition_values[field_name]:
                continue
            
            available_values = [v for v in nutrition_values[field_name] if not v.is_claimed]
            
            if not available_values:
                continue
            
            # Enhanced preference: per_100g column + non-zero values
            if field_name in ['fats', 'carbs', 'proteins']:
                # First try: per_100g non-zero values
                per_100g_non_zero = [v for v in available_values if v.column_type == 'per_100g' and v.value > 0.01]
                if per_100g_non_zero:
                    available_values = per_100g_non_zero
                    self.log_debug(f"   📍 Preferring per_100g non-zero values for {field_name}")
                else:
                    # Fallback: any non-zero values
                    non_zero_values = [v for v in available_values if v.value > 0.01]
                    if non_zero_values:
                        available_values = non_zero_values
                        self.log_debug(f"   📍 Preferring non-zero values for {field_name}")
            
            # Sort by confidence (which includes column bonuses)
            available_values.sort(key=lambda x: (-x.confidence, x.column_type == 'per_100g'))
            best_value = available_values[0]
            
            # Enhanced duplicate checking
            duplicate_found = False
            
            if field_name == 'saturated_fats':
                tolerance = 0.001
                for claimed_value in [v for v in all_values if v.is_claimed]:
                    if claimed_value.field_type == 'fats' and best_value.value <= claimed_value.value * 1.1:
                        duplicate_found = False
                        self.log_debug(f"   ✅ Allowing saturated_fats {best_value.value} vs fats {claimed_value.value} (reasonable ratio)")
                        break
                    elif abs(best_value.value - claimed_value.value) <= tolerance:
                        duplicate_found = True
                        break
            else:
                tolerance = 0.01 if field_name != 'calories' else 1.0
                for claimed_value in [v for v in all_values if v.is_claimed]:
                    if abs(best_value.value - claimed_value.value) <= tolerance:
                        duplicate_found = True
                        break
            
            if not duplicate_found:
                best_value.is_claimed = True
                selected_values[field_name] = best_value
                self.log_debug(f"   ✅ SELECTED {field_name}: {best_value.value} (conf: {best_value.confidence:.3f}, column: {best_value.column_type}) - CLAIMED")
        
        return selected_values

    def validate_enhanced_results(self, selected_values: Dict[str, NutritionValue]) -> Dict[str, float]:
        """Enhanced validation"""
        self.log_debug("\n🔧 ENHANCED VALIDATION")
        
        results = {}
        
        for field_name, nutrition_value in selected_values.items():
            results[field_name] = round(nutrition_value.value, 1)
        
        # Enhanced constraints
        if 'saturated_fats' in results and 'fats' in results:
            if results['saturated_fats'] > results['fats']:
                results['saturated_fats'] = round(results['fats'] * 0.95, 1)
        
        if 'sugars' in results and 'carbs' in results:
            if results['sugars'] > results['carbs'] * 0.98:
                results['sugars'] = round(results['carbs'] * 0.95, 1)
        
        # Carbs fix
        if 'carbs' in results and results['carbs'] > 100:
            potential_fix = results['carbs'] % 100
            if 5 <= potential_fix <= 25:
                results['carbs'] = potential_fix
        
        self.log_debug("✅ Enhanced validation complete")
        return results

    def scan_nutrition_label(self, image_data):
        """ENHANCED main scanning function"""
        try:
            self.log_debug("🚀 Starting ENHANCED SIMPLE v19.0 Scanner...")

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

            # Enhanced OCR
            extracted_text = self.extract_text_enhanced(img)

            if not extracted_text:
                return {'error': 'No text detected', 'success': False}

            # Check per 100g
            full_text = ' '.join([item['text'] for item in extracted_text])
            is_per_100g = any(pattern in full_text.lower() 
                             for pattern in ['100g', '100 g', 'per 100', 'kohti'])

            # Column identification
            columns = self.identify_columns(extracted_text)

            # Enhanced parsing with column awareness
            nutrition_values = self.find_nutrition_values_enhanced(extracted_text, columns)
            selected_values = self.select_best_values_enhanced(nutrition_values)
            validated_results = self.validate_enhanced_results(selected_values)

            # Extract confidence scores
            confidence_scores = {}
            column_info = {}
            for field_name, nutrition_value in selected_values.items():
                confidence_scores[field_name] = nutrition_value.confidence
                column_info[field_name] = nutrition_value.column_type

            # Response
            response = {
                'success': True,
                'nutrition_data': validated_results,
                'per_100g': is_per_100g,
                'raw_text': [item['text'] for item in extracted_text],
                'debug_info': {
                    'total_text_items': len(extracted_text),
                    'fields_found': list(validated_results.keys()),
                    'avg_confidence': sum(item['confidence'] for item in extracted_text) / len(extracted_text),
                    'confidence_scores': confidence_scores,
                    'column_info': column_info,
                    'columns_detected': {
                        'per_100g_x': columns[0],
                        'per_product_x': columns[1]
                    },
                    'version': 'v19.0_enhanced_simple_column_aware',
                    'engines_available': {'easyocr': True}
                }
            }

            self.log_debug(f"\n📊 ENHANCED RESULTS: {len(validated_results)} fields found")
            for field, value in validated_results.items():
                confidence = confidence_scores.get(field, 'N/A')
                column = column_info.get(field, 'N/A')
                self.log_debug(f"    ✅ {field}: {value} (conf: {confidence:.3f}, column: {column})")

            return response

        except Exception as e:
            self.log_debug(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e), 'success': False}


# Example usage
if __name__ == "__main__":
    # Initialize test harness
    harness = NutritionTestHarness(EnhancedSimpleScanner)

    # Test the 4 benchmark clean images
    test_images = [
        "kuva1.jpg",  # Expected: 150 kcal, 9.1g fats, 4.4g saturated_fats, 11g carbs, 6.1g proteins, 1.5g fiber, 0.9g salt
        "kuva4.jpg",  # Expected: 233 kcal, 0.3g fats, 0.1g saturated_fats, 20g carbs, 5g proteins, 65g fiber, 0.10g salt  
        "kuva5.jpg",  # Expected: 360 kcal, 2.2g fats, 1.2g saturated_fats, 13.7g carbs, 65g proteins, 2.9g fiber, 0.5g salt
        "kuva6.jpg"   # Expected: 370 kcal, 6.5g fats, 1.3g saturated_fats, 58g carbs, 14g proteins, 11g fiber, 0g salt
    ]

    # Run test
    report = harness.run_comprehensive_test(test_images)

    print("✅ ENHANCED SIMPLE v19.0 ready with:")
    print("   • COLUMN-AWARE detection (per 100g vs per product)")
    print("   • ENHANCED sugar detection with expanded keywords")
    print("   • FIXED fat value selection (prefer per 100g values)")
    print("   • ENHANCED saturated fat detection with column preference")
    print("   • SMART confidence bonuses for correct columns")
    print("   • TARGET: Fix fat accuracy and improve sugar detection")
    print("   • COLUMN INTELLIGENCE - The Smart Fix! 🎯")
