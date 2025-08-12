import json
import time
import base64
import requests
import logging
import os
from typing import Dict, Optional

class KandinskyService:
    """Сервис для работы с Kandinsky 3.0 API через Fusion Brain"""
    
    def __init__(self, api_key: str, secret_key: str):
        """
        Инициализация сервиса Kandinsky
        
        Args:
            api_key: API ключ от Fusion Brain
            secret_key: Секретный ключ от Fusion Brain
        """
        self.URL = "https://api-key.fusionbrain.ai/"
        self.api_key = api_key
        self.secret_key = secret_key
        
        # Заголовки для авторизации
        self.AUTH_HEADERS = {
            'X-Key': f'Key {api_key}',
            'X-Secret': f'Secret {secret_key}',
        }
        
        # Настройки по умолчанию
        self.default_width = 1024
        self.default_height = 1024
        self.default_style = "DEFAULT"
        
        # Инициализация
        self.pipeline_id = None
        self._initialize()
        
    def _initialize(self):
        """Инициализация сервиса - получение ID пайплайна"""
        try:
            self.pipeline_id = self.get_pipeline()
            if self.pipeline_id:
                logging.info("Kandinsky 3.0 сервис успешно инициализирован")
            else:
                logging.error("Не удалось получить pipeline_id")
        except Exception as e:
            logging.error(f"Ошибка инициализации Kandinsky: {str(e)}")
    
    def get_pipeline(self) -> Optional[str]:
        """Получение доступных моделей и выбор первой"""
        try:
            response = requests.get(
                self.URL + 'key/api/v1/pipelines', 
                headers=self.AUTH_HEADERS,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    pipeline_id = data[0]['id']
                    model_name = data[0].get('name', 'Unknown')
                    version = data[0].get('version', 'Unknown')
                    logging.info(f"Подключена модель: {model_name} v{version}")
                    return pipeline_id
            else:
                logging.error(f"Ошибка получения пайплайнов: {response.status_code}")
                
        except Exception as e:
            logging.error(f"Ошибка при получении pipeline: {str(e)}")
            
        return None
    
    def check_service_availability(self) -> Dict:
        """Проверка доступности сервиса через получение списка пайплайнов"""
        try:
            # Используем основной эндпоинт для проверки доступности
            response = requests.get(
                self.URL + 'key/api/v1/pipelines',
                headers=self.AUTH_HEADERS,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return {
                        'available': True,
                        'status': 'online',
                        'message': 'Сервис доступен'
                    }
                else:
                    return {
                        'available': False,
                        'status': 'no_models',
                        'message': 'Нет доступных моделей'
                    }
            elif response.status_code == 401:
                return {
                    'available': False,
                    'status': 'unauthorized',
                    'message': 'Ошибка авторизации API ключа'
                }
            elif response.status_code == 403:
                return {
                    'available': False,
                    'status': 'forbidden',
                    'message': 'Доступ запрещен'
                }
            else:
                return {
                    'available': False,
                    'status': f'http_{response.status_code}',
                    'message': f'HTTP ошибка: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'available': False,
                'status': 'error',
                'message': f'Ошибка подключения: {str(e)}'
            }
    
    def generate_image(
        self, 
        prompt: str, 
        width: Optional[int] = None, 
        height: Optional[int] = None,
        style: Optional[str] = None,
        negative_prompt: str = ""
    ) -> Dict:
        """
        Генерация изображения по текстовому описанию
        
        Args:
            prompt: Текстовое описание изображения
            width: Ширина изображения (по умолчанию 1024)
            height: Высота изображения (по умолчанию 1024)
            style: Стиль изображения
            negative_prompt: Негативный промпт
            
        Returns:
            Dict с результатом генерации
        """
        if not self.pipeline_id:
            return {
                'success': False,
                'error': 'Сервис не инициализирован',
                'message': 'Ошибка инициализации Kandinsky API'
            }
        
        if not prompt or not prompt.strip():
            return {
                'success': False,
                'error': 'Пустой промпт',
                'message': 'Необходимо указать описание изображения'
            }
        
        # Если нет пайплайна, пробуем переинициализироваться
        if not self.pipeline_id:
            self._initialize()
            if not self.pipeline_id:
                return {
                    'success': False,
                    'error': 'Сервис не инициализирован',
                    'message': 'Не удалось подключиться к API'
                }
        
        # Параметры по умолчанию
        width = width if width is not None else self.default_width
        height = height if height is not None else self.default_height
        style = style if style is not None else self.default_style
        
        # Ограничиваем длину промпта
        if len(prompt) > 1000:
            prompt = prompt[:1000]
        
        try:
            # Запуск генерации
            request_id = self._start_generation(
                prompt, width, height, style, negative_prompt
            )
            
            if not request_id:
                return {
                    'success': False,
                    'error': 'Ошибка запуска генерации',
                    'message': 'Не удалось запустить генерацию изображения'
                }
            
            # Ожидание завершения генерации
            result = self._wait_for_completion(request_id)
            
            if result['success']:
                return {
                    'success': True,
                    'image_data': result['image_data'],
                    'prompt': prompt,
                    'width': width,
                    'height': height,
                    'style': style,
                    'service': 'Kandinsky 3.0',
                    'message': f'Изображение "{prompt}" успешно сгенерировано'
                }
            else:
                return result
                
        except Exception as e:
            logging.error(f"Ошибка генерации изображения: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Произошла ошибка при генерации изображения'
            }
    
    def _start_generation(
        self, 
        prompt: str, 
        width: int, 
        height: int, 
        style: str, 
        negative_prompt: str
    ) -> Optional[str]:
        """Запуск процесса генерации изображения"""
        
        params = {
            "type": "GENERATE",
            "numImages": 1,
            "width": width,
            "height": height,
            "generateParams": {
                "query": prompt
            }
        }
        
        # Добавляем стиль, если указан и не является дефолтным
        if style and style != "DEFAULT":
            params["style"] = style
            
        # Добавляем негативный промпт, если указан
        if negative_prompt and negative_prompt.strip():
            params["negativePromptDecoder"] = negative_prompt.strip()
        
        data = {
            'pipeline_id': (None, self.pipeline_id),
            'params': (None, json.dumps(params), 'application/json')
        }
        
        try:
            response = requests.post(
                self.URL + 'key/api/v1/pipeline/run',
                headers=self.AUTH_HEADERS,
                files=data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                request_id = result.get('uuid')
                if request_id:
                    logging.info(f"Генерация запущена с ID: {request_id}")
                    return request_id
                else:
                    logging.error(f"Нет UUID в ответе: {result}")
            else:
                logging.error(f"Ошибка запуска генерации: {response.status_code} - {response.text}")
                
        except Exception as e:
            logging.error(f"Исключение при запуске генерации: {str(e)}")
            
        return None
    
    def _wait_for_completion(self, request_id: str, max_attempts: int = 60, delay: int = 3) -> Dict:
        """Ожидание завершения генерации"""
        
        attempts = 0
        while attempts < max_attempts:
            try:
                response = requests.get(
                    self.URL + f'key/api/v1/pipeline/status/{request_id}',
                    headers=self.AUTH_HEADERS,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status')
                    
                    if status == 'DONE':
                        result = data.get('result', {})
                        files = result.get('files', [])
                        censored = result.get('censored', False)
                        
                        if censored:
                            return {
                                'success': False,
                                'error': 'Контент заблокирован модерацией',
                                'message': 'Изображение не прошло модерацию контента'
                            }
                        
                        if files and len(files) > 0:
                            # Декодируем изображение из base64
                            image_base64 = files[0]
                            
                            return {
                                'success': True,
                                'image_data': image_base64,
                                'format': 'base64'
                            }
                        else:
                            return {
                                'success': False,
                                'error': 'Нет файлов в ответе',
                                'message': 'Сервер не вернул сгенерированное изображение'
                            }
                    
                    elif status == 'FAIL':
                        error_description = data.get('errorDescription', 'Неизвестная ошибка')
                        return {
                            'success': False,
                            'error': error_description,
                            'message': f'Генерация не удалась: {error_description}'
                        }
                    
                    elif status in ['INITIAL', 'PROCESSING']:
                        attempts += 1
                        if attempts % 10 == 0:  # Логируем каждые 30 секунд
                            logging.info(f"Генерация в процессе... Попытка {attempts}/{max_attempts}")
                        time.sleep(delay)
                        continue
                    
                    else:
                        logging.warning(f"Неизвестный статус: {status}")
                        attempts += 1
                        time.sleep(delay)
                        continue
                
                else:
                    logging.error(f"Ошибка проверки статуса: {response.status_code}")
                    attempts += 1
                    time.sleep(delay)
                    continue
                    
            except Exception as e:
                logging.error(f"Исключение при проверке статуса: {str(e)}")
                attempts += 1
                time.sleep(delay)
                continue
        
        return {
            'success': False,
            'error': 'Превышено время ожидания',
            'message': 'Генерация изображения заняла слишком много времени'
        }
    
    def get_available_styles(self) -> list:
        """Получение списка доступных стилей"""
        try:
            response = requests.get(
                "https://cdn.fusionbrain.ai/static/styles/api",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.error(f"Ошибка получения стилей: {str(e)}")
        
        # Возвращаем базовые стили по умолчанию
        return [
            {"id": "DEFAULT", "name": "По умолчанию"},
            {"id": "ANIME", "name": "Аниме"},
            {"id": "UHD", "name": "Высокое качество"}
        ]
    
    def is_image_generation_request(self, message: str) -> bool:
        """Проверка, является ли сообщение запросом на генерацию изображения"""
        message_lower = message.lower()
        
        # Ключевые слова для определения запроса на генерацию изображения
        image_keywords = [
            'нарисуй', 'создай изображение', 'сгенерируй изображение', 
            'создай картинку', 'нарисовать', 'изображение', 'картинку',
            '/generate', 'generate image', 'создать изображение',
            'сделай изображение', 'покажи изображение', 'можешь сгенерировать',
            'создай', 'принт', 'дизайн', 'логотип', 'визуализируй',
            'покажи как выглядит', 'сгенерируй', 'можешь создать',
            'футболка', 'эскиз', 'концепт', 'рисунок', 'техно самурай'
        ]
        
        return any(keyword in message_lower for keyword in image_keywords)
    
    def extract_image_prompt(self, message: str) -> str:
        """Извлечение промпта для генерации изображения из сообщения"""
        message_lower = message.lower()
        
        # Удаляем команды и получаем чистый промпт
        prefixes_to_remove = [
            'нарисуй', 'создай изображение', 'сгенерируй изображение',
            'создай картинку', 'нарисовать', '/generate', 'generate image',
            'создать изображение', 'сделай изображение', 'покажи изображение'
        ]
        
        prompt = message
        for prefix in prefixes_to_remove:
            if message_lower.startswith(prefix):
                prompt = message[len(prefix):].strip()
                break
        
        # Удаляем лишние символы в начале
        prompt = prompt.lstrip(':-.,! ')
        
        return prompt if prompt else message
    
    def get_service_status(self) -> Dict:
        """Получение статуса сервиса для API"""
        availability = self.check_service_availability()
        
        return {
            'service': 'Kandinsky 3.0',
            'status': 'online' if availability['available'] else 'offline',
            'available': availability['available'],
            'message': availability['message'],
            'pipeline_id': self.pipeline_id is not None,
            'api_configured': bool(self.api_key and self.secret_key)
        }