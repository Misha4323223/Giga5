import os
import requests
import json
import logging
import urllib.parse
from typing import Optional, Dict, Any

class SearchService:
    def __init__(self):
        self.enabled = True  # Всегда включен - используем SearXNG + DuckDuckGo
        logging.info("Поиск в интернете включен: SearXNG + DuckDuckGo")
    
    def search(self, query: str) -> Optional[str]:
        """Поиск информации в интернете через SearXNG и DuckDuckGo"""
        if not self.enabled:
            return None
        
        # Сначала пробуем SearXNG (лучше для свежих новостей)
        result = self._search_searxng(query)
        if result:
            return result
        
        # Резервный поиск через DuckDuckGo
        result = self._search_duckduckgo(query)
        if result:
            return result
        
        # Если ничего не найдено
        return f"🔍 **Поиск информации в интернете**\n\nК сожалению, в данный момент не удалось получить актуальную информацию по запросу '{query}'. Проверены источники: SearXNG и DuckDuckGo."
    
    def _search_duckduckgo(self, query: str) -> Optional[str]:
        """Поиск через DuckDuckGo используя готовую библиотеку"""
        try:
            # Переводим русские поисковые фразы в английские для лучших результатов
            translated_query = self._translate_query_to_english(query)
            logging.info(f"Переведенный запрос: {translated_query}")
            
            from duckduckgo_search import DDGS
            
            # Создаем экземпляр DDGS
            ddgs = DDGS()
            
            # Сначала пробуем получить instant answer
            try:
                answers = ddgs.answers(translated_query)
                if answers:
                    # Форматируем instant answer
                    answer = answers[0]
                    result = f"📋 **{answer.get('title', 'Информация')}:**\n{answer.get('answer', answer.get('text', ''))}"
                    
                    if answer.get('url'):
                        result += f"\n\n📚 **Источник:** {answer['url']}"
                        
                    return f"🔍 **Информация из DuckDuckGo:**\n\n{result}"
            except Exception as e:
                logging.debug(f"Instant answers недоступны: {str(e)}")
            
            # Если instant answer нет, делаем обычный поиск
            try:
                results = list(ddgs.text(translated_query, max_results=3))
                
                if results:
                    result_parts = []
                    
                    for i, result in enumerate(results, 1):
                        title = result.get('title', '').strip()
                        body = result.get('body', '').strip()
                        href = result.get('href', '').strip()
                        
                        if title and body:
                            formatted_result = f"**{i}. {title}**\n{body}"
                            if href:
                                formatted_result += f"\n🔗 {href}"
                            result_parts.append(formatted_result)
                    
                    if result_parts:
                        formatted_results = "\n\n".join(result_parts)
                        return f"🔍 **Результаты поиска DuckDuckGo:**\n\n{formatted_results}"
                        
            except Exception as e:
                logging.error(f"Поиск DuckDuckGo не удался: {str(e)}")
            
            return None
                
        except Exception as e:
            logging.error(f"Ошибка при поиске DuckDuckGo: {str(e)}")
            return None
    
    def _search_searxng(self, query: str) -> Optional[str]:
        """Поиск через SearXNG (метапоисковик)"""
        try:
            # Переводим запрос для лучших результатов
            translated_query = self._translate_query_to_english(query)
            logging.info(f"SearXNG поиск: {translated_query}")
            
            # Список надежных SearXNG инстансов
            searxng_instances = [
                "https://searx.be",
                "https://search.bus-hit.me", 
                "https://searx.tiekoetter.com"
            ]
            
            for instance in searxng_instances:
                try:
                    url = f"{instance}/search"
                    params = {
                        "q": translated_query,
                        "format": "json",
                        "categories": "general",
                        "safesearch": 0,
                        "language": "auto"
                    }
                    
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                    
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get('results'):
                            return self._format_searxng_response(data)
                    
                except Exception as e:
                    logging.debug(f"SearXNG инстанс {instance} недоступен: {str(e)}")
                    continue
                    
            return None
                    
        except Exception as e:
            logging.error(f"Ошибка при поиске SearXNG: {str(e)}")
            return None
    
    def _format_searxng_response(self, data: dict) -> Optional[str]:
        """Форматирование ответа от SearXNG"""
        try:
            results = data.get('results', [])
            if not results:
                return None
            
            result_parts = []
            
            # Берем первые 3 результата для краткости
            for i, result in enumerate(results[:3], 1):
                title = result.get('title', '').strip()
                content = result.get('content', '').strip()
                url = result.get('url', '').strip()
                
                if title:
                    formatted_result = f"**{i}. {title}**"
                    if content:
                        # Обрезаем длинный контент
                        content = content[:200] + "..." if len(content) > 200 else content
                        formatted_result += f"\n{content}"
                    if url:
                        formatted_result += f"\n🔗 {url}"
                    
                    result_parts.append(formatted_result)
            
            if result_parts:
                formatted_results = "\n\n".join(result_parts)
                return f"🔍 **Результаты поиска SearXNG:**\n\n{formatted_results}"
                
            return None
            
        except Exception as e:
            logging.error(f"Ошибка форматирования SearXNG: {str(e)}")
            return None

    

    
    def _format_duckduckgo_response(self, data: dict) -> Optional[str]:
        """Форматирование ответа от DuckDuckGo API"""
        result_parts = []
        
        # Основной ответ
        if data.get('Abstract'):
            result_parts.append(f"📋 **Краткая информация:**\n{data['Abstract']}")
        elif data.get('AbstractText'):
            result_parts.append(f"📋 **Краткая информация:**\n{data['AbstractText']}")
        
        # Определение
        if data.get('Definition'):
            result_parts.append(f"📖 **Определение:**\n{data['Definition']}")
        
        # Быстрый ответ
        if data.get('Answer'):
            result_parts.append(f"💡 **Быстрый ответ:**\n{data['Answer']}")
        
        # Связанные темы
        if data.get('RelatedTopics'):
            topics = []
            for topic in data['RelatedTopics'][:3]:
                if isinstance(topic, dict) and topic.get('Text'):
                    topics.append(f"• {topic['Text'][:100]}...")
            if topics:
                result_parts.append(f"🔗 **Связанные темы:**\n" + "\n".join(topics))
        
        # Результаты поиска
        if data.get('Results'):
            results = []
            for result in data['Results'][:2]:
                if isinstance(result, dict) and result.get('Text'):
                    results.append(f"• {result['Text']}")
            if results:
                result_parts.append(f"🔎 **Дополнительные результаты:**\n" + "\n".join(results))
        
        if result_parts:
            result = "\n\n".join(result_parts)
            
            # Добавляем источник
            if data.get('AbstractURL'):
                result += f"\n\n📚 **Источник:** {data['AbstractURL']}"
            elif data.get('OfficialWebsite'):
                result += f"\n\n🌐 **Официальный сайт:** {data['OfficialWebsite']}"
            
            return f"🔍 **Информация из DuckDuckGo:**\n\n{result}"
        
        return None


    
    def _translate_query_to_english(self, query: str) -> str:
        """Переводим русские запросы в английские для лучших результатов DuckDuckGo"""
        query_lower = query.lower().strip()
        
        # Словарь базовых переводов
        translations = {
            # Информационные запросы
            "что такое": "what is",
            "кто такой": "who is", 
            "расскажи о": "tell about",
            "расскажи про": "tell about",
            "информация о": "information about",
            "данные о": "data about",
            "определение": "definition",
            "история": "history",
            "биография": "biography",
            
            # Новости и актуальные события
            "последние новости": "latest news",
            "свежие новости": "recent news", 
            "что происходит": "what happens",
            "актуальная информация": "current information",
            "что нового": "what's new",
            "новости": "news",
            
            # Технологии
            "последняя версия": "latest version",
            "новая версия": "new version",
            "обновление": "update",
            "выпуск": "release",
            "последняя информация": "latest information",
            "информация про": "information about",
            "расскажи про": "tell about",
            "про чат жпт": "about ChatGPT",
            "чат жпт": "ChatGPT",
            "жпт": "GPT",
            "жпт-5": "GPT-5",
            "жпт5": "GPT-5",
            "последние новости про": "latest news about",
            "релиз": "release",
            "анонс": "announcement",
            
            # Финансы
            "курс": "exchange rate",
            "цена": "price",
            "стоимость": "cost",
            "котировки": "quotes",
            
            # Погода
            "погода": "weather",
            "прогноз": "forecast", 
            "температура": "temperature",
            "климат": "climate"
        }
        
        # Применяем переводы
        translated = query_lower
        for ru_phrase, en_phrase in translations.items():
            translated = translated.replace(ru_phrase, en_phrase)
        
        # Если оригинальный запрос был полностью на русском и мы его перевели, возвращаем переведенную версию
        if translated != query_lower:
            return translated
        
        # Иначе возвращаем оригинальный запрос
        return query