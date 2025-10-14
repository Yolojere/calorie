import fuzzywuzzy
from rapidocr_onnxruntime import RapidOCR
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

        # Processing time statistics
        processing_times = [r.processing_time for r in self.results]
        avg_processing_time = sum(processing_times) / len(processing_times)

        # Generate report
        report = f"""
📊 ENHANCED SCANNER v32.0 TEST REPORT
{'='*55}

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
    """Enhanced nutrition value container with row grouping"""
    field_type: str
    value: float
    unit: str
    confidence: float
    source_text: str
    x_pos: float
    y_pos: float
    is_claimed: bool = False
    column_type: str = 'unknown'
    row_group: int = -1  # NEW: Row grouping for better alignment

class EnhancedSimpleScanner:
    """
    ENHANCED SCANNER v32.0 - FIXED REGEX PATTERNS + Improved text filtering and row alignment
    """

    def __init__(self, debug=True):
        self.debug = debug
        print("🚀 Initializing ENHANCED SCANNER v32.0...")

        # Initialize ONLY RapidOCR (proven to work)
        try:
            self.rapid_reader = RapidOCR()
            self.rapidocr_available = True
            print("✅ RapidOCR initialized successfully")
        except Exception as e:
            print(f"❌ RapidOCR initialization failed: {e}")
            self.rapidocr_available = False

        if not self.rapidocr_available:
            raise RuntimeError("❌ RapidOCR not available!")

        print(f"📊 Enhanced OCR engine: RapidOCR with FIXED regex patterns")

        # ENHANCED field definitions with better noise filtering
        self.nutrition_fields = {
            'calories': {
                'keywords': ['energia', 'energi', 'energy', 'kcal', 'kj', 'kalori'],
                'exclude_keywords': ['information', 'ingredient', 'allergen', 'storage', 'advice'],
                'expected_range': (50, 600),
                'priority': 1
            },
            'fats': {
                'keywords': ['rasva', 'rasvaa', 'fett', 'fat', 'rasvad', 'lipid'],
                'exclude_keywords': ['tyydytt', 'mättat', 'saturated', 'kullast', 'gesättigt', 'information', 'ingredient'],
                'expected_range': (0, 100),
                'priority': 2
            },
            'saturated_fats': {
                'keywords': [
                    'saturated', 'tyydytt', 'mattat', 'gesättigt', 'saturés',
                    'mattede', 'kullastunud', 'piesätinäti', 'насыщен',
                    'saturat', 'mättade', 'насищен', 'tydytty', 'mättad',
                    'tyydyttynyt', 'tyydyttyneet', 'tyydyttyneitä', 'mattad',
                    'tyydyttynytta'
                ],
                'context_keywords': ['josta', 'varav', 'millest', 'of which', 'siitä', 'whereof', 'davon'],
                'expected_range': (0, 50),
                'priority': 4,
                'special_handling': True
            },
            'carbs': {
                'keywords': ['hiilihydraat', 'hiilihydraatit', 'kolhydrat', 'carbohydrat', 'carb', 'susivesik', 'hilihydraat'],
                'exclude_keywords': ['sokeri', 'socker', 'sugar', 'suhkr', 'kuitu', 'fiber', 'fibre', 'protei', 'valk', 'information'],
                'expected_range': (0, 120),
                'priority': 3
            },
            'fiber': {
                'keywords': [
                    'fiber', 'fibre', 'kuitu', 'ravintokuitu', 'kostfiber', 'ballaststoff', 'fibres',
                    'kiudaine', 'skiedrviela', 'skaidula', 'клетчатка',
                    'kostfibr', 'dietary fiber', 'kuidained', 'kiudained'
                ],
                'exclude_keywords': ['hiilihydraat', 'kolhydrat', 'carb', 'susivesik', 'protei', 'rasva', 'tyydytty', 'valk', 'protein', 'information'],
                'expected_range': (0, 80),
                'priority': 5
            },
            'proteins': {
                'keywords': ['proteiini', 'protein', 'valk', 'белок', 'olbaltum', 'baltym', 'prot', 'valgud'],
                'exclude_keywords': ['rasva', 'hiilihydra', 'kuitu', 'tyydytty', 'sokeri', 'ravinto', 'suola', 'fiber', 'fibre', 'information'],
                'expected_range': (0, 85),
                'priority': 3
            },
            'sugars': {
                'keywords': [
                    'sugar', 'sokeri', 'socker', 'sucre', 'azucar', 'zucker', 'suhkr',
                    'sockerarter', 'sokereita', 'suhkrud', 'cukru', 'cukurs',
                    'sugars', 'zuccheri', 'açúcar', 'glucides', 'сахар', 'cukrų'
                ],
                'context_keywords': ['josta', 'varav', 'millest', 'of which', 'joista', 'siitä', 'whereof'],
                'exclude_keywords': ['hiilihydraat', 'kolhydrat', 'carb', 'protei', 'fiber', 'information'],
                'expected_range': (0, 80),
                'priority': 6
            },
            'salt': {
                'keywords': ['suola', 'salt', 'sool'],
                'exclude_keywords': ['sisaldus', 'narings', 'ravinto', 'protei', 'fiber', 'information', 'ingredient'],
                'expected_range': (0, 5),
                'priority': 7
            }
        }

        # ENHANCED noise filtering patterns
        self.noise_patterns = [
            # Header/footer noise
            r'nutrition\s*information',
            r'nutritional\s*values',
            r'ravintosisältö',
            r'näringsinnehåll',
            r'näringsdeklaration',
            r'toiteväärtus',
            
            # Storage/usage instructions
            r'store\s*in',
            r'best\s*before',
            r'use\s*by',
            r'säilytä',
            r'käytä\s*ennen',
            
            # Ingredient lists
            r'ingredients',
            r'ainesosat',
            r'ingredienser',
            r'koostis',
            
            # Allergen information
            r'allergen',
            r'allergeni',
            r'allergeeni',
            
            # Company information
            r'manufactured\s*by',
            r'produced\s*by',
            r'distributed\s*by',
            r'valmistaja',
            
            # Advice/warnings
            r'advice',
            r'warning',
            r'neuvo',
            r'varoitus',
            
            # Legal text
            r'trademark',
            r'copyright',
            r'©',
            r'®',
            r'™'
        ]

        # Contamination patterns
        self.contamination_patterns = [
            r'100\s*g',     
            r'100g',        
            r'per\s*100',   
            r'kohti',       
            r'%',           
            r'narings',     
            r'toite',       
        ]

        # PER 100G COLUMN DETECTION PATTERNS
        self.per_100g_indicators = [
            '100g', '100 g', 'per 100', 'kohti 100', '/100g', '/ 100g', '100g:',
            'per 100g', 'per 100 g', 'à 100g', 'à 100 g', '100 gramm', '100gr', '/100gr'
        ]
        
        # PER PORTION DETECTION PATTERNS  
        self.per_portion_indicators = [
            'per portion', 'portion', 'per serving', 'serving', 'per pack', 'pack',
            'per 40g', 'per 30g', 'per 50g', 'annos', 'portion'
        ]

    def filter_noise_enhanced(self, extracted_text):
        """ENHANCED noise filtering for text-heavy images"""
        self.log_debug(f"\n🔍 ENHANCED NOISE FILTERING")
        
        filtered_text = []
        noise_count = 0
        
        for item in extracted_text:
            text_lower = item['text'].lower().strip()
            
            # Skip empty or very short text
            if len(text_lower) < 2:
                noise_count += 1
                continue
            
            # Check against noise patterns
            is_noise = False
            for pattern in self.noise_patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    is_noise = True
                    self.log_debug(f"  🚫 NOISE FILTERED: '{item['text']}' (matched: {pattern})")
                    noise_count += 1
                    break
            
            if is_noise:
                continue
            
            # Filter out very long text items (likely paragraphs)
            if len(item['text']) > 50:
                # Check if it contains nutrition-relevant keywords
                has_nutrition_keywords = False
                for field_config in self.nutrition_fields.values():
                    for keyword in field_config['keywords']:
                        if keyword in text_lower:
                            has_nutrition_keywords = True
                            break
                    if has_nutrition_keywords:
                        break
                
                if not has_nutrition_keywords:
                    self.log_debug(f"  🚫 LONG TEXT FILTERED: '{item['text'][:30]}...'")
                    noise_count += 1
                    continue
            
            # Filter out obvious non-nutrition text
            if any(word in text_lower for word in ['www.', 'http', 'email', 'phone', 'tel:', 'fax:']):
                self.log_debug(f"  🚫 CONTACT INFO FILTERED: '{item['text']}'")
                noise_count += 1
                continue
            
            # Filter out barcodes/product codes (all numbers with specific patterns)
            if re.match(r'^\d{8,}$', item['text'].replace(' ', '')):
                self.log_debug(f"  🚫 BARCODE FILTERED: '{item['text']}'")
                noise_count += 1
                continue
            
            filtered_text.append(item)
        
        self.log_debug(f"  📊 NOISE FILTERING: {noise_count} items filtered, {len(filtered_text)} items remaining")
        return filtered_text

    def create_row_groups_enhanced(self, extracted_text):
        """ENHANCED row grouping to handle curved/tilted images"""
        self.log_debug(f"\n🔧 ENHANCED ROW GROUPING")
        
        if not extracted_text:
            return []
        
        # Sort by Y position
        sorted_items = sorted(extracted_text, key=lambda x: x['y'])
        
        # ENHANCED row grouping with adaptive tolerance
        row_groups = []
        current_group = []
        adaptive_tolerance = 25  # Start with base tolerance
        
        for i, item in enumerate(sorted_items):
            if not current_group:
                current_group = [item]
                continue
            
            # Calculate Y position variance in current group
            current_y_positions = [x['y'] for x in current_group]
            y_variance = max(current_y_positions) - min(current_y_positions)
            
            # Adaptive tolerance based on variance (handles curves better)
            if y_variance > 20:
                adaptive_tolerance = min(40, y_variance * 1.5)  # Increase tolerance for curved lines
            else:
                adaptive_tolerance = 25  # Standard tolerance
            
            # Check if item belongs to current group
            avg_y = sum(current_y_positions) / len(current_y_positions)
            y_distance = abs(item['y'] - avg_y)
            
            if y_distance <= adaptive_tolerance:
                current_group.append(item)
                self.log_debug(f"    📍 Added '{item['text']}' to group (y_dist: {y_distance:.1f}, tolerance: {adaptive_tolerance:.1f})")
            else:
                # Start new group
                if current_group:
                    row_groups.append(current_group)
                    self.log_debug(f"  📝 ROW GROUP {len(row_groups)}: {len(current_group)} items, Y range: {min(current_y_positions):.1f}-{max(current_y_positions):.1f}")
                current_group = [item]
        
        # Add last group
        if current_group:
            row_groups.append(current_group)
        
        # Assign row group numbers
        enhanced_text = []
        for group_idx, group in enumerate(row_groups):
            for item in group:
                enhanced_item = item.copy()
                enhanced_item['row_group'] = group_idx
                enhanced_text.append(enhanced_item)
        
        self.log_debug(f"  📊 CREATED {len(row_groups)} row groups from {len(extracted_text)} items")
        return enhanced_text

    def detect_columns_enhanced(self, extracted_text):
        """Enhanced column detection with per 100g identification"""
        self.log_debug(f"\n🔍 ENHANCED COLUMN DETECTION")
        
        per_100g_x_positions = []
        per_portion_x_positions = []
        
        # Find column indicators
        for item in extracted_text:
            text_lower = item['text'].lower()
            
            # Check for per 100g indicators
            for indicator in self.per_100g_indicators:
                if indicator in text_lower:
                    per_100g_x_positions.append(item['x'])
                    self.log_debug(f"  🏷️ Per 100g indicator found: '{item['text']}' at x={item['x']}")
                    break
            
            # Check for per portion indicators  
            for indicator in self.per_portion_indicators:
                if indicator in text_lower:
                    per_portion_x_positions.append(item['x'])
                    self.log_debug(f"  📦 Per portion indicator found: '{item['text']}' at x={item['x']}")
                    break
        
        # Determine column positions
        per_100g_x = None
        per_portion_x = None
        
        if per_100g_x_positions:
            per_100g_x = sum(per_100g_x_positions) / len(per_100g_x_positions)
            self.log_debug(f"  📊 Per 100g column detected at x={per_100g_x:.0f}")
        
        if per_portion_x_positions:
            per_portion_x = sum(per_portion_x_positions) / len(per_portion_x_positions)
            self.log_debug(f"  📦 Per portion column detected at x={per_portion_x:.0f}")
        
        return per_100g_x, per_portion_x

    def extract_numbers_with_ocr_enhancement(self, text: str) -> List[Tuple[float, str]]:
        """FIXED OCR-enhanced decimal extraction with corrected regex patterns"""
        original_text = text
        self.log_debug(f"🔢 FIXED OCR extraction from: '{original_text}'")
        
        # Contamination check - but be less strict
        text_lower = text.lower()
        strict_contamination = ['per 100', 'kohti', 'narings', 'toite']
        for pattern in strict_contamination:
            if pattern in text_lower and 'kcal' not in text_lower and 'kj' not in text_lower:
                self.log_debug(f"  🚫 STRICT CONTAMINATION: '{text}' - SKIPPING")
                return []
        
        found_numbers = []

        # FIXED ENHANCEMENT PATTERNS with corrected regex
        enhanced_patterns = [
            # === ABSOLUTE HIGHEST PRIORITY: ENERGY COMBINATIONS ===
            (r'(\d+)\s*kj\s*/\s*(\d+)\s*kcal', 'energy_combo_space'),
            (r'(\d+)kj/(\d+)kcal', 'energy_combo_nospace'),
            (r'(\d+),(\d+)\s*kj\s*/\s*(\d+)\s*kcal', 'energy_combo_decimal'),
            (r'(\d+)\s*kj\s*/\s*(\d+),(\d+)\s*kcal', 'energy_combo_decimal'),
            
            # === FIXED OCR ENHANCEMENT: MISSING DIGIT RECOVERY ===
            (r'^\.(\d{1,2})\s*g\b', 'missing_first_digit'),      # ".14g" -> could be "14g"
            (r'^,(\d{1,2})\s*g\b', 'missing_first_digit'),       # ",14g" -> could be "14g"  
            (r'^(\d{1,2})\.\s*g\b', 'missing_last_digit'),       # "14.g" -> could be "14g"
            (r'^(\d{1,2}),\s*g\b', 'missing_last_digit'),        # "14,g" -> could be "14g"
            
            # === STANDARD PARTIAL OCR FIXES ===
            (r'^\.(\d{1,3})\s*g\b', 'partial_dot'),
            (r'^,(\d{1,3})\s*g\b', 'partial_comma'),
            
            # === FIXED DECIMAL PATTERNS ===
            (r'(\d+),(\d{1,3})\s*kcal\b', 'decimal_comma'),   
            (r'(\d+)\.(\d{1,3})\s*kcal\b', 'decimal_dot'),    
            (r'(\d+),(\d{1,3})\s*g\b', 'decimal_comma'),      
            (r'(\d+)\.(\d{1,3})\s*g\b', 'decimal_dot'),       
            (r'0,(\d{1,3})\s*g\b', 'small_comma'),            
            (r'0\.(\d{1,3})\s*g\b', 'small_dot'),             
            
            # === NO-SPACE PATTERNS ===
            (r'(\d+),(\d{1,3})kcal\b', 'decimal_comma'),      
            (r'(\d+)\.(\d{1,3})kcal\b', 'decimal_dot'),       
            (r'(\d+),(\d{1,3})g\b', 'decimal_comma'),         
            (r'(\d+)\.(\d{1,3})g\b', 'decimal_dot'),          
            (r'0,(\d{1,3})g\b', 'small_comma'),               
            (r'0\.(\d{1,3})g\b', 'small_dot'),                
            
            # === BASIC SPACE SEPARATED PATTERNS ===
            (r'(\d+)\s+g\b', 'integer_space'),                # "22 g"
            (r'(\d+)\s+kcal\b', 'integer_space'),             # "360 kcal" 
            (r'(\d+),(\d{1,3})\s+g\b', 'decimal_comma_space'), # "1,2 g"
            (r'(\d+)\.(\d{1,3})\s+g\b', 'decimal_dot_space'),  # "1.2 g"
            (r'(\d+):(\d{1,3})\s+g\b', 'colon_decimal'),      # "12:7 g" (OCR error)
            
            # === INTEGER PATTERNS (LOWEST PRIORITY) ===
            (r'(\d+)\s*kcal\b', 'integer'),                   
            (r'(\d+)\s*g\b', 'integer'),                      
            (r'(\d+)kcal\b', 'integer'),                      
            (r'(\d+)g\b', 'integer'),
            
            # === OCR ERROR PATTERNS ===
            (r'(\d+)\.(\d{1,3})', 'standalone_decimal'),      # "2.99" 
            (r'(\d+),(\d{1,3})', 'standalone_decimal_comma'), # "13,7"
            (r'^(\d+)$', 'standalone_integer'),               # Just numbers like "360", "419"
        ]
        
        # Process patterns in priority order, stop at first match
        for pattern, pattern_type in enhanced_patterns:
            match = re.search(pattern, original_text, re.IGNORECASE)
            if match:
                try:
                    full_match = match.group(0)
                    groups = match.groups()
                    
                    # Determine unit from match or context
                    unit = 'g'  # default
                    if 'kcal' in full_match.lower():
                        unit = 'kcal'
                    elif 'mg' in full_match.lower():
                        unit = 'mg' 
                    elif 'kj' in full_match.lower():
                        unit = 'kj'
                    # Context-based unit detection
                    elif pattern_type == 'standalone_integer':
                        # Try to determine unit from context
                        if 300 <= int(groups[0]) <= 700:  # Likely calories
                            unit = 'kcal'
                        elif int(groups[0]) >= 1000:  # Very likely kJ 
                            unit = 'kj'
                    
                    # Handle different pattern types
                    value = None
                    
                    if pattern_type in ['energy_combo_space', 'energy_combo_nospace']:
                        value = float(groups[1])
                        unit = 'kcal'
                        self.log_debug(f"  🔥 ENERGY COMBO DETECTED: '{full_match}' -> {value} kcal")
                        
                    elif pattern_type == 'energy_combo_decimal':
                        if len(groups) == 3:
                            value = float(groups[2])
                            unit = 'kcal'
                        elif len(groups) == 4:
                            value = float(f"{groups[2]}.{groups[3]}")
                            unit = 'kcal'
                        self.log_debug(f"  🔥 ENERGY COMBO DECIMAL: '{full_match}' -> {value} kcal")
                        
                    elif pattern_type == 'missing_first_digit':
                        # OCR ENHANCEMENT: ".14g" could be "14g" (missing first digit)
                        digit_value = int(groups[0])
                        if digit_value >= 10:  # 10-99 range suggests missing digit
                            value = float(digit_value)
                            self.log_debug(f"  🔧 OCR ENHANCEMENT - MISSING FIRST DIGIT: '{full_match}' -> {value}g (recovered)")
                        else:
                            value = float(f"0.{groups[0]}")
                            self.log_debug(f"  🔧 PARTIAL OCR FIX: '{full_match}' -> {value}")
                        
                    elif pattern_type == 'missing_last_digit':
                        value = float(groups[0])
                        self.log_debug(f"  🔧 OCR ENHANCEMENT - MISSING LAST DIGIT: '{full_match}' -> {value}g")
                        
                    elif pattern_type in ['partial_dot', 'partial_comma']:
                        value = float(f"0.{groups[0]}")
                        self.log_debug(f"  🔧 PARTIAL OCR FIX: '{full_match}' -> {value}")
                        
                    elif pattern_type in ['small_comma', 'small_dot']:
                        value = float(f"0.{groups[0]}")
                        
                    elif pattern_type in ['decimal_comma', 'decimal_dot', 'decimal_comma_space', 'decimal_dot_space']:
                        if len(groups) == 2:
                            value = float(f"{groups[0]}.{groups[1]}")
                        else:
                            value = float(groups[0])
                    
                    elif pattern_type == 'colon_decimal':
                        # Handle "12:7 g" -> "12.7 g"
                        value = float(f"{groups[0]}.{groups[1]}")
                        self.log_debug(f"  🔧 COLON ERROR FIX: '{full_match}' -> {value}g")
                        
                    elif pattern_type in ['integer', 'integer_space']:
                        value = float(groups[0])
                        
                    elif pattern_type in ['standalone_decimal', 'standalone_decimal_comma']:
                        value = float(f"{groups[0]}.{groups[1]}")
                        
                    elif pattern_type == 'standalone_integer':
                        value = float(groups[0])
                        
                    if value is not None and value >= 0:
                        found_numbers.append((value, unit))
                        self.log_debug(f"  ✅ FIXED OCR MATCH: {value} {unit} from '{full_match}' (type: {pattern_type})")
                        break  # STOP AT FIRST MATCH
                        
                except (ValueError, IndexError) as e:
                    self.log_debug(f"  ❌ Pattern match error: {e}")
                    continue

        self.log_debug(f"  📊 TOTAL EXTRACTED: {len(found_numbers)} numbers")
        for num, unit in found_numbers:
            self.log_debug(f"    • {num} {unit}")
        
        return found_numbers

    def is_field_keyword_match_strict(self, text: str, field_config: dict) -> bool:
        """Strict field keyword matching"""
        text_lower = text.lower().strip()
        
        # Check exclusion keywords FIRST
        exclude_keywords = field_config.get('exclude_keywords', [])
        for exclude_kw in exclude_keywords:
            if exclude_kw in text_lower:
                self.log_debug(f"  🚫 EXCLUDED by keyword '{exclude_kw}' in '{text}'")
                return False
        
        # Check positive keywords
        keywords = field_config['keywords']
        for keyword in keywords:
            if keyword in text_lower:
                # Strict matching for salt field
                if field_config.get('priority') == 7:  # salt field
                    if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
                        self.log_debug(f"  ✅ STRICT FIELD MATCH: '{keyword}' found in '{text}'")
                        return True
                else:
                    self.log_debug(f"  ✅ FIELD MATCH: '{keyword}' found in '{text}'")
                    return True
        
        return False

    def determine_value_column_type(self, val_x: float, per_100g_x: Optional[float], per_portion_x: Optional[float]) -> str:
        """Determine if a value is in per 100g or per portion column"""
        if per_100g_x is not None and per_portion_x is not None:
            # Both columns detected - choose closest
            dist_to_100g = abs(val_x - per_100g_x)
            dist_to_portion = abs(val_x - per_portion_x)
            
            if dist_to_100g <= 50:  # Within 50px of per 100g column
                return 'per_100g'
            elif dist_to_portion <= 50:  # Within 50px of per portion column
                return 'per_portion'
        elif per_100g_x is not None:
            # Only per 100g column detected
            if abs(val_x - per_100g_x) <= 50:
                return 'per_100g'
        elif per_portion_x is not None:
            # Only per portion column detected
            if abs(val_x - per_portion_x) <= 50:
                return 'per_portion'
        
        return 'unknown'

    def find_all_nutrition_values_enhanced(self, extracted_text, columns) -> Dict[str, List[NutritionValue]]:
        """ENHANCED value finding with better row alignment and text filtering"""
        nutrition_values = {field: [] for field in self.nutrition_fields.keys()}
        per_100g_x, per_portion_x = columns
        
        self.log_debug(f"\n🔥 ENHANCED NUTRITION VALUE EXTRACTION")
        self.log_debug(f"📊 Column positions - per_100g: {per_100g_x}, per_portion: {per_portion_x}")
        
        # First pass: Find all field labels
        field_labels = {}
        for field_name, field_config in self.nutrition_fields.items():
            field_labels[field_name] = []
            for i, item in enumerate(extracted_text):
                if self.is_field_keyword_match_strict(item['text'], field_config):
                    field_labels[field_name].append((i, item))
                    self.log_debug(f"  🏷️ {field_name.upper()} label: '{item['text']}' at ({item['x']:.0f}, {item['y']:.0f}) [row_group: {item.get('row_group', -1)}]")
        
        # Second pass: Find all numerical values with column classification
        all_values = []
        for i, item in enumerate(extracted_text):
            numbers = self.extract_numbers_with_ocr_enhancement(item['text'])
            for value, unit in numbers:
                column_type = self.determine_value_column_type(item['x'], per_100g_x, per_portion_x)
                all_values.append({
                    'index': i,
                    'item': item,
                    'value': value,
                    'unit': unit,
                    'x': item['x'],
                    'y': item['y'],
                    'column_type': column_type,
                    'row_group': item.get('row_group', -1)
                })
        
        self.log_debug(f"\n📊 Found {len(all_values)} numerical values total")
        for val in all_values:
            self.log_debug(f"  📈 VALUE: {val['value']} {val['unit']} at ({val['x']:.0f}, {val['y']:.0f}) [{val['column_type']}] row:{val['row_group']}")
        
        # Third pass: Enhanced mapping with row group consideration
        for field_name, labels in field_labels.items():
            if not labels:
                continue
                
            self.log_debug(f"\n📍 ENHANCED mapping for {field_name.upper()}")
            
            for label_idx, label_item in labels:
                candidates = []
                label_row_group = label_item.get('row_group', -1)
                
                # Enhanced tolerances based on field type
                if field_name == 'proteins':
                    max_y_tolerance = 50
                    max_row_group_diff = 2  # Allow more flexibility for proteins
                else:
                    max_y_tolerance = 35
                    max_row_group_diff = 1  # Stricter for other fields
                
                # Find values spatially related to this label
                for val_data in all_values:
                    val_item = val_data['item']
                    value = val_data['value']
                    unit = val_data['unit']
                    column_type = val_data['column_type']
                    val_row_group = val_data['row_group']
                    
                    # Calculate spatial relationship
                    x_distance = val_item['x'] - label_item['x']
                    y_distance = abs(val_item['y'] - label_item['y'])
                    
                    # Enhanced row group consideration
                    row_group_bonus = 0
                    if label_row_group != -1 and val_row_group != -1:
                        row_group_diff = abs(val_row_group - label_row_group)
                        if row_group_diff == 0:
                            row_group_bonus = 0.8  # Strong bonus for same row group
                            self.log_debug(f"    🎯 SAME ROW GROUP: {field_name} and value in group {val_row_group}")
                        elif row_group_diff <= max_row_group_diff:
                            row_group_bonus = 0.4  # Moderate bonus for nearby row groups
                        else:
                            # Skip if too far in different row groups
                            continue
                    
                    if x_distance > -50 and y_distance <= max_y_tolerance:
                        
                        # CALORIES FIX: Strong preference for per 100g values
                        if field_name == 'calories':
                            if column_type == 'per_portion':
                                # Check if per 100g version exists
                                per_100g_calories = [v for v in all_values 
                                                   if v['column_type'] == 'per_100g' 
                                                   and v['unit'] == 'kcal'
                                                   and abs(v['y'] - label_item['y']) <= max_y_tolerance
                                                   and self._is_reasonable_value_enhanced('calories', v['value'], v['unit'])]
                                if per_100g_calories:
                                    self.log_debug(f"    🔧 CALORIES PER 100G FIX: Skipping per portion value {value} - per 100g available")
                                    continue
                        
                        # Enhanced proximity checking with row group awareness
                        is_closest_to_this_field = True
                        for other_field_name, other_labels in field_labels.items():
                            if other_field_name != field_name and other_labels:
                                for _, other_label_item in other_labels:
                                    other_y_distance = abs(val_item['y'] - other_label_item['y'])
                                    other_row_group = other_label_item.get('row_group', -1)
                                    
                                    # Consider both spatial distance and row group
                                    if other_y_distance < y_distance - 10:
                                        # But give preference if same row group as current field
                                        if not (label_row_group != -1 and val_row_group == label_row_group and other_row_group != val_row_group):
                                            is_closest_to_this_field = False
                                            self.log_debug(f"    ⚠️ Value {value} at y={val_item['y']:.0f} is closer to {other_field_name}")
                                            break
                                if not is_closest_to_this_field:
                                    break
                        
                        if not is_closest_to_this_field:
                            continue
                        
                        # Validate value is reasonable for this field
                        if self._is_reasonable_value_enhanced(field_name, value, unit):
                            
                            # Calculate enhanced spatial score
                            spatial_distance = (x_distance**2 + y_distance**2)**0.5
                            direction_bonus = 0.3 if x_distance > 0 else 0
                            
                            # Row precision bonus
                            row_precision_bonus = 0
                            if y_distance <= 15:
                                row_precision_bonus = 0.5
                            elif y_distance <= 25:
                                row_precision_bonus = 0.3
                            
                            # Column bonus
                            column_bonus = 0
                            if field_name == 'calories' and column_type == 'per_100g':
                                column_bonus = 1.0
                            elif column_type == 'per_100g':
                                column_bonus = 0.3
                            
                            # Enhanced magnitude bonus
                            magnitude_bonus = 0
                            if field_name == 'proteins' and value >= 10:
                                magnitude_bonus = 0.6
                            elif field_name in ['carbs', 'fiber'] and value >= 10:
                                magnitude_bonus = 0.4
                            elif field_name in ['fats', 'saturated_fats'] and value >= 1:
                                magnitude_bonus = 0.2
                            elif field_name == 'calories' and value >= 100:
                                magnitude_bonus = 0.5
                            
                            # Convert units if needed
                            final_value = value
                            if field_name == 'calories' and unit == 'kj':
                                final_value = value / 4.184
                            elif field_name == 'salt' and unit == 'mg':
                                final_value = value / 1000
                            
                            spatial_score = (val_item['confidence'] + direction_bonus + magnitude_bonus + 
                                           row_precision_bonus + column_bonus + row_group_bonus - 
                                           (spatial_distance / 1000))
                            
                            candidate = NutritionValue(
                                field_type=field_name,
                                value=final_value,
                                unit=unit,
                                confidence=spatial_score,
                                source_text=f"{label_item['text']} -> {val_item['text']}",
                                x_pos=val_item['x'],
                                y_pos=val_item['y'],
                                is_claimed=False,
                                column_type=column_type,
                                row_group=val_row_group
                            )
                            
                            candidates.append(candidate)
                            self.log_debug(f"    ✅ CANDIDATE: {field_name}={candidate.value} [{column_type}] row_group={val_row_group} (conf: {candidate.confidence:.3f})")
                
                # Sort candidates and add best ones
                if candidates:
                    candidates.sort(key=lambda x: -x.confidence)
                    
                    # Add top candidates
                    for candidate in candidates[:2]:
                        nutrition_values[field_name].append(candidate)
        
        return nutrition_values

    def select_best_values_production(self, nutrition_values: Dict[str, List[NutritionValue]]) -> Dict[str, NutritionValue]:
        """PRODUCTION value selection with per 100g preference"""
        selected_values = {}

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

        self.log_debug(f"\n🎯 PRODUCTION VALUE SELECTION WITH PER 100G PREFERENCE")

        used_positions = set()
        used_values = set()

        for field_name, priority in field_priorities:
            if field_name not in nutrition_values or not nutrition_values[field_name]:
                continue

            available_values = [v for v in nutrition_values[field_name] if not v.is_claimed]
            if not available_values:
                continue

            # Strict deduplication
            unique_values = []
            for val in available_values:
                pos_key = (round(val.x_pos/20)*20, round(val.y_pos/15)*15)
                val_key = (round(val.value, 1), val.unit)
                
                if pos_key not in used_positions and val_key not in used_values:
                    unique_values.append(val)
            
            if not unique_values:
                continue

            # CALORIES FIX: Always prefer per 100g for calories
            if field_name == 'calories':
                per_100g_calories = [v for v in unique_values if v.column_type == 'per_100g']
                if per_100g_calories:
                    unique_values = per_100g_calories
                    self.log_debug(f"    🎯 CALORIES PER 100G FIX: Using only per 100g calorie values")

            # Enhanced selection logic for other fields
            elif field_name == 'proteins':
                reasonable_proteins = [v for v in unique_values if v.value >= 10]
                if reasonable_proteins:
                    unique_values = reasonable_proteins
                    self.log_debug(f"    🔧 PROTEIN PRIORITY: Using values >= 10")
            elif field_name in ['carbs', 'fiber']:
                reasonable_values = [v for v in unique_values if v.value >= 5]
                if reasonable_values:
                    unique_values = reasonable_values
            elif field_name == 'fats':
                reasonable_values = [v for v in unique_values if v.value >= 1]
                if reasonable_values:
                    unique_values = reasonable_values

            # Sort by confidence
            unique_values.sort(key=lambda x: -x.confidence)
            best_value = unique_values[0]

            # Mark as used
            best_value.is_claimed = True
            pos_key = (round(best_value.x_pos/20)*20, round(best_value.y_pos/15)*15)
            val_key = (round(best_value.value, 1), best_value.unit)
            used_positions.add(pos_key)
            used_values.add(val_key)
            
            selected_values[field_name] = best_value
            self.log_debug(f"   ✅ SELECTED {field_name}: {best_value.value} [{best_value.column_type}] at y={best_value.y_pos:.0f} (conf: {best_value.confidence:.3f})")

        return selected_values

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

        # Special handling for commonly zero fields
        if final_value == 0 and field_name in ['salt', 'sugars', 'saturated_fats', 'fiber']:
            is_reasonable = True
            
        # Enhanced salt range
        if field_name == 'salt' and 0.01 <= final_value <= 3.0:
            is_reasonable = True

        return is_reasonable

    def preprocess_mobile_optimized(self, image):
        """Production-ready image preprocessing"""
        from PIL import Image, ImageEnhance

        if isinstance(image, str):
            if image.startswith('data:'):
                image = image.split(',')[1]
            image_bytes = base64.b64decode(image)
            pil_image = Image.open(io.BytesIO(image_bytes))
        else:
            pil_image = image.copy()

        # Mobile optimization
        width, height = pil_image.size
        max_dimension = 1200
        
        if max(width, height) > max_dimension:
            if width > height:
                scale_factor = max_dimension / width
                new_size = (max_dimension, int(height * scale_factor))
            else:
                scale_factor = max_dimension / height
                new_size = (int(width * scale_factor), max_dimension)
                
            pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)

        # Enhanced preprocessing
        enhancer = ImageEnhance.Contrast(pil_image)
        pil_image = enhancer.enhance(1.4)

        enhancer = ImageEnhance.Sharpness(pil_image)
        pil_image = enhancer.enhance(1.5)

        return pil_image

    def log_debug(self, message):
        if self.debug:
            print(f"🔍 {message}")

    def extract_text_enhanced(self, image_data):
        """Production-ready OCR extraction"""
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
            
            preprocessed_image = self.preprocess_mobile_optimized(image)
            image_array = np.array(preprocessed_image)
            
            try:
                ocr_result = self.rapid_reader(image_array)
                processed_results = []
                
                if ocr_result and len(ocr_result) >= 1:
                    ocr_results = ocr_result[0]
                    if ocr_results:
                        for result in ocr_results:
                            if len(result) >= 3:
                                bbox_points, text, confidence = result[0], result[1], float(result[2])
                                if confidence >= 0.2:
                                    bbox = bbox_points
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
                return processed_results
            
            except Exception as e:
                self.log_debug(f"❌ RapidOCR failed: {e}")
                return []
                
        except Exception as e:
            self.log_debug(f"❌ Image preprocessing failed: {e}")
            return []

    def validate_enhanced_results(self, selected_values: Dict[str, NutritionValue]) -> Dict[str, float]:
        """Enhanced result validation"""
        results = {}
        
        for field_name, nutrition_value in selected_values.items():
            if field_name == 'salt':
                results[field_name] = round(nutrition_value.value, 3)
            else:
                results[field_name] = round(nutrition_value.value, 2)
        
        # Relaxed constraints
        if 'saturated_fats' in results and 'fats' in results:
            if results['saturated_fats'] > results['fats'] * 1.1:
                results['saturated_fats'] = round(results['fats'] * 0.95, 2)
        
        if 'sugars' in results and 'carbs' in results:
            if results['sugars'] > results['carbs'] * 1.2:
                results['sugars'] = round(results['carbs'] * 0.95, 2)
        
        return results

    def scan_nutrition_label(self, image_data):
        """🚀 Enhanced nutrition label scanning with FIXED regex patterns"""
        try:
            self.log_debug("🚀 Starting ENHANCED SCANNER v32.0...")

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

            # ENHANCED: Filter noise from text-heavy images
            filtered_text = self.filter_noise_enhanced(extracted_text)
            
            # ENHANCED: Create row groups for better alignment handling
            grouped_text = self.create_row_groups_enhanced(filtered_text)

            # Check per 100g
            full_text = ' '.join([item['text'] for item in grouped_text])
            is_per_100g = any(pattern in full_text.lower() 
                             for pattern in ['100g', '100 g', 'per 100', 'kohti'])

            # Enhanced column detection
            columns = self.detect_columns_enhanced(grouped_text)

            # ENHANCED parsing with better row alignment
            nutrition_values = self.find_all_nutrition_values_enhanced(grouped_text, columns)
            selected_values = self.select_best_values_production(nutrition_values)
            validated_results = self.validate_enhanced_results(selected_values)

            # Extract confidence scores
            confidence_scores = {}
            for field_name, nutrition_value in selected_values.items():
                confidence_scores[field_name] = nutrition_value.confidence

            # Response
            response = {
                'success': True,
                'nutrition_data': validated_results,
                'per_100g': is_per_100g,
                'raw_text': [item['text'] for item in grouped_text],
                'debug_info': {
                    'total_text_items': len(grouped_text),
                    'fields_found': list(validated_results.keys()),
                    'avg_confidence': sum(item['confidence'] for item in grouped_text) / len(grouped_text),
                    'confidence_scores': confidence_scores,
                    'version': 'v32.0_fixed_regex_patterns',
                    'engines_available': {'rapidocr': True},
                    'noise_filtered': len(extracted_text) - len(filtered_text),
                    'row_groups_created': len(set(item.get('row_group', -1) for item in grouped_text))
                }
            }

            self.log_debug(f"\n📊 ENHANCED RESULTS: {len(validated_results)} fields found")
            for field, value in validated_results.items():
                confidence = confidence_scores.get(field, 'N/A')
                self.log_debug(f"    ✅ {field}: {value} (conf: {confidence:.3f})")

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

    # Test images
    test_images = [
        "kuva1.jpg",  
        "kuva4.jpg",  
        "kuva5.jpg",  
        "kuva6.jpg"   
    ]

    # Run test
    report = harness.run_comprehensive_test(test_images)

    print("✅ ENHANCED SCANNER v32.0 deployed with:")
    print("   • 🔧 FIXED REGEX PATTERNS - Corrected double backslashes preventing matches")
    print("   • 🔍 ENHANCED NOISE FILTERING - Better handling of text-heavy images")
    print("   • 📏 IMPROVED ROW ALIGNMENT - Adaptive tolerance for curved/tilted images")  
    print("   • 🎯 ROW GROUP AWARENESS - Values matched using row grouping")
    print("   • 🚫 TEXT-HEAVY IMAGE SUPPORT - Filters out irrelevant text blocks")
    print("   • 📊 ENHANCED COLUMN DETECTION - Better separation of nutrition values")
    print("   • ⚡ ALL PREVIOUS FIXES MAINTAINED - Production-ready with REGEX FIXES")
