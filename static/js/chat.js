// Chat application JavaScript
class ChatApp {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.chatMessages = document.getElementById('chatMessages');
        this.chatForm = document.getElementById('chatForm');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.clearChatBtn = document.getElementById('clearChatBtn');
        this.modelStatus = document.getElementById('modelStatus');
        this.imageStatus = document.getElementById('imageStatus');
        this.sidebarToggle = document.getElementById('sidebarToggle');
        this.sidebarOverlay = document.getElementById('sidebarOverlay');
        this.sidebar = document.querySelector('.sidebar');
        
        this.isLoading = false;
        this.messageHistory = [];
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.checkModelStatus();
        this.checkImageStatus();
        this.loadChatHistory();
        
        // Проверяем статус сервисов каждые 10 секунд
        setInterval(() => {
            this.checkModelStatus();
            this.checkImageStatus();
        }, 10000);
        
        // Фокус на поле ввода
        this.messageInput.focus();
    }
    
    setupEventListeners() {
        // Отправка сообщения
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        // Включение/отключение кнопки отправки
        this.messageInput.addEventListener('input', () => {
            const hasText = this.messageInput.value.trim().length > 0;
            this.sendBtn.disabled = !hasText || this.isLoading;
        });
        
        // Новый чат
        this.newChatBtn.addEventListener('click', () => {
            this.clearChat();
        });
        
        // Очистка чата
        this.clearChatBtn.addEventListener('click', () => {
            this.clearChat();
        });
        
        // Переключение сайдбара на мобильных устройствах
        if (this.sidebarToggle) {
            this.sidebarToggle.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }
        
        if (this.sidebarOverlay) {
            this.sidebarOverlay.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }
        
        // Закрытие сайдбара при клике на основной контент
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && 
                !this.sidebar.contains(e.target) && 
                !this.sidebarToggle.contains(e.target)) {
                this.closeSidebar();
            }
        });
        
        // Обработка изменения размера окна
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                this.closeSidebar();
            }
        });
        
        // Автоматическое изменение высоты поля ввода
        this.messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
        });
        
        // Отправка по Ctrl+Enter
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        
        if (!message || this.isLoading) {
            return;
        }
        
        // Добавляем сообщение пользователя
        this.addMessage(message, 'user');
        
        // Очищаем поле ввода
        this.messageInput.value = '';
        this.sendBtn.disabled = true;
        
        // Показываем индикатор загрузки
        this.showLoading();
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            const data = await response.json();
            // console.log('Получен ответ от сервера:', data);
            
            if (response.ok) {
                // Проверяем, есть ли изображение в ответе
                if (data.type === 'image' && data.image_url) {
                    // console.log('Обнаружен ответ с изображением:', data.image_url.substring(0, 50) + '...');
                    this.addImageMessage(data.response, data.image_url, data.prompt, data.service);
                } else {
                    // Добавляем обычный текстовый ответ
                    this.addMessage(data.response, 'bot');
                }
            } else {
                // Обработка ошибки
                this.addMessage(
                    data.error || 'Произошла ошибка при обработке сообщения.',
                    'bot',
                    'error'
                );
            }
        } catch (error) {
            console.error('Ошибка при отправке сообщения:', error);
            this.addMessage(
                'Ошибка соединения. Проверьте подключение к серверу.',
                'bot',
                'error'
            );
        } finally {
            this.hideLoading();
        }
    }
    
    addMessage(content, sender, type = 'normal') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = sender === 'user' 
            ? '<i class="fas fa-user"></i>' 
            : '<i class="fas fa-robot"></i>';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = `message-bubble ${type === 'error' ? 'error' : ''}`;
        
        // Обработка форматирования текста
        bubbleDiv.innerHTML = this.formatMessage(content);
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = this.formatTime(new Date());
        
        contentDiv.appendChild(bubbleDiv);
        contentDiv.appendChild(timeDiv);
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        // Удаляем приветственное сообщение если это первое сообщение пользователя
        if (sender === 'user' && this.messageHistory.length === 0) {
            const welcomeMessage = this.chatMessages.querySelector('.message');
            if (welcomeMessage) {
                welcomeMessage.remove();
            }
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Добавляем в историю
        this.messageHistory.push({ content, sender, timestamp: new Date() });
        
        // Анимация появления
        setTimeout(() => {
            messageDiv.style.opacity = '1';
        }, 10);
    }
    
    addImageMessage(content, imageUrl, prompt, service) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message image-message';
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = '<i class="fas fa-palette"></i>'; // Иконка для генерации изображений
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        
        // Создаем контейнер изображения
        const imageContainer = document.createElement('div');
        imageContainer.className = 'image-container';
        
        const img = document.createElement('img');
        img.src = imageUrl;
        img.alt = prompt;
        img.className = 'generated-image';
        img.loading = 'lazy';
        
        // Добавляем обработчик загрузки изображения
        img.onload = () => {
            console.log('Изображение загружено успешно:', imageUrl);
            img.style.opacity = '1';
        };
        
        // Добавляем обработчик ошибок загрузки
        img.onerror = () => {
            console.error('Ошибка загрузки изображения:', imageUrl);
            img.alt = 'Ошибка загрузки изображения';
            img.style.opacity = '1';
            // Добавляем сообщение об ошибке
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-warning mt-2';
            errorDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Изображение не удалось загрузить';
            imageContainer.appendChild(errorDiv);
        };
        
        // Добавляем обработчик клика для полноэкранного просмотра
        img.onclick = () => {
            this.showImageModal(imageUrl, prompt);
        };
        
        const imageInfo = document.createElement('div');
        imageInfo.className = 'image-info';
        imageInfo.innerHTML = `
            <div class="image-prompt"><strong>Промпт:</strong> ${this.escapeHtml(prompt)}</div>
            <div class="image-service"><small>Сервис: ${service}</small></div>
        `;
        
        imageContainer.appendChild(img);
        imageContainer.appendChild(imageInfo);
        
        // Добавляем текст ответа (без URL изображения)
        const textContent = content.replace(/\nИзображение:.*$/i, '').trim();
        if (textContent) {
            const textDiv = document.createElement('div');
            textDiv.className = 'message-text';
            textDiv.innerHTML = this.formatMessage(textContent);
            bubbleDiv.appendChild(textDiv);
        }
        
        bubbleDiv.appendChild(imageContainer);
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = this.formatTime(new Date());
        
        contentDiv.appendChild(bubbleDiv);
        contentDiv.appendChild(timeDiv);
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        // Удаляем приветственное сообщение если необходимо
        if (this.messageHistory.length === 1) {
            const welcomeMessage = this.chatMessages.querySelector('.message:not(.user-message):not(.bot-message)');
            if (welcomeMessage) {
                welcomeMessage.remove();
            }
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Добавляем в историю
        this.messageHistory.push({ 
            content, 
            sender: 'bot', 
            timestamp: new Date(),
            type: 'image',
            imageUrl,
            prompt
        });
        
        // Анимация появления
        setTimeout(() => {
            messageDiv.style.opacity = '1';
        }, 10);
    }
    
    showImageModal(imageUrl, prompt) {
        // Создаем модальное окно для полноэкранного просмотра
        const modal = document.createElement('div');
        modal.className = 'image-modal';
        modal.innerHTML = `
            <div class="image-modal-content">
                <div class="image-modal-header">
                    <h5>${this.escapeHtml(prompt)}</h5>
                    <button class="btn btn-link text-white" onclick="this.closest('.image-modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="image-modal-body">
                    <img src="${imageUrl}" alt="${this.escapeHtml(prompt)}" class="modal-image">
                </div>
                <div class="image-modal-footer">
                    <a href="${imageUrl}" download="generated-image.jpg" class="btn btn-primary">
                        <i class="fas fa-download me-1"></i>Скачать
                    </a>
                </div>
            </div>
        `;
        
        // Закрытие по клику на фон
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        };
        
        document.body.appendChild(modal);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatMessage(content) {
        // Простое форматирование текста
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
    }
    
    formatTime(date) {
        return date.toLocaleTimeString('ru-RU', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
    
    showLoading() {
        this.isLoading = true;
        this.loadingIndicator.style.display = 'block';
        this.sendBtn.disabled = true;
        this.scrollToBottom();
    }
    
    hideLoading() {
        this.isLoading = false;
        this.loadingIndicator.style.display = 'none';
        this.sendBtn.disabled = this.messageInput.value.trim().length === 0;
        this.messageInput.focus();
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    async clearChat() {
        try {
            const response = await fetch('/api/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                // Очищаем интерфейс
                this.chatMessages.innerHTML = `
                    <div class="message bot-message">
                        <div class="message-avatar">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="message-content">
                            <div class="message-bubble">
                                Чат очищен. Начните новый разговор!
                            </div>
                            <div class="message-time">
                                ${this.formatTime(new Date())}
                            </div>
                        </div>
                    </div>
                `;
                
                this.messageHistory = [];
                this.messageInput.focus();
            }
        } catch (error) {
            console.error('Ошибка при очистке чата:', error);
        }
    }
    
    async loadChatHistory() {
        try {
            const response = await fetch('/api/history');
            const data = await response.json();
            
            if (response.ok && data.history.length > 0) {
                // Очищаем приветственное сообщение
                this.chatMessages.innerHTML = '';
                
                // Загружаем историю
                data.history.forEach(message => {
                    if (message.type === 'image' && message.has_image) {
                        // Для сообщений с изображениями из истории показываем только текст
                        // так как base64 данные не сохранены в сессии
                        const imageMessage = message.content + '\n[Изображение было сгенерировано ранее]';
                        this.addMessage(imageMessage, 'bot');
                    } else {
                        this.addMessage(
                            message.content,
                            message.role === 'user' ? 'user' : 'bot'
                        );
                    }
                });
            }
        } catch (error) {
            console.error('Ошибка при загрузке истории:', error);
        }
    }
    
    async checkModelStatus() {
        try {
            const response = await fetch('/api/model_status');
            const data = await response.json();
            
            this.updateModelStatus(data);
        } catch (error) {
            console.error('Ошибка при проверке статуса модели:', error);
            this.updateModelStatus({
                loaded: false,
                loading: false,
                error: true
            });
        }
    }
    
    updateModelStatus(status) {
        const statusEl = this.modelStatus;
        const icon = statusEl.querySelector('i');
        const text = statusEl.querySelector('span');
        
        // Удаляем все классы статуса
        statusEl.classList.remove('loading', 'ready', 'error');
        
        if (status.loading) {
            statusEl.classList.add('loading');
            icon.className = 'fas fa-circle text-warning';
            text.textContent = 'GigaChat: Загружается...';
        } else if (status.loaded) {
            statusEl.classList.add('ready');
            icon.className = 'fas fa-circle text-success';
            text.textContent = 'GigaChat: Готов';
        } else {
            statusEl.classList.add('error');
            icon.className = 'fas fa-circle text-danger';
            text.textContent = 'GigaChat: Ошибка';
        }
    }
    
    async checkImageStatus() {
        try {
            const response = await fetch('/api/image_status');
            const data = await response.json();
            
            this.updateImageStatus(data);
        } catch (error) {
            console.error('Ошибка при проверке статуса сервиса изображений:', error);
            this.updateImageStatus({
                kandinsky: { available: false, status: 'error' }
            });
        }
    }
    
    updateImageStatus(data) {
        const statusEl = this.imageStatus;
        const icon = statusEl.querySelector('i');
        const text = statusEl.querySelector('span');
        
        const kandinskyStatus = data.kandinsky;
        
        // Удаляем все классы статуса
        statusEl.classList.remove('loading', 'ready', 'error');
        
        if (kandinskyStatus && kandinskyStatus.available && kandinskyStatus.status === 'online') {
            statusEl.classList.add('ready');
            icon.className = 'fas fa-circle text-success';
            text.textContent = 'Kandinsky: Готов';
        } else if (kandinskyStatus && kandinskyStatus.pipeline_id) {
            statusEl.classList.add('loading');
            icon.className = 'fas fa-circle text-warning';
            text.textContent = 'Kandinsky: Инициализация...';
        } else {
            statusEl.classList.add('error');
            icon.className = 'fas fa-circle text-danger';
            text.textContent = 'Kandinsky: Недоступен';
        }
    }
    
    toggleSidebar() {
        if (window.innerWidth <= 768) {
            this.sidebar.classList.toggle('show');
            this.sidebarOverlay.classList.toggle('show');
        }
    }
    
    closeSidebar() {
        if (window.innerWidth <= 768) {
            this.sidebar.classList.remove('show');
            this.sidebarOverlay.classList.remove('show');
        }
    }
    
    autoResizeTextarea() {
        const textarea = this.messageInput;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
}

// Инициализация приложения
document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});

// Дополнительные утилиты
function showNotification(message, type = 'info') {
    // Простое уведомление (можно заменить на более продвинутое)
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} position-fixed`;
    notification.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        animation: slideInRight 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Обработка ошибок JavaScript
window.addEventListener('error', (e) => {
    console.error('JavaScript ошибка:', e.error);
});

// Обработка необработанных промисов
window.addEventListener('unhandledrejection', (e) => {
    console.error('Необработанная ошибка промиса:', e.reason);
});
