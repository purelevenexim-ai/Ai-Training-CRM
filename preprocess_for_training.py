#!/usr/bin/env python3
"""
AI Training Data Preprocessor

Convert Wabis chat history to format required by different AI platforms:
- OpenAI (fine-tuning format)
- Anthropic Claude (prompt/completion pairs)
- HuggingFace (conversation format)
- Generic (for custom models)

Usage:
    python3 preprocess_for_training.py --format openai --input wabis_chats.jsonl
"""

import json
import argparse
from pathlib import Path
from typing import Generator, Any
from datetime import datetime
import re


class ChatPreprocessor:
    """Convert Wabis chats to AI training format."""

    @staticmethod
    def read_jsonl(file_path: str) -> Generator[dict[str, Any], None, None]:
        """Read JSONL file and yield conversations."""
        with open(file_path) as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove control characters but keep emojis
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        return text

    def to_openai_format(self, input_file: str, output_file: str, max_chats: int = 10000):
        """
        Convert to OpenAI fine-tuning format.
        
        Format:
        {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
        {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
        """
        print(f"Converting to OpenAI format: {output_file}")
        
        count = 0
        with open(output_file, 'w') as out_f:
            for conv in self.read_jsonl(input_file):
                if count >= max_chats:
                    break
                
                messages = conv.get('messages', [])
                if len(messages) < 2:
                    continue  # Skip conversations with <2 messages
                
                # Build message pairs
                openai_messages = []
                for msg in messages:
                    sender = msg.get('sender', '')
                    content = self.clean_text(msg.get('content', ''))
                    
                    if not content:
                        continue
                    
                    # Determine role (simplified: odd=user, even=assistant)
                    # In reality, you'd want to identify who is the bot
                    role = "assistant" if "+bot" in sender.lower() or "pureleven" in sender.lower() else "user"
                    
                    openai_messages.append({
                        "role": role,
                        "content": content
                    })
                
                # Only include if we have at least one exchange
                if len(openai_messages) >= 2:
                    out_f.write(json.dumps({"messages": openai_messages}) + '\n')
                    count += 1
        
        print(f"✓ Converted {count} conversations to OpenAI format")
        return output_file

    def to_anthropic_format(self, input_file: str, output_file: str, max_chats: int = 10000):
        """
        Convert to Anthropic format.
        
        Format for Claude fine-tuning:
        {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
        """
        print(f"Converting to Anthropic format: {output_file}")
        
        # Anthropic uses similar format to OpenAI
        return self.to_openai_format(input_file, output_file, max_chats)

    def to_huggingface_format(self, input_file: str, output_file: str, max_chats: int = 10000):
        """
        Convert to HuggingFace conversational format.
        
        Format:
        {
          "id": "conv_1",
          "conversation": [
            {"role": "user", "text": "..."},
            {"role": "bot", "text": "..."}
          ]
        }
        """
        print(f"Converting to HuggingFace format: {output_file}")
        
        count = 0
        with open(output_file, 'w') as out_f:
            for conv in self.read_jsonl(input_file):
                if count >= max_chats:
                    break
                
                conv_id = conv.get('conversation_id', f'conv_{count}')
                messages = conv.get('messages', [])
                
                if len(messages) < 2:
                    continue
                
                hf_messages = []
                for msg in messages:
                    content = self.clean_text(msg.get('content', ''))
                    if not content:
                        continue
                    
                    # Determine role
                    sender = msg.get('sender', '')
                    role = 'bot' if "+bot" in sender.lower() or "pureleven" in sender.lower() else 'user'
                    
                    hf_messages.append({
                        "role": role,
                        "text": content
                    })
                
                if len(hf_messages) >= 2:
                    out_f.write(json.dumps({
                        "id": conv_id,
                        "conversation": hf_messages
                    }) + '\n')
                    count += 1
        
        print(f"✓ Converted {count} conversations to HuggingFace format")
        return output_file

    def to_csv_pairs(self, input_file: str, output_file: str, max_chats: int = 10000):
        """
        Export as CSV with user-bot pairs for spreadsheet analysis.
        
        Format:
        conversation_id,user_message,bot_response,timestamp
        """
        print(f"Converting to CSV pairs: {output_file}")
        
        import csv
        
        count = 0
        pairs = 0
        
        with open(output_file, 'w', newline='') as out_f:
            writer = csv.writer(out_f)
            writer.writerow(['conversation_id', 'user_message', 'bot_response', 'timestamp'])
            
            for conv in self.read_jsonl(input_file):
                if count >= max_chats:
                    break
                
                conv_id = conv.get('conversation_id', f'conv_{count}')
                messages = conv.get('messages', [])
                
                # Pair consecutive messages
                for i in range(0, len(messages) - 1, 2):
                    user_msg = self.clean_text(messages[i].get('content', ''))
                    bot_msg = self.clean_text(messages[i+1].get('content', ''))
                    timestamp = messages[i].get('timestamp', '')
                    
                    if user_msg and bot_msg:
                        writer.writerow([conv_id, user_msg, bot_msg, timestamp])
                        pairs += 1
                
                count += 1
        
        print(f"✓ Converted {count} conversations to {pairs} user-bot pairs (CSV)")
        return output_file

    def to_plain_text(self, input_file: str, output_file: str, max_chats: int = 10000):
        """
        Export as plain text conversations (for human review/QA).
        
        Format:
        === Conversation conv_1 ===
        User: Hello
        Bot: Hi there!
        """
        print(f"Converting to plain text: {output_file}")
        
        count = 0
        
        with open(output_file, 'w') as out_f:
            for conv in self.read_jsonl(input_file):
                if count >= max_chats:
                    break
                
                conv_id = conv.get('conversation_id', f'conv_{count}')
                messages = conv.get('messages', [])
                
                if len(messages) < 2:
                    continue
                
                out_f.write(f"\n{'='*60}\n")
                out_f.write(f"Conversation: {conv_id}\n")
                out_f.write(f"{'='*60}\n")
                
                for msg in messages:
                    sender = msg.get('sender', 'Unknown')
                    content = self.clean_text(msg.get('content', ''))
                    timestamp = msg.get('timestamp', '')
                    
                    if content:
                        role = 'Bot' if "+bot" in sender.lower() else 'Customer'
                        out_f.write(f"\n[{timestamp}] {role}: {content}\n")
                
                count += 1
        
        print(f"✓ Converted {count} conversations to plain text")
        return output_file

    def validate_data(self, input_file: str, sample_size: int = 10):
        """Validate data quality and show statistics."""
        print(f"\nValidating data from {input_file}...\n")
        
        total_convs = 0
        total_msgs = 0
        msg_lengths = []
        empty_msgs = 0
        
        samples = []
        
        for conv in self.read_jsonl(input_file):
            total_convs += 1
            messages = conv.get('messages', [])
            total_msgs += len(messages)
            
            for msg in messages:
                content = msg.get('content', '')
                if not content:
                    empty_msgs += 1
                else:
                    msg_lengths.append(len(content))
            
            if len(samples) < sample_size:
                samples.append({
                    'id': conv.get('conversation_id'),
                    'msg_count': len(messages),
                    'first_msg': messages[0].get('content', '')[:50] if messages else 'N/A'
                })
        
        # Statistics
        if msg_lengths:
            avg_length = sum(msg_lengths) / len(msg_lengths)
            print(f"📊 Statistics:")
            print(f"  Total conversations: {total_convs}")
            print(f"  Total messages: {total_msgs}")
            print(f"  Empty messages: {empty_msgs}")
            print(f"  Avg message length: {avg_length:.0f} characters")
            print(f"  Min/Max length: {min(msg_lengths)} / {max(msg_lengths)}")
        
        print(f"\n📋 Sample conversations:")
        for sample in samples:
            print(f"  • {sample['id']}: {sample['msg_count']} messages")
            print(f"    First: {sample['first_msg']}...")
        
        print(f"\n✓ Validation complete")


def main():
    parser = argparse.ArgumentParser(description='Preprocess Wabis chats for AI training')
    parser.add_argument('--format', 
                       choices=['openai', 'anthropic', 'huggingface', 'csv', 'text', 'all'],
                       default='all',
                       help='Output format')
    parser.add_argument('--input', 
                       default='wabis_chats.jsonl',
                       help='Input JSONL file')
    parser.add_argument('--output-dir',
                       default='./training_data',
                       help='Output directory')
    parser.add_argument('--max-chats',
                       type=int,
                       default=10000,
                       help='Maximum conversations to process')
    parser.add_argument('--validate',
                       action='store_true',
                       help='Validate data and show statistics')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    preprocessor = ChatPreprocessor()
    
    # Validate if requested
    if args.validate:
        preprocessor.validate_data(args.input)
        return
    
    # Convert
    formats = {
        'openai': lambda: preprocessor.to_openai_format(
            args.input, str(output_dir / 'openai_format.jsonl'), args.max_chats
        ),
        'anthropic': lambda: preprocessor.to_anthropic_format(
            args.input, str(output_dir / 'anthropic_format.jsonl'), args.max_chats
        ),
        'huggingface': lambda: preprocessor.to_huggingface_format(
            args.input, str(output_dir / 'huggingface_format.jsonl'), args.max_chats
        ),
        'csv': lambda: preprocessor.to_csv_pairs(
            args.input, str(output_dir / 'user_bot_pairs.csv'), args.max_chats
        ),
        'text': lambda: preprocessor.to_plain_text(
            args.input, str(output_dir / 'conversations.txt'), args.max_chats
        ),
    }
    
    print(f"\n{'='*60}")
    print("WABIS CHAT PREPROCESSOR FOR AI TRAINING")
    print(f"{'='*60}\n")
    
    if args.format == 'all':
        for fmt_name in ['openai', 'anthropic', 'huggingface', 'csv', 'text']:
            formats[fmt_name]()
    else:
        formats[args.format]()
    
    print(f"\n✓ Output saved to: {output_dir.absolute()}\n")


if __name__ == "__main__":
    main()
