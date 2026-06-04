"""
Gemini Provider - API wrapper for Google Gemini 2.5 Flash
"""

import os
import logging
from typing import Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Wrapper around Google Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini provider"""
        if not genai:
            raise ImportError("google-generativeai package required. Install with: pip install google-generativeai")
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from file"""
        prompt_file = "/Users/bthomas/Documents/pureleven_dev/PURELEVEN_CHATBOT_SYSTEM_PROMPT.txt"
        try:
            with open(prompt_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"System prompt file not found: {prompt_file}")
            return "You are a helpful AI assistant for Pureleven, a Kerala spices business."
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            response = self.model.count_tokens(text)
            return response.total_tokens
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Rough estimate: ~1 token per 4 characters
            return len(text) // 4
    
    def generate_response(
        self,
        message: str,
        context: Optional[dict] = None,
        language: str = "english"
    ) -> tuple[str, int]:
        """
        Generate response using Gemini
        
        Returns:
            (response_text, tokens_used)
        """
        try:
            # Build context for Gemini
            products_context = ""
            kb_context = ""
            
            if context:
                if 'products' in context and context['products']:
                    products = context['products']
                    products_context = "\n\nAvailable products:\n"
                    for p in products[:10]:  # Limit to 10 products
                        products_context += f"- {p.get('name', 'Unknown')}: ₹{p.get('price_inr', 0)} (Stock: {p.get('stock', 0)})\n"
                
                if 'kb' in context and context['kb']:
                    kb = context['kb']
                    kb_context = "\n\nRelevant information:\n"
                    for item in kb[:5]:  # Limit to 5 KB items
                        kb_context += f"Q: {item.get('question', 'N/A')}\nA: {item.get('answer', 'N/A')}\n\n"
            
            # Prepare messages for Gemini
            full_context = f"{self.system_prompt}{products_context}{kb_context}"
            
            # Use chat interface
            chat = self.model.start_chat(history=[])
            
            response = chat.send_message(
                f"{full_context}\n\nCustomer message: {message}",
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_output_tokens": 256,
                }
            )
            
            response_text = response.text if response.text else "I couldn't generate a response. Please try again."
            tokens_used = self.count_tokens(message + response_text)
            
            return response_text, tokens_used
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    def estimate_cost(self, tokens_used: int) -> float:
        """Estimate cost in USD for tokens used"""
        # Gemini 2.5 Flash pricing (as of June 2026):
        # Input: $0.075 per 1M tokens
        # Output: $0.3 per 1M tokens
        # Rough average: $0.1 per 1M tokens
        cost_per_token = 0.0000001  # $0.0000001 per token
        return tokens_used * cost_per_token
