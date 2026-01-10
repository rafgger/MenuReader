"""
Menu Parser Service for Menu Image Analyzer.

This module provides functionality to parse OCR-extracted text and identify
individual dishes with their prices and descriptions.
"""

import re
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from app.models.data_models import ParsedDish, OCRResult


logger = logging.getLogger(__name__)


class MenuParser:
    """
    Service for parsing menu text and extracting dish information.
    
    Identifies dishes, prices, and descriptions from OCR-extracted text
    using pattern matching and heuristic analysis.
    """
    
    def __init__(self):
        """Initialize the menu parser with pattern configurations."""
        # Common price patterns across different currencies and formats
        self.price_patterns = [
            r'\$\d+(?:\.\d{2})?',  # $12.99, $12
            r'€\d+(?:[.,]\d{2})?',  # €12.99, €12,99
            r'£\d+(?:\.\d{2})?',  # £12.99
            r'¥\d+',  # ¥1200
            r'\d+(?:[.,]\d{2})?\s*(?:USD|EUR|GBP|CAD|AUD)',  # 12.99 USD
            r'\d+(?:[.,]\d{2})?\s*(?:dollars?|euros?|pounds?)',  # 12.99 dollars
            r'\d+(?:[.,]\d{2})?',  # 12.99 (fallback for numbers)
        ]
        
        # Patterns to identify menu sections to skip
        self.skip_patterns = [
            r'(?i)^(?:appetizers?|starters?|salads?|soups?|mains?|entrees?|desserts?|drinks?|beverages?)$',
            r'(?i)^(?:menu|today\'s special|chef\'s recommendation)$',
            r'(?i)^(?:hours?|phone|address|website).*',
            r'^\s*[-=_]{3,}\s*$',  # Separator lines
        ]
        
        # Common dish name indicators
        self.dish_indicators = [
            r'(?i)\b(?:with|served|topped|grilled|fried|baked|roasted|steamed)\b',
            r'(?i)\b(?:chicken|beef|pork|fish|salmon|tuna|shrimp|vegetarian|vegan)\b',
            r'(?i)\b(?:pasta|pizza|burger|sandwich|salad|soup|rice|noodles)\b',
        ]
        
        # Minimum confidence threshold for extracted dishes
        self.min_confidence = 0.3
    
    def parse_dishes(self, ocr_result: OCRResult) -> List[ParsedDish]:
        """
        Parse OCR text to extract dishes and their information.
        
        Args:
            ocr_result: OCR result containing extracted text
            
        Returns:
            List of ParsedDish objects with extracted information
        """
        if not ocr_result.text or not ocr_result.text.strip():
            logger.warning("Empty OCR text provided for parsing")
            return []
        
        try:
            # Split text into lines and clean them
            lines = self._clean_and_split_text(ocr_result.text)
            
            # Extract potential dish entries
            dish_candidates = self._extract_dish_candidates(lines)
            
            # Parse each candidate for dish information
            parsed_dishes = []
            for candidate in dish_candidates:
                dish = self._parse_dish_candidate(candidate, ocr_result.confidence)
                if dish and dish.confidence >= self.min_confidence:
                    parsed_dishes.append(dish)
            
            logger.info(f"Parsed {len(parsed_dishes)} dishes from {len(lines)} text lines")
            return parsed_dishes
            
        except Exception as e:
            logger.error(f"Error parsing dishes from OCR text: {str(e)}")
            return []
    
    def _clean_and_split_text(self, text: str) -> List[str]:
        """
        Clean and split OCR text into processable lines.
        
        Args:
            text: Raw OCR text
            
        Returns:
            List of cleaned text lines
        """
        # Split by newlines and clean each line
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove extra whitespace
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip lines that match skip patterns
            if any(re.match(pattern, line) for pattern in self.skip_patterns):
                continue
            
            # Remove common OCR artifacts
            line = re.sub(r'[|]{2,}', '', line)  # Multiple pipes
            line = re.sub(r'[-_]{5,}', '', line)  # Long separators
            line = re.sub(r'\s{3,}', ' ', line)  # Multiple spaces
            
            if line.strip():
                cleaned_lines.append(line.strip())
        
        return cleaned_lines
    
    def _extract_dish_candidates(self, lines: List[str]) -> List[str]:
        """
        Extract lines that are likely to contain dish information.
        
        Args:
            lines: List of cleaned text lines
            
        Returns:
            List of candidate dish lines
        """
        candidates = []
        
        for line in lines:
            # Skip very short lines (likely not dishes)
            if len(line) < 3:
                continue
            
            # Skip lines that are only numbers or prices
            if re.match(r'^\s*[\d.,\$€£¥]+\s*$', line):
                continue
            
            # Look for lines with dish indicators or price patterns
            has_dish_indicator = any(re.search(pattern, line) for pattern in self.dish_indicators)
            has_price = any(re.search(pattern, line) for pattern in self.price_patterns)
            
            # Include lines that have dish indicators or prices, or are reasonable length
            if has_dish_indicator or has_price or (5 <= len(line) <= 100):
                candidates.append(line)
        
        return candidates
    
    def _parse_dish_candidate(self, line: str, base_confidence: float) -> Optional[ParsedDish]:
        """
        Parse a candidate line to extract dish information.
        
        Args:
            line: Text line to parse
            base_confidence: Base confidence from OCR
            
        Returns:
            ParsedDish object or None if parsing fails
        """
        try:
            # Extract price from the line
            price, price_confidence = self._extract_price(line)
            
            # Extract dish name (text without price)
            dish_name = self._extract_dish_name(line, price)
            
            if not dish_name or len(dish_name.strip()) < 2:
                return None
            
            # Extract any description
            description = self._extract_description(line, dish_name, price)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(
                dish_name, price, description, base_confidence, price_confidence
            )
            
            return ParsedDish(
                name=dish_name.strip(),
                price=price.strip() if price else "",
                description=description.strip() if description else None,
                confidence=confidence
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse dish candidate '{line}': {str(e)}")
            return None
    
    def _extract_price(self, line: str) -> Tuple[str, float]:
        """
        Extract price from a text line.
        
        Args:
            line: Text line to search
            
        Returns:
            Tuple of (price_string, confidence)
        """
        for pattern in self.price_patterns:
            matches = re.findall(pattern, line)
            if matches:
                # Return the last match (usually the price at the end)
                price = matches[-1]
                confidence = 0.9 if any(symbol in price for symbol in ['$', '€', '£', '¥']) else 0.6
                return price, confidence
        
        return "", 0.0
    
    def _extract_dish_name(self, line: str, price: str) -> str:
        """
        Extract dish name by removing price and cleaning up.
        
        Args:
            line: Original text line
            price: Extracted price string
            
        Returns:
            Cleaned dish name
        """
        dish_name = line
        
        # Remove price from the line
        if price:
            # Escape special regex characters in price
            escaped_price = re.escape(price)
            dish_name = re.sub(escaped_price, '', dish_name)
        
        # Remove common separators and dots at the end
        dish_name = re.sub(r'\.{2,}.*$', '', dish_name)  # Remove dotted lines
        dish_name = re.sub(r'-{2,}.*$', '', dish_name)   # Remove dashed lines
        dish_name = re.sub(r'_{2,}.*$', '', dish_name)   # Remove underscored lines
        
        # Clean up extra whitespace and punctuation
        dish_name = re.sub(r'\s+', ' ', dish_name)
        dish_name = dish_name.strip(' .-_')
        
        return dish_name
    
    def _extract_description(self, line: str, dish_name: str, price: str) -> Optional[str]:
        """
        Extract description from the line after removing dish name and price.
        
        Args:
            line: Original text line
            dish_name: Extracted dish name
            price: Extracted price
            
        Returns:
            Description text or None
        """
        # Start with the original line
        remaining = line
        
        # Remove dish name and price
        if dish_name:
            remaining = remaining.replace(dish_name, '', 1)
        if price:
            remaining = remaining.replace(price, '', 1)
        
        # Clean up the remaining text
        remaining = re.sub(r'\.{2,}', '', remaining)  # Remove dotted separators
        remaining = re.sub(r'-{2,}', '', remaining)   # Remove dashed separators
        remaining = re.sub(r'\s+', ' ', remaining)    # Normalize whitespace
        remaining = remaining.strip(' .-_')
        
        # Return description if it's substantial enough
        if remaining and len(remaining) > 5:
            return remaining
        
        return None
    
    def _calculate_confidence(self, dish_name: str, price: str, description: Optional[str],
                            base_confidence: float, price_confidence: float) -> float:
        """
        Calculate confidence score for the parsed dish.
        
        Args:
            dish_name: Extracted dish name
            price: Extracted price
            description: Extracted description
            base_confidence: OCR confidence
            price_confidence: Price extraction confidence
            
        Returns:
            Overall confidence score (0.0 to 1.0)
        """
        confidence = base_confidence * 0.4  # Start with OCR confidence
        
        # Boost confidence for having a price
        if price:
            confidence += price_confidence * 0.3
        
        # Boost confidence for dish indicators
        dish_name_lower = dish_name.lower()
        if any(re.search(pattern, dish_name_lower) for pattern in self.dish_indicators):
            confidence += 0.2
        
        # Boost confidence for reasonable dish name length
        if 5 <= len(dish_name) <= 50:
            confidence += 0.1
        
        # Small boost for having a description
        if description:
            confidence += 0.05
        
        # Ensure confidence is within bounds
        return min(max(confidence, 0.0), 1.0)
    
    def get_parsing_statistics(self, dishes: List[ParsedDish]) -> Dict[str, Any]:
        """
        Get statistics about the parsing results.
        
        Args:
            dishes: List of parsed dishes
            
        Returns:
            Dictionary with parsing statistics
        """
        if not dishes:
            return {
                'total_dishes': 0,
                'dishes_with_prices': 0,
                'dishes_with_descriptions': 0,
                'average_confidence': 0.0,
                'confidence_distribution': {}
            }
        
        dishes_with_prices = sum(1 for dish in dishes if dish.price)
        dishes_with_descriptions = sum(1 for dish in dishes if dish.description)
        average_confidence = sum(dish.confidence for dish in dishes) / len(dishes)
        
        # Confidence distribution
        confidence_ranges = {'low': 0, 'medium': 0, 'high': 0}
        for dish in dishes:
            if dish.confidence < 0.5:
                confidence_ranges['low'] += 1
            elif dish.confidence < 0.8:
                confidence_ranges['medium'] += 1
            else:
                confidence_ranges['high'] += 1
        
        return {
            'total_dishes': len(dishes),
            'dishes_with_prices': dishes_with_prices,
            'dishes_with_descriptions': dishes_with_descriptions,
            'average_confidence': round(average_confidence, 3),
            'confidence_distribution': confidence_ranges
        }