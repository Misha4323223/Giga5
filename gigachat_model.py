import os
import requests
import json
import uuid
import time
import logging
from datetime import datetime, timedelta
from search_service import SearchService

class GigaChatModel:
    def __init__(self):
        self.api_key = os.environ.get("GIGACHAT_API_KEY")
        self.access_token = None
        self.token_expires_at = None
        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"
        
        # Инициализируем сервис поиска
        self.search_service = SearchService()
        
        if not self.api_key:
            logging.error("GIGACHAT_API_KEY не найден в переменных окружения")
            self.model_loaded = False
        else:
            logging.info("Инициализация GigaChat...")
            self.model_loaded = True
            self._get_access_token()
    
    def _get_access_token(self):
        """Получение токена доступа для GigaChat API"""
        try:
            url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'RqUID': str(uuid.uuid4()),
                'Authorization': f'Basic {self.api_key}'
            }
            
            data = {
                'scope': 'GIGACHAT_API_PERS'
            }
            
            response = requests.post(url, headers=headers, data=data, verify=False)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                # Токен действует 30 минут
                self.token_expires_at = datetime.now() + timedelta(minutes=25)
                logging.info("GigaChat токен получен успешно")
                return True
            else:
                logging.error(f"Ошибка получения токена: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"Ошибка при получении токена GigaChat: {str(e)}")
            return False
    
    def _ensure_valid_token(self):
        """Проверка и обновление токена при необходимости"""
        if not self.access_token or (self.token_expires_at and datetime.now() >= self.token_expires_at):
            return self._get_access_token()
        return True
    
    def generate_response(self, user_message, chat_history=None, kandinsky_service=None):
        """Генерация ответа от GigaChat с поиском в интернете и генерацией изображений"""
        if not self.model_loaded:
            return "Ошибка: GigaChat API не настроен. Проверьте API ключ."
        
        if not self._ensure_valid_token():
            return "Ошибка авторизации в GigaChat. Проверьте API ключ."
        
        # Сначала получаем предварительный ответ от GigaChat (без поиска)
        preliminary_response = self._get_gigachat_response(user_message, chat_history, None)
        
        # Проверяем, хочет ли GigaChat поискать информацию в интернете
        if "ИЩУИНФОРМАЦИЮ:" in preliminary_response:
            # Извлекаем поисковый запрос из ответа GigaChat
            search_query = self._extract_search_query_from_response(preliminary_response)
            logging.info(f"GigaChat решил поискать информацию: {search_query}")
            
            # Выполняем поиск
            search_result = self.search_service.search(search_query)
            
            if search_result:
                # Добавляем задержку чтобы избежать rate limiting
                time.sleep(2)
                # Получаем финальный ответ от GigaChat с результатами поиска
                final_response = self._get_gigachat_response(user_message, chat_history, search_result)
                
                # Проверяем на генерацию изображения в финальном ответе
                if ("ГЕНЕРИРУЮ_ИЗОБРАЖЕНИЕ:" in final_response and kandinsky_service):
                    return self._handle_image_generation(final_response, user_message, kandinsky_service)
                
                return final_response
            else:
                # Если поиск не удался, возвращаем ответ без поиска
                return "К сожалению, не удалось получить актуальную информацию из интернета."
        
        # Проверяем, содержит ли ответ GigaChat указание на создание изображения
        if ("ГЕНЕРИРУЮ_ИЗОБРАЖЕНИЕ:" in preliminary_response and kandinsky_service):
            return self._handle_image_generation(preliminary_response, user_message, kandinsky_service)
        
        # Возвращаем обычный текстовый ответ
        return preliminary_response
    
    def _get_gigachat_response(self, user_message, chat_history=None, search_result=None):
        """Получение ответа непосредственно от GigaChat API"""
        try:
            # Подготавливаем сообщения для API
            messages = self._prepare_messages(user_message, chat_history, search_result)
            
            url = f"{self.base_url}/chat/completions"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.access_token}'
            }
            
            payload = {
                "model": "GigaChat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 512,
                "n": 1,
                "stream": False,
                "update_interval": 0
            }
            
            response = requests.post(url, headers=headers, json=payload, verify=False)
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    ai_response = result['choices'][0]['message']['content'].strip()
                    
                    # Если был поиск, источники уже включены в ответ ИИ
                    return ai_response
                else:
                    return "Не удалось получить ответ от GigaChat."
            else:
                logging.error(f"Ошибка GigaChat API: {response.status_code} - {response.text}")
                return f"Ошибка API GigaChat: {response.status_code}"
                
        except Exception as e:
            logging.error(f"Ошибка при обращении к GigaChat: {str(e)}")
            return "Произошла ошибка при генерации ответа. Попробуйте еще раз."
    
    def _extract_search_query_from_response(self, response):
        """Извлечение поискового запроса из ответа GigaChat"""
        if "ИЩУИНФОРМАЦИЮ:" in response:
            # Извлекаем текст после маркера
            parts = response.split("ИЩУИНФОРМАЦИЮ:")
            if len(parts) > 1:
                query = parts[1].strip()
                # Убираем лишние символы и возвращаем запрос
                return query.strip('.,!"\n ')
        
        # Если маркер не найден, возвращаем пустую строку
        return ""
    
    def _handle_image_generation(self, response, original_message, kandinsky_service):
        """Обработка генерации изображения"""
        # Извлекаем описание из ответа GigaChat
        image_prompt = self._extract_image_description_from_response(response, original_message)
        logging.info(f"GigaChat решил создать изображение: {image_prompt}")
        
        image_result = kandinsky_service.generate_image(image_prompt)
        
        if image_result['success']:
            return {
                'type': 'image',
                'message': image_result['message'],
                'image_data': image_result['image_data'],
                'prompt': image_result['prompt'],
                'service': image_result['service']
            }
        else:
            return f"Не удалось создать изображение: {image_result['message']}"
    
    def _extract_image_description_from_response(self, response, original_message):
        """Извлечение описания изображения из ответа GigaChat"""
        if "ГЕНЕРИРУЮ_ИЗОБРАЖЕНИЕ:" in response:
            # Извлекаем текст после маркера
            parts = response.split("ГЕНЕРИРУЮ_ИЗОБРАЖЕНИЕ:")
            if len(parts) > 1:
                description = parts[1].strip()
                # Убираем лишние символы и возвращаем описание
                return description.strip('.,!"\n ')
        
        # Если маркер не найден, используем исходное сообщение как fallback
        return original_message
    
    def _prepare_messages(self, user_message, chat_history=None, search_result=None):
        """Подготовка сообщений для GigaChat API"""
        messages = []
        
        # Системное сообщение с учетом поиска и возможностей генерации изображений
        system_content = """Ты AI-ассистент с возможностями поиска в интернете и генерации изображений через Kandinsky 3.0.

У тебя есть 3 основные возможности:

1. ПОИСК АКТУАЛЬНОЙ ИНФОРМАЦИИ:
   ОБЯЗАТЕЛЬНО используй поиск для любых запросов о:
   - Новых версиях продуктов (GPT-5, Claude, Gemini)
   - Актуальных событиях, новостях, курсах валют
   - Определениях современных технологий и терминов
   - Свежих данных и фактах
   
   Формат: "ИЩУИНФОРМАЦИЮ: [конкретный поисковый запрос на английском]"
   
   КРИТИЧЕСКИ ВАЖНО: ВСЕ русские термины переводи на английский!
   
   Примеры перевода терминов:
   - чат жпт/жпт/gpt → ChatGPT/GPT
   - искусственный интеллект → artificial intelligence
   - нейронные сети → neural networks
   - машинное обучение → machine learning
   - блокчейн → blockchain
   - криптовалюта/биткойн → cryptocurrency/Bitcoin
   - квантовые компьютеры → quantum computers
   - курс доллара → USD exchange rate
   - погода в Москве → weather Moscow
   - новости Tesla → Tesla news
   - цена нефти → oil price
   
   ПРИМЕРЫ ЗАПРОСОВ:
   - "что такое GPT-5" → ИЩУИНФОРМАЦИЮ: GPT-5 latest information
   - "искусственный интеллект новости" → ИЩУИНФОРМАЦИЮ: artificial intelligence news today  
   - "курс биткойна сегодня" → ИЩУИНФОРМАЦИЮ: Bitcoin price today
   - "машинное обучение обучение" → ИЩУИНФОРМАЦИЮ: machine learning tutorial
   - "блокчейн технологии" → ИЩУИНФОРМАЦИЮ: blockchain technology overview

2. ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ:
   - Запросы на совет/варианты → отвечай текстом с предложениями
   - Конкретные запросы на создание → используй "ГЕНЕРИРУЮ_ИЗОБРАЖЕНИЕ: [детальное описание]"

3. ОБЫЧНЫЕ ОТВЕТЫ:
   Для остальных вопросов отвечай на основе своих знаний.

ВАЖНО: 
- НЕ говори "у меня нет доступа к интернету" - у тебя есть поиск!
- НЕ говори "не могу генерировать изображения" - ты можешь!
- Сначала определи тип запроса, потом действуй соответственно.

Отвечай на русском языке кратко и по существу."""
        
        if search_result:
            system_content = """ВАЖНО! Тебе предоставлены АКТУАЛЬНЫЕ данные из интернета по запросу пользователя.

ОБЯЗАТЕЛЬНЫЕ ИНСТРУКЦИИ:
1. Используй ТОЛЬКО предоставленные данные из поиска для ответа
2. НЕ добавляй информацию из твоих знаний
3. НЕ говори "официальной информации нет" если в поиске есть данные
4. Отвечай основываясь исключительно на найденной информации
5. Если есть конкретные факты в поиске - приводи их

Отвечай на русском языке, структурированно и информативно."""
        
        messages.append({
            "role": "system",
            "content": system_content
        })
        
        # Добавляем историю чата (последние 10 сообщений)
        if chat_history:
            recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
            
            for message in recent_history:
                if message['role'] == 'user':
                    messages.append({
                        "role": "user",
                        "content": message['content']
                    })
                elif message['role'] == 'assistant':
                    messages.append({
                        "role": "assistant",
                        "content": message['content']
                    })
        
        # Формируем текущее сообщение
        current_message = user_message
        if search_result:
            current_message = f"Пользователь спрашивает: {user_message}\n\n=== АКТУАЛЬНЫЕ ДАННЫЕ ИЗ ИНТЕРНЕТА ===\n{search_result}\n\n=== ИНСТРУКЦИЯ ===\nОтветь на вопрос пользователя, используя ТОЛЬКО предоставленную выше актуальную информацию. Не упоминай ограничения доступа к интернету - у тебя есть свежие данные!"
        
        messages.append({
            "role": "user",
            "content": current_message
        })
        
        return messages
    
    def get_status(self):
        """Получение статуса модели"""
        if not self.model_loaded:
            return {
                'status': 'error',
                'message': 'API ключ не настроен'
            }
        
        if not self.access_token:
            return {
                'status': 'loading',
                'message': 'Получение токена доступа...'
            }
        
        return {
            'status': 'ready',
            'message': 'GigaChat готов к работе',
            'model': 'GigaChat API'
        }