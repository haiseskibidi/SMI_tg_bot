from typing import List
from loguru import logger

class TextHelpers:
    
    @staticmethod
    def split_message(message: str, max_length: int = 4000) -> List[str]:
        if len(message) <= max_length:
            return [message]
        
        parts = []
        current_part = ""
        lines = message.split('\n')
        
        for line in lines:
            if len(current_part) + len(line) + 1 > max_length:
                if current_part:
                    parts.append(current_part.strip())
                    current_part = line
                else:
                    while len(line) > max_length:
                        parts.append(line[:max_length])
                        line = line[max_length:]
                    current_part = line
            else:
                if current_part:
                    current_part += '\n' + line
                else:
                    current_part = line
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        
        text = text.replace('**', '').replace('__', '').replace('*', '').replace('_', '')
        text = ' '.join(text.split())
        
        return text.strip()
    
    @staticmethod
    def truncate_text(text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        
        words = text.split()
        result = ""
        
        for word in words:
            if len(result + " " + word) <= max_length - 3:
                if result:
                    result += " "
                result += word
            else:
                break
        
        return result + "..." if result != text else text
