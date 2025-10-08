
import re
from typing import List, Optional, Dict
from loguru import logger


class ChannelParser:
    
    def parse_channel_username(self, channel_input: str) -> Optional[str]:
        try:
            if not channel_input or not channel_input.strip():
                return None
            
            channel_input = channel_input.strip()
            
            
            if "t.me/" in channel_input:
                match = re.search(r't\.me/([a-zA-Z_][a-zA-Z0-9_]{3,})', channel_input)
                if match:
                    return match.group(1)
            
            
            elif channel_input.startswith("@"):
                username = channel_input[1:]
                if self._is_valid_username(username):
                    return username
            
            
            
            elif "tg://resolve?domain=" in channel_input:
                match = re.search(r'domain=([a-zA-Z_][a-zA-Z0-9_]{3,})', channel_input)
                if match:
                    return match.group(1)
            
            logger.warning(f"⚠️ Не удалось распарсить ссылку: {channel_input}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга канала '{channel_input}': {e}")
            return None
    
    def parse_multiple_channels(self, text: str) -> List[str]:
        try:
            channels = []
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                
                username = self.parse_channel_username(line)
                if username:
                    channels.append(username)
                else:
                    
                    
                    found_channels = self._extract_channels_from_line(line)
                    channels.extend(found_channels)
            
            return list(set(channels))  
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга нескольких каналов: {e}")
            return []
    
    def _extract_channels_from_line(self, line: str) -> List[str]:
        channels = []
        
        
        mentions = re.findall(r'@([a-zA-Z_][a-zA-Z0-9_]{3,})', line)
        channels.extend(mentions)
        
        
        tme_links = re.findall(r't\.me/([a-zA-Z_][a-zA-Z0-9_]{3,})', line)
        channels.extend(tme_links)
        
        return channels
    
    def _is_valid_username(self, username: str) -> bool:
        if not username:
            return False
        
        
        if len(username) < 5 or len(username) > 32:
            return False
        
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*[a-zA-Z0-9]$', username):
            return False
        
        return True
    
    def normalize_channel_username(self, username: str) -> str:
        if not username:
            return ""
        
        if username.startswith("@"):
            username = username[1:]
        
        return username.lower().strip()
    
    def extract_channel_info_from_url(self, url: str) -> Dict[str, Optional[str]]:
        try:
            username = self.parse_channel_username(url)
            
            return {
                "username": username,
                "original_url": url,
                "normalized_username": self.normalize_channel_username(username) if username else None,
                "is_valid": self._is_valid_username(username) if username else False
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения информации из URL: {e}")
            return {
                "username": None,
                "original_url": url,
                "normalized_username": None,
                "is_valid": False
            }

