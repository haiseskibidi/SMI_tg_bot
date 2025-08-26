"""
🌐 Web Interface Module
Простой веб-интерфейс для мониторинга системы
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import threading
import time

try:
    from flask import Flask, render_template_string, jsonify, request
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from loguru import logger


class WebInterface:
    """Веб-интерфейс для мониторинга"""
    
    def __init__(self, database, system_monitor, port: int = 8080):
        self.database = database
        self.system_monitor = system_monitor
        self.port = port
        self.app = None
        self.server_thread = None
        
        if not FLASK_AVAILABLE:
            logger.warning("⚠️ Flask не установлен. Веб-интерфейс недоступен.")
            logger.info("💡 Установите: pip install flask")
            return
        
        self.setup_flask()
        logger.info(f"🌐 WebInterface инициализирован на порту {port}")
    
    def setup_flask(self):
        """Настройка Flask приложения"""
        if not FLASK_AVAILABLE:
            return
        
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'news_monitor_secret_key'
        
        # Главная страница
        @self.app.route('/')
        def index():
            return render_template_string(self.get_main_template())
        
        # API для получения статистики
        @self.app.route('/api/stats')
        def get_stats():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Получаем статистику из базы
                stats = loop.run_until_complete(self.database.get_today_stats())
                
                # Добавляем системную информацию
                system_stats = {
                    'memory': self.system_monitor.get_memory_usage(),
                    'cpu': self.system_monitor.get_cpu_usage(),
                    'disk': self.system_monitor.get_disk_usage()
                }
                
                loop.close()
                
                return jsonify({
                    'database': stats,
                    'system': system_stats,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"❌ Ошибка API статистики: {e}")
                return jsonify({'error': str(e)}), 500
        
        # API для получения новостей
        @self.app.route('/api/news')
        def get_news():
            try:
                limit = request.args.get('limit', 999999, type=int)  # Показываем ВСЕ новости
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                news = loop.run_until_complete(
                    self.database.get_unsent_news_today(limit)
                )
                
                loop.close()
                
                return jsonify(news)
                
            except Exception as e:
                logger.error(f"❌ Ошибка API новостей: {e}")
                return jsonify({'error': str(e)}), 500
    
    def get_main_template(self) -> str:
        """HTML шаблон главной страницы"""
        return """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📰 Мониторинг Новостей | Сахалин & Камчатка</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-card h3 {
            font-size: 1.2em;
            margin-bottom: 15px;
            color: #555;
        }
        
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .news-section {
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .news-item {
            border-bottom: 1px solid #eee;
            padding: 20px 0;
            transition: background 0.3s ease;
            text-align: left; /* Выравнивание по левому краю */
        }
        
        .news-item:hover {
            background: rgba(102, 126, 234, 0.05);
            border-radius: 10px;
            margin: 0 -10px;
            padding: 20px 10px;
        }
        
        .news-item:last-child {
            border-bottom: none;
        }
        
        .news-title {
            font-size: 1.4em;
            font-weight: bold;
            margin-bottom: 8px;
            color: #333;
            line-height: 1.3;
        }
        
        .news-source {
            color: #667eea;
            font-size: 0.9em;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .news-meta {
            color: #666;
            font-size: 0.85em;
            margin-bottom: 12px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        .news-meta span {
            background: rgba(102, 126, 234, 0.1);
            padding: 2px 8px;
            border-radius: 12px;
        }
        
        .news-text {
            color: #555;
            line-height: 1.6;
            text-align: justify; /* Выравнивание по ширине */
            margin-bottom: 10px;
        }
        
        .news-url {
            margin-top: 8px;
        }
        
        .news-url a {
            color: #667eea;
            text-decoration: none;
            font-size: 0.9em;
        }
        
        .news-url a:hover {
            text-decoration: underline;
        }
        
        .loading {
            text-align: center;
            padding: 50px;
            color: #666;
            font-size: 1.2em;
        }
        
        .refresh-btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            transition: transform 0.3s ease;
            margin: 20px auto;
            display: block;
        }
        
        .refresh-btn:hover {
            transform: scale(1.05);
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-online { background: #4CAF50; }
        .status-warning { background: #FF9800; }
        .status-error { background: #F44336; }
        
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .header h1 { font-size: 2em; }
            .stats-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📰 Мониторинг Новостей</h1>
            <p>Автоматический отбор важных новостей Сахалина и Камчатки</p>
            <p id="last-update">Загрузка...</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>📊 Всего сегодня</h3>
                <div class="stat-value" id="total-messages">-</div>
                <p>сообщений обработано</p>
            </div>
            
            <div class="stat-card">
                <h3>⭐ Отобрано</h3>
                <div class="stat-value" id="selected-messages">-</div>
                <p>важных новостей</p>
            </div>
            
            <div class="stat-card">
                <h3>🧠 Память</h3>
                <div class="stat-value" id="memory-usage">-</div>
                <p>использовано</p>
            </div>
            
            <div class="stat-card">
                <h3>⚡ Процессор</h3>
                <div class="stat-value" id="cpu-usage">-</div>
                <p>загрузка CPU</p>
            </div>
        </div>
        
        <button class="refresh-btn" onclick="loadData()">🔄 Обновить</button>
        
        <div class="news-section">
            <h2>📰 Последние новости</h2>
            <div id="news-list" class="loading">
                Загрузка новостей...
            </div>
        </div>
    </div>

    <script>
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('total-messages').textContent = data.database.total_messages;
                document.getElementById('selected-messages').textContent = data.database.selected_messages;
                document.getElementById('memory-usage').textContent = data.system.memory.used_percent.toFixed(1) + '%';
                document.getElementById('cpu-usage').textContent = data.system.cpu.cpu_percent.toFixed(1) + '%';
                
                const updateTime = new Date(data.timestamp).toLocaleString('ru-RU');
                document.getElementById('last-update').innerHTML = 
                    '<span class="status-indicator status-online"></span>Обновлено: ' + updateTime;
                    
            } catch (error) {
                console.error('Ошибка загрузки статистики:', error);
                document.getElementById('last-update').innerHTML = 
                    '<span class="status-indicator status-error"></span>Ошибка подключения';
            }
        }
        
        async function loadNews() {
            try {
                const response = await fetch('/api/news');  // БЕЗ ЛИМИТА - ВСЕ НОВОСТИ!
                const news = await response.json();
                
                const newsList = document.getElementById('news-list');
                
                if (news.length === 0) {
                    newsList.innerHTML = '<p class="loading">Новостей пока нет</p>';
                    return;
                }
                
                newsList.innerHTML = news.map(item => {
                    // Извлекаем заголовок из AI анализа или создаем из текста
                    let title = 'Без заголовка';
                    try {
                        const aiAnalysis = JSON.parse(item.ai_analysis || '{}');
                        title = aiAnalysis.title || item.text?.substring(0, 80) + '...' || 'Без заголовка';
                    } catch {
                        title = item.text?.substring(0, 80) + '...' || 'Без заголовка';
                    }
                    
                    // Форматируем дату
                    const newsDate = new Date(item.created_at || item.date);
                    const formattedDate = newsDate.toLocaleString('ru-RU', {
                        day: '2-digit',
                        month: '2-digit', 
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                    
                    return `
                        <div class="news-item">
                            <div class="news-title">${title}</div>
                            <div class="news-source">📍 ${item.channel_name || item.channel_title || 'Неизвестный источник'}</div>
                            <div class="news-meta">
                                <span>⭐ ${item.ai_score || 0}/10</span>
                                <span>👁 ${item.views || 0} просмотров</span>
                                <span>❤️ ${item.reactions_count || 0} реакций</span>
                                <span>🕐 ${formattedDate}</span>
                            </div>
                            <div class="news-text">${(item.text || '').substring(0, 400)}${item.text && item.text.length > 400 ? '...' : ''}</div>
                            ${item.url ? `<div class="news-url"><a href="${item.url}" target="_blank">🔗 Читать полностью</a></div>` : ''}
                        </div>
                    `;
                }).join('');
                
            } catch (error) {
                console.error('Ошибка загрузки новостей:', error);
                document.getElementById('news-list').innerHTML = 
                    '<p class="loading">Ошибка загрузки новостей</p>';
            }
        }
        
        async function loadData() {
            await Promise.all([loadStats(), loadNews()]);
        }
        
        // Загружаем данные при загрузке страницы
        loadData();
        
        // Автоматическое обновление каждые 30 секунд
        setInterval(loadData, 30000);
    </script>
</body>
</html>
        """
    
    def start_server(self):
        """Запуск веб-сервера в отдельном потоке"""
        if not FLASK_AVAILABLE or not self.app:
            logger.warning("⚠️ Веб-интерфейс недоступен")
            return False
        
        def run_server():
            try:
                logger.info(f"🌐 Запуск веб-сервера на http://localhost:{self.port}")
                self.app.run(
                    host='0.0.0.0',
                    port=self.port,
                    debug=False,
                    use_reloader=False,
                    threaded=True
                )
            except Exception as e:
                logger.error(f"❌ Ошибка веб-сервера: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        time.sleep(2)  # Даем серверу время запуститься
        logger.success(f"✅ Веб-интерфейс доступен: http://localhost:{self.port}")
        
        return True
    
    def stop_server(self):
        """Остановка веб-сервера"""
        if self.server_thread and self.server_thread.is_alive():
            logger.info("🛑 Остановка веб-сервера")
            # Flask сервер остановится автоматически при завершении программы
