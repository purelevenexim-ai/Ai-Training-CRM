"""
Rule Engine - Multi-language intent detection
Detects customer intent from English, Malayalam, and Manglish messages
"""

import re
from typing import Tuple
from enum import Enum


class Language(str, Enum):
    """Supported languages"""
    ENGLISH = "english"
    MALAYALAM = "malayalam"
    MANGLISH = "manglish"
    MIXED = "mixed"


class Intent(str, Enum):
    """Customer intent types"""
    PRICE_INQUIRY = "PRICE_INQUIRY"
    SHIPPING_INQUIRY = "SHIPPING_INQUIRY"
    COD_INQUIRY = "COD_INQUIRY"
    TRACKING_INQUIRY = "TRACKING_INQUIRY"
    PURCHASE = "PURCHASE"
    COMPLAINT = "COMPLAINT"
    GENERAL = "GENERAL"


class RuleEngine:
    """Multi-language intent detection using keyword rules"""
    
    def __init__(self):
        """Initialize keyword patterns for each language and intent"""
        
        # English patterns
        self.english_patterns = {
            Intent.PRICE_INQUIRY: [
                r'\bprice\b', r'\bcost\b', r'\brate\b', r'\bhow\s+much\b',
                r'\bcost\s+how\s+much\b', r'\bhow\s+much\s+will\b',
                r'\bwhat\s+is\s+the\s+price\b', r'\bpricing\b'
            ],
            Intent.SHIPPING_INQUIRY: [
                r'\bdelivery\b', r'\bshipping\b', r'\bwhen\s+will\s+it\s+arrive\b',
                r'\bhow\s+long\b', r'\bshipping\s+time\b', r'\bdelivery\s+time\b',
                r'\bfree\s+shipping\b', r'\bshipping\s+charge\b'
            ],
            Intent.COD_INQUIRY: [
                r'\bcod\b', r'\bcash\s+on\s+delivery\b', r'\bpay\s+on\s+delivery\b',
                r'\bpayment\s+method\b', r'\bcan\s+i\s+pay\b'
            ],
            Intent.TRACKING_INQUIRY: [
                r'\btrack\b', r'\bwhere\s+is\s+my\s+order\b', r'\border\s+status\b',
                r'\btracking\s+number\b', r'\btracking\s+id\b'
            ],
            Intent.PURCHASE: [
                r'\bplace\s+order\b', r'\bbuy\b', r'\border\s+now\b',
                r'\bhow\s+to\s+order\b', r'\bwant\s+to\s+buy\b', r'\bread\s+to\s+order\b',
                r'\bpurchase\b'
            ],
            Intent.COMPLAINT: [
                r'\bnot\s+received\b', r'\bnot\s+happy\b', r'\bcomplain\b',
                r'\bwrong\s+product\b', r'\bdamaged\b', r'\brefund\b',
                r'\breturn\b', r'\bquality\s+issue\b'
            ]
        }
        
        # Malayalam patterns (transliterated + script)
        self.malayalam_patterns = {
            Intent.PRICE_INQUIRY: [
                r'\bvila\b', r'\bvilamenu\b', r'\bethra\b', r'\brice\b',
                r'\bvilaethram\b', r'\bvila\s+ethra\b',
                r'വില', r'എത്ര', r'വില കാണും', r'ദരം'
            ],
            Intent.SHIPPING_INQUIRY: [
                r'\bdelivery\b', r'\bdithanam\b', r'\bfree\s+diksha\b',
                r'\bhow\s+many\s+days\b', r'\bdivasam\b',
                r'ഡെലിവറി', r'കിട്ടാൻ', r'എത്ര നാൾ'
            ],
            Intent.COD_INQUIRY: [
                r'\bcod\b', r'\bcash\b', r'\bpay\b', r'\bmode\b',
                r'കാശ്', r'കൊടുക്കാം', r'പേയ്'
            ],
            Intent.PURCHASE: [
                r'\bcheyyan\b', r'\bcheyyanam\b', r'\border\s+cheyyan\b',
                r'\bvenam\b', r'\bwant\b',
                r'ചെയ്യാം', r'വേണം', r'പോകും'
            ],
            Intent.COMPLAINT: [
                r'\bnot\s+received\b', r'\bkittiyilla\b', r'\bproblem\b',
                r'\bbad\b', r'\bwrong\b',
                r'കിട്ടിയില്ല', r'പ്രശ്നം', r'തെറ്റ്'
            ]
        }
        
        # Manglish (English + Malayalam mixed) patterns
        self.manglish_patterns = {
            Intent.PRICE_INQUIRY: [
                r'\bvila\b', r'\bethra\b', r'\brate\s+vila\b', r'\bcost\s+vila\b',
                r'\bvila\s+ethra\b', r'\bkoski\s+vila\b', r'\bvilamenu\b'
            ],
            Intent.SHIPPING_INQUIRY: [
                r'\bdithanam\b', r'\bdelivery\s+undo\b', r'\bkitti\s+enna\s+divasam\b',
                r'\bfree\s+diksha\b', r'\bethram\s+naal\b'
            ],
            Intent.COD_INQUIRY: [
                r'\bcod\s+aano\b', r'\bcash\s+pay\b', r'\bmode\s+nee\b',
                r'\bkittum\s+aano\b'
            ],
            Intent.PURCHASE: [
                r'\bcheyyan\b', r'\bordernum\b', r'\bvenam\s+order\b',
                r'\bplacecheyyan\b'
            ]
        }
    
    def detect_language(self, text: str) -> Tuple[Language, float]:
        """
        Detect language of customer message
        Returns: (language, confidence)
        """
        text_lower = text.lower()
        
        # Count Malayalam script characters
        malayalam_script_count = len(re.findall(r'[\u0D00-\u0D7F]', text))
        
        # If significant Malayalam script, it's Malayalam
        if malayalam_script_count > 2:
            confidence = min(0.99, 0.6 + (malayalam_script_count * 0.1))
            return Language.MALAYALAM, confidence
        
        # Check for transliterated Malayalam keywords
        manglish_keywords = [
            'vila', 'ethra', 'venam', 'aano', 'cheyyan', 'kitti',
            'dithanam', 'divasam', 'kozhikuttam', 'undo'
        ]
        manglish_count = sum(1 for kw in manglish_keywords if f' {kw} ' in f' {text_lower} ')
        
        # Check for English
        english_keywords = [
            'price', 'delivery', 'order', 'shipping', 'payment',
            'refund', 'return', 'cod', 'tracking'
        ]
        english_count = sum(1 for kw in english_keywords if f' {kw} ' in f' {text_lower} ')
        
        # Determine language
        if manglish_count > 0 and english_count > 0:
            return Language.MIXED, 0.7
        elif manglish_count >= 2:
            return Language.MANGLISH, 0.85
        elif english_count >= 2:
            return Language.ENGLISH, 0.9
        elif manglish_count > 0:
            return Language.MANGLISH, 0.6
        else:
            # Default to English if unclear
            return Language.ENGLISH, 0.5
    
    def detect_intent(self, text: str, language: Language = None) -> Tuple[Intent, float]:
        """
        Detect customer intent from message
        Returns: (intent, confidence)
        """
        if language is None:
            language, _ = self.detect_language(text)
        
        text_lower = text.lower()
        scores = {}
        
        # Select patterns based on language
        if language == Language.ENGLISH:
            patterns = self.english_patterns
        elif language == Language.MALAYALAM:
            patterns = self.malayalam_patterns
        elif language == Language.MANGLISH:
            patterns = self.manglish_patterns
        else:  # MIXED
            # Combine patterns for mixed language
            patterns = self.english_patterns.copy()
            for intent, pattern_list in self.malayalam_patterns.items():
                if intent in patterns:
                    patterns[intent].extend(pattern_list)
        
        # Score each intent
        for intent, pattern_list in patterns.items():
            matches = 0
            for pattern in pattern_list:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    matches += 1
            scores[intent] = matches
        
        # Find highest scoring intent
        if max(scores.values()) == 0:
            return Intent.GENERAL, 0.3
        
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        
        # Calculate confidence (0-1)
        # More keyword matches = higher confidence
        confidence = min(0.99, 0.5 + (best_score * 0.25))
        
        return best_intent, confidence
    
    def should_use_gemini(self, intent_confidence: float, threshold: float = 0.70) -> bool:
        """
        Determine if we should call Gemini for this message
        Rule engine is confident enough (>70%) = don't call Gemini
        """
        return intent_confidence < threshold
