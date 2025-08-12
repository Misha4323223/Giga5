import os
import logging
import base64
from flask import Flask, render_template, request, jsonify, session
from werkzeug.middleware.proxy_fix import ProxyFix
from gigachat_model import GigaChatModel
from kandinsky_service import KandinskyService

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key-here")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize GigaChat model and Kandinsky service
ai_model = GigaChatModel()

# Initialize Kandinsky service with environment variables
kandinsky_api_key = os.environ.get("KANDINSKY_API_KEY")
kandinsky_secret_key = os.environ.get("KANDINSKY_SECRET_KEY")

if kandinsky_api_key and kandinsky_secret_key:
    kandinsky_service = KandinskyService(kandinsky_api_key, kandinsky_secret_key)
    logging.info("Kandinsky сервис инициализирован с ключами из переменных окружения")
else:
    kandinsky_service = None
    logging.warning("Kandinsky API ключи не найдены в переменных окружения. Генерация изображений недоступна.")

@app.route('/')
def index():
    """Главная страница чата"""
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """API endpoint для отправки сообщений в чат"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400
        
        # Получаем историю чата из сессии
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        # Добавляем сообщение пользователя в историю
        session['chat_history'].append({
            'role': 'user',
            'content': user_message
        })
        
        # Генерируем ответ через GigaChat (он сам решит, нужно ли изображение)
        ai_response = ai_model.generate_response(user_message, session['chat_history'], kandinsky_service)
        
        # Проверяем, содержит ли ответ информацию об изображении
        if isinstance(ai_response, dict) and ai_response.get('type') == 'image':
            # GigaChat решил создать изображение
            image_data_url = f"data:image/png;base64,{ai_response['image_data']}"
            
            # Добавляем ответ с изображением в историю
            session['chat_history'].append({
                'role': 'assistant',
                'content': ai_response['message'],
                'type': 'image',
                'prompt': ai_response['prompt'],
                'service': ai_response['service'],
                'has_image': True
            })
            
            session.modified = True
            
            return jsonify({
                'response': ai_response['message'],
                'type': 'image',
                'image_url': image_data_url,
                'prompt': ai_response['prompt'],
                'service': ai_response['service'],
                'status': 'success'
            })
        
        # Добавляем ответ AI в историю
        session['chat_history'].append({
            'role': 'assistant',
            'content': ai_response
        })
        
        # Ограничиваем историю последними 20 сообщениями для экономии памяти
        if len(session['chat_history']) > 20:
            session['chat_history'] = session['chat_history'][-20:]
        
        session.modified = True
        
        return jsonify({
            'response': ai_response,
            'status': 'success'
        })
        
    except Exception as e:
        logging.error(f"Ошибка при обработке сообщения: {str(e)}")
        return jsonify({
            'error': 'Произошла ошибка при генерации ответа. Попробуйте еще раз.',
            'status': 'error'
        }), 500

@app.route('/api/clear', methods=['POST'])
def clear_chat():
    """Очистка истории чата"""
    session['chat_history'] = []
    session.modified = True
    return jsonify({'status': 'success', 'message': 'История чата очищена'})

@app.route('/api/history', methods=['GET'])
def get_history():
    """Получение истории чата"""
    history = session.get('chat_history', [])
    return jsonify({'history': history})

@app.route('/api/model_status', methods=['GET'])
def model_status():
    """Проверка статуса модели"""
    status = ai_model.get_status()
    return jsonify(status)

@app.route('/api/image_status', methods=['GET'])  
def image_status():
    """Проверка статуса сервиса генерации изображений"""
    if kandinsky_service:
        kandinsky_status = kandinsky_service.get_service_status()
    else:
        kandinsky_status = {
            'status': 'error',
            'message': 'API ключи не настроены',
            'available': False
        }
    
    return jsonify({
        'kandinsky': kandinsky_status,
        'service': 'Kandinsky 3.0'
    })

@app.route('/api/kandinsky/styles', methods=['GET'])
def kandinsky_styles():
    """Получение доступных стилей Kandinsky"""
    if not kandinsky_service:
        return jsonify({
            'error': 'Kandinsky API ключи не настроены',
            'status': 'error'
        }), 500
    
    try:
        styles = kandinsky_service.get_available_styles()
        return jsonify({
            'styles': styles,
            'status': 'success'
        })
    except Exception as e:
        logging.error(f"Ошибка получения стилей Kandinsky: {str(e)}")
        return jsonify({
            'error': 'Не удалось получить список стилей',
            'status': 'error'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
