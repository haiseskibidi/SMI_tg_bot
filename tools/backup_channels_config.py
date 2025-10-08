
"""
📦 Автоматический бэкап channels_config.yaml
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

def backup_channels_config():
    """Создать бэкап channels_config.yaml"""
    
    
    source = Path('config/channels_config.yaml')
    backup_dir = Path('backups/channels_config')
    
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    if not source.exists():
        print('❌ Файл channels_config.yaml не найден')
        return False
    
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_name = f'channels_config_{timestamp}.yaml'
    backup_path = backup_dir / backup_name
    
    
    shutil.copy2(source, backup_path)
    
    
    latest_link = backup_dir / 'latest.yaml'
    if latest_link.exists():
        latest_link.unlink()
    
    
    shutil.copy2(backup_path, latest_link)
    
    print(f'✅ Бэкап создан: {backup_name}')
    print(f'📁 Путь: {backup_path}')
    
    
    cleanup_old_backups(backup_dir)
    
    return True

def cleanup_old_backups(backup_dir, keep_count=10):
    """Удалить старые бэкапы, оставить только последние"""
    
    backup_files = []
    for file in backup_dir.glob('channels_config_*.yaml'):
        backup_files.append(file)
    
    
    backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    
    for file in backup_files[keep_count:]:
        file.unlink()
        print(f'🗑️ Удален старый бэкап: {file.name}')

if __name__ == '__main__':
    backup_channels_config()