document.addEventListener('DOMContentLoaded', function () {
    // Обработка кнопок удаления пользователей
    document.addEventListener('click', function (event) {
        if (event.target.classList.contains('remove-user-btn')) {
            const userId = event.target.dataset.userId;
            const chatId = event.target.dataset.chatId;
            removeUserFromChat(userId, chatId, event.target);
        }
    });
});


function removeUserFromChat(userId, chatId, buttonElement) {
    fetch('/remove_user_from_chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            user_id: userId,
            chat_id: chatId
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Удаляем элемент пользователя из DOM
                const userItem = buttonElement.closest('.user-item');
                userItem.remove();

                // Обновляем счетчик пользователей
            updateUsersCount(getUsersCount() - 1);
            
            // Показываем сообщение об успешном удалении
            showNotification(data.message, 'success');
            
            // Проверяем, остались ли пользователи в списке
            const usersContainer = document.querySelector('.users-panel-content');
            if (usersContainer && !usersContainer.querySelector('.user-item')) {
                // Если не осталось пользователей, показываем сообщение
                const noUsersMessage = document.createElement('div');
                noUsersMessage.className = 'no-users';
                noUsersMessage.textContent = 'В этом чате нет пользователей';
                usersContainer.appendChild(noUsersMessage);
            }
        } else {
            showNotification(data.message || 'Произошла ошибка при удалении пользователя', 'error');
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        showNotification('Произошла ошибка при удалении пользователя', 'error');
    });
    }
    
    // Функция для получения текущего количества пользователей
    function getUsersCount() {
    const userCountElement = document.querySelector('.users-panel-header h3');
    if (userCountElement) {
        const match = userCountElement.textContent.match(/\d+/);
        if (match) {
            return parseInt(match[0]);
        }
    }
    return 0;
    }
    
    // Функция для обновления счетчика пользователей
    function updateUsersCount(count) {
    const userCountElement = document.querySelector('.users-panel-header h3');
    if (userCountElement) {
        userCountElement.textContent = `Участники чата (${count})`;
    }
    }
    
    // Функция для отображения уведомлений
    function showNotification(message, type = 'info') {
    // Создаем элемент уведомления
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Добавляем на страницу
    document.body.appendChild(notification);
    
    // Анимация появления
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Удаляем через некоторое время
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}
