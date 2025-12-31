import re
import os
import cv2
import csv
import numpy as np
import pillow_heif
from PIL import Image
from dateutil import parser
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from sentence_transformers import SentenceTransformer, util
from .utils import load_config

class OCREngine:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.model = self._load_ocr_model()
        self.sentence_model = SentenceTransformer('bert-base-nli-mean-tokens')
    
    def _load_ocr_model(self):
        """Load OCR model with configuration"""
        ocr_config = self.config['ocr']
        return ocr_predictor(
            det_arch=ocr_config['det_arch'],
            reco_arch=ocr_config['reco_arch'],
            pretrained=ocr_config['pretrained']
        )
    
    def perform_ocr(self, img):
        """Perform OCR on image and return text list"""
        result = self.model(img)
        output = result.export()
        
        text_list = []
        for obj1 in output['pages'][0]["blocks"]:
            for obj2 in obj1["lines"]:
                for obj3 in obj2["words"]:
                    text_list.append(obj3['value'])
        return text_list
    
    def divide_image(self, image_path):
        """Divide image in half and return lower half"""
        original_image = cv2.imread(image_path)
        height, width, _ = original_image.shape
        midpoint_y = height // 2
        lower_half = original_image[midpoint_y:height, :]
        return np.asarray(lower_half)
    
    def read_heic(self, file_path):
        """Read HEIC file and convert to numpy array"""
        try:
            import gc
            from PIL import Image
            pillow_heif.register_heif_opener()
            
            print(f"Processing HEIC: {file_path}")
            
            # Force garbage collection before processing
            gc.collect()
            
            with Image.open(file_path) as image:
                # Aggressively resize to manage memory - smaller size
                max_size = 1200
                if image.size[0] > max_size or image.size[1] > max_size:
                    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert to RGB with lower quality to save memory
                rgb_image = image.convert('RGB')
                
                # Convert to numpy array
                result = np.asarray(rgb_image, dtype=np.uint8)
                
                # Clear intermediate variables
                del rgb_image
                
            # Force garbage collection after processing
            gc.collect()
            print(f"Successfully processed HEIC (size: {result.shape})")
            return result
            
        except (OSError, MemoryError) as e:
            print(f"Memory/OS error reading HEIC file {file_path}: {e}")
            import gc
            gc.collect()
            return None
        except Exception as e:
            print(f"Error reading HEIC file {file_path}: {e}")
            import gc
            gc.collect()
            return None
    
    def find_similar_words(self, ocr_output, comparison_word):
        """Find most similar word using sentence transformers"""
        comparison_embedding = self.sentence_model.encode(comparison_word, convert_to_tensor=True)
        ocr_embeddings = self.sentence_model.encode(ocr_output, convert_to_tensor=True)
        
        similarities = util.pytorch_cos_sim(comparison_embedding, ocr_embeddings)[0].tolist()
        max_similarity_index = similarities.index(max(similarities))
        
        most_similar_word = ocr_output[max_similarity_index]
        similarity_score = similarities[max_similarity_index]
        
        return most_similar_word, similarity_score
    
    def extract_amount(self, input_list):
        """Extract maximum numeric value from text list"""
        numeric_pattern = r"[-+]?\d*\.\d+|\d+"
        all_numeric_values = []
        
        for element in input_list:
            numeric_values = re.findall(numeric_pattern, str(element))
            all_numeric_values.extend(map(float, numeric_values))
        
        return max(all_numeric_values, default=None)
    
    def extract_emp_code(self, data):
        """Extract employee code from OCR data"""
        emp_code_pattern = re.compile(r'(?i)(TGLP|TGZM|GZM|GLP|TGM|TGP)\w+')
        
        for item in data:
            match = emp_code_pattern.match(item)
            if match:
                return match.group()
        return ""
    
    def extract_date(self, text_list):
        """Extract date from OCR text"""
        ocr_text = ' '.join(text_list)
        date_pattern = re.compile(r'\b(\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|\d{1,2}[-/]?\w{3,}-?\d{2,4})\b', re.IGNORECASE)
        matches = date_pattern.findall(ocr_text)
        
        for match in matches:
            try:
                # Fix OCR errors: 0 -> O
                fixed_match = match.replace('0ct', 'Oct').replace('0ec', 'Dec').replace('0ov', 'Nov')
                parsed_date = parser.parse(fixed_match, fuzzy=True)
                return parsed_date.strftime('%d-%b-%Y')
            except ValueError:
                print(f"Error parsing date: {match}")
        
        return None
    
    def identify_meal_type(self, text_list):
        """Identify meal type from OCR text"""
        # Check for Special Packed M
        meal1, conf1 = self.find_similar_words(text_list, 'Special')
        meal2, conf2 = self.find_similar_words(text_list, 'Packed')
        meal3, conf3 = self.find_similar_words(text_list, 'M')
        
        if conf1 > 0.90 and conf2 > 0.90 and conf3 > 0.80:
            return 'Special Packed M'
        
        # Check for Special Veg Thali
        veg, veg_conf = self.find_similar_words(text_list, 'Veg')
        thali, thali_conf = self.find_similar_words(text_list, 'Thali')
        
        if conf1 > 0.90 and veg_conf > 0.90 and thali_conf > 0.80:
            return 'Special Veg Thali'
        
        # Check for Special Non Veg Thali
        non_veg, non_veg_conf = self.find_similar_words(text_list, 'Non veg')
        
        if conf1 > 0.90 and non_veg_conf > 0.85 and thali_conf > 0.80:
            return 'Special Non Veg Thali'
        
        return ''
    
    def identify_company(self, text_list):
        """Identify company from OCR text"""
        com1, conf1 = self.find_similar_words(text_list, 'grazitti')
        com2, conf2 = self.find_similar_words(text_list, 'intractive')
        
        if conf1 > 0.90:
            return 'Grazitti Intractive'
        elif conf2 > 0.95 and conf1 > 0.80:
            return 'Grazitti Intractive'
        elif conf2 < 0.80 and conf1 > 0.90:
            return com1 + ' ' + com2
        
        return ''
    
    def process_image(self, image_path, logger=None):
        """Process single image and extract all information"""
        try:
            if logger:
                logger.info(f"Processing image: {image_path}")
            
            # Handle HEIC format
            if image_path.lower().endswith('.heic'):
                image_array = self.read_heic(image_path)
                if image_array is None:
                    if logger:
                        logger.error(f"Failed to read HEIC file: {image_path}")
                    return None
                
                full_text = self.perform_ocr([image_array])
                
                height, width, _ = image_array.shape
                midpoint_y = height // 2
                half_img = image_array[midpoint_y:height, :]
                half_text = self.perform_ocr([half_img])
            else:
                # Handle other formats
                img = DocumentFile.from_images(image_path)
                full_text = self.perform_ocr(img)
                
                half_img = self.divide_image(image_path)
                half_text = self.perform_ocr([half_img])
            
            if logger:
                logger.info('-------------')
                logger.info(f"Image path: {image_path}")
                logger.info(f"OCR result: {half_text}")
            
            # Extract information
            date = self.extract_date(full_text)
            emp_code = self.extract_emp_code(full_text)
            amount = self.extract_amount(half_text)
            company = self.identify_company(full_text)
            meal = self.identify_meal_type(full_text)
            
            if logger:
                logger.info(f"Date: {date}")
                logger.info(f"EMP Code: {emp_code}")
                logger.info(f"Company: {company}")
                logger.info(f"Meal: {meal}")
                logger.info(f"Amount: {amount}")
                logger.info(full_text)
            
            return {
                'Date': date,
                'Code': emp_code,
                'Amount': amount,
                'Company': company,
                'Meal': meal,
                'Image_name': image_path
            }
            
        except Exception as e:
            if logger:
                logger.error(f"Error processing image {image_path}: {e}")
            return None
    
    def save_to_csv(self, data_dict, file_path):
        """Save dictionary to CSV file"""
        file_exists = os.path.exists(file_path)
        
        with open(file_path, 'a', newline='') as csv_file:
            fieldnames = list(data_dict.keys())
            csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            
            if not file_exists:
                csv_writer.writeheader()
            
            csv_writer.writerow(data_dict)