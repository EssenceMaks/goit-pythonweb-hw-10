// Файл для работы с настройками пользователя

document.addEventListener('DOMContentLoaded', function() {
  // Находим ссылку настроек в меню
  const settingsLink = document.querySelector('.settings-link');
  if (settingsLink) {
    settingsLink.addEventListener('click', function(e) {
      e.preventDefault(); // Предотвращаем переход по ссылке
      
      // Здесь очистка поиска нужна, т.к. это первоначальная загрузка настроек
      const searchInput = document.getElementById('contact-search');
      if (searchInput) {
        // Сохраняем оригинальное значение поиска, чтобы восстановить его при необходимости
        window._savedSearchValue = searchInput.value;
        searchInput.value = '';
        
        // Обновляем URL без параметра поиска
        const currentUrl = new URL(window.location.href);
        if (currentUrl.searchParams.has('search')) {
          currentUrl.searchParams.delete('search');
          history.replaceState({}, '', currentUrl);
        }
      }
      
      renderUserSettings();
    });
  }
});

// Глобальная переменная для хранения данных пользователя
let currentUserData = null;

// Функция для отображения настроек пользователя
async function renderUserSettings() {
  const contactsList = document.getElementById('contacts-list');
  if (!contactsList) return;
  
  // Сбрасываем глобальные состояния (если используются переменные из contacts.js)
  if (typeof birthdayMode !== 'undefined') birthdayMode = false;
  if (typeof expandedContactId !== 'undefined') expandedContactId = null;
  
  try {
    // Получаем информацию о текущем пользователе
    const userData = await authorizedFetch('/users/me');
    console.log('Получены данные пользователя:', userData);
    
    // Если данные о пользователе не загрузились, используем запасные данные из глобальных переменных
    if (!userData) {
      console.warn('Не удалось загрузить данные пользователя из API, используем данные из сессии');
      
      // Используем глобальные переменные, установленные в index.html как запасной вариант
      currentUserData = {
        id: window.currentUserId,
        username: window.currentUsername,
        email: window.currentEmail,
        role: window.userRole
      };
    } else {
      // Сохраняем данные пользователя в глобальную переменную
      currentUserData = userData;
    }
    
    // Создаем шаблон настроек пользователя
    const settingsTemplate = `
      <div class="user-settings-container" id="settings-container">
        <div class="settings-header">
          <button id="back-to-contacts-btn" class="back-btn">← Повернутися до контактів</button>
          <h2>Налаштування користувача</h2>
        </div>
        
        <div class="settings-form">
          <div class="settings-row">
            <div class="settings-label">Email:</div>
            <div class="settings-value">${currentUserData.email || ''}</div>
            <div class="settings-action">
              <span class="email-note">(Змінити неможливо)</span>
            </div>
          </div>
          
          <div class="settings-row" id="username-row">
            <div class="settings-label">Ім'я користувача:</div>
            <div class="settings-value">${currentUserData.username || ''}</div>
            <div class="settings-action">
              <button class="edit-username-btn">Редагувати</button>
            </div>
          </div>
          
          <div class="settings-row" id="password-row">
            <div class="settings-label">Пароль:</div>
            <div class="settings-value">********</div>
            <div class="settings-action">
              <button class="edit-password-btn">Змінити пароль</button>
              <button class="reset-password-btn">Скинути пароль</button>
            </div>
          </div>
          
          <div class="settings-row">
            <div class="settings-label">Аватар:</div>
            <div class="settings-value">
              <div class="avatar-preview">
                <img src="${currentUserData.avatar_url || '/static/menu/img/user_1.png'}" alt="Аватар користувача">
              </div>
            </div>
            <div class="settings-action">
              <button class="change-avatar-btn">Змінити аватар</button>
            </div>
          </div>
        </div>
      </div>
    `;
    
    // Устанавливаем шаблон настроек в блок контактов
    contactsList.innerHTML = settingsTemplate;
    contactsList.setAttribute('data-mode', 'settings');
    
    // Добавляем обработчики событий для кнопок
    setupSettingsEventHandlers();
    
    // Предотвращаем сброс страницы при клике внутри контейнера настроек
    const container = document.getElementById('settings-container');
    if (container) {
      container.addEventListener('click', function(e) {
        e.stopPropagation(); // Останавливаем всплытие события
      });
    }
    
  } catch (error) {
    console.error('Ошибка при загрузке данных пользователя:', error);
    contactsList.innerHTML = '<div class="error-message">Помилка при завантаженні налаштувань користувача</div>';
  }
}

// Настройка обработчиков событий для кнопок в настройках
function setupSettingsEventHandlers() {
  // Кнопка возврата к контактам
  const backBtn = document.getElementById('back-to-contacts-btn');
  if (backBtn) {
    backBtn.addEventListener('click', function() {
      const contactsList = document.getElementById('contacts-list');
      if (contactsList) {
        contactsList.removeAttribute('data-mode');
      }
      
      // Восстанавливаем значение поиска, если оно было сохранено
      if (window._savedSearchValue) {
        const searchInput = document.getElementById('contact-search');
        if (searchInput) {
          searchInput.value = window._savedSearchValue;
          delete window._savedSearchValue;
        }
      }
      
      // Используем функции из contacts.js для возврата к отображению контактов
      if (typeof resetContactsUI === 'function') resetContactsUI();
      if (typeof fetchAndRenderContacts === 'function') fetchAndRenderContacts();
    });
  }
  
  // Редактирование имени пользователя
  const editUsernameBtn = document.querySelector('.edit-username-btn');
  if (editUsernameBtn) {
    editUsernameBtn.addEventListener('click', function(e) {
      e.stopPropagation(); // Предотвращаем всплытие события
      showUsernameEditForm();
    });
  }
  
  // Изменение пароля
  const editPasswordBtn = document.querySelector('.edit-password-btn');
  if (editPasswordBtn) {
    editPasswordBtn.addEventListener('click', function(e) {
      e.stopPropagation(); // Предотвращаем всплытие события
      showPasswordEditForm();
    });
  }
  
  // Сброс пароля - перенаправляем на страницу /forgot с автозаполненным email
  const resetPasswordBtn = document.querySelector('.reset-password-btn');
  if (resetPasswordBtn) {
    resetPasswordBtn.addEventListener('click', function(e) {
      e.stopPropagation(); // Предотвращаем всплытие события
      
      // Проверяем, есть ли у нас данные о пользователе
      if (currentUserData && currentUserData.email) {
        if (confirm('Ви дійсно хочете скинути пароль? Вас буде вилогінено з системи, і на вашу пошту буде відправлено посилання для встановлення нового пароля.')) {
          // Формируем URL с параметром email для страницы /forgot
          const forgotUrl = `/forgot?email=${encodeURIComponent(currentUserData.email)}`;
          
          // Выходим из системы и перенаправляем на страницу сброса пароля
          authorizedFetch('/logout', { method: 'GET' })
            .then(() => {
              // Удаляем куки с токеном
              document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
              // Перенаправляем на страницу забытого пароля
              window.location.href = forgotUrl;
            })
            .catch((error) => {
              console.error('Ошибка при выходе из системы:', error);
              // Даже при ошибке перенаправляем на страницу сброса пароля
              window.location.href = forgotUrl;
            });
        }
      } else {
        alert('Не вдалося отримати адресу електронної пошти. Спробуйте перезавантажити сторінку або скористатися сторінкою відновлення пароля вручну.');
      }
    });
  }
  
  // Изменение аватара
  const changeAvatarBtn = document.querySelector('.change-avatar-btn');
  if (changeAvatarBtn) {
    changeAvatarBtn.addEventListener('click', function(e) {
      e.stopPropagation(); // Предотвращаем всплытие события
      // Заглушка для будущей функциональности
      alert('Функціонал зміни аватара буде доступний незабаром');
    });
  }
}

// Функция для отображения формы редактирования имени пользователя
function showUsernameEditForm() {
  const usernameRow = document.getElementById('username-row');
  if (!usernameRow) return;
  
  const currentUsername = currentUserData ? currentUserData.username : '';
  
  // Заменяем содержимое строки на форму редактирования
  usernameRow.innerHTML = `
    <div class="settings-label">Ім'я користувача:</div>
    <div class="settings-value">
      <input type="text" id="new-username" value="${currentUsername}" class="settings-input" autofocus>
    </div>
    <div class="settings-action">
      <button id="save-username-btn" class="save-btn">Підтвердити</button>
      <button id="cancel-username-btn" class="cancel-btn">Відміна</button>
    </div>
  `;
  
  // Добавляем обработчики для новых кнопок
  const saveBtn = document.getElementById('save-username-btn');
  const cancelBtn = document.getElementById('cancel-username-btn');
  const usernameInput = document.getElementById('new-username');
  
  // Предотвращаем сброс при клике на элементы формы
  if (usernameInput) {
    usernameInput.addEventListener('click', function(e) {
      e.stopPropagation();
    });
    
    // Фокусируемся на поле ввода и выделяем текст
    setTimeout(() => {
      usernameInput.focus();
      usernameInput.select();
    }, 0);
    
    // Добавляем обработчик нажатия Enter для сохранения
    usernameInput.addEventListener('keypress', function(e) {
      e.stopPropagation();
      if (e.key === 'Enter') {
        saveUsername();
      }
    });
  }
  
  if (saveBtn) {
    saveBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      saveUsername();
    });
  }
  
  if (cancelBtn) {
    cancelBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      // Отменяем редактирование и восстанавливаем отображение
      renderUserSettings();
    });
  }
}

// Функция для сохранения нового имени пользователя
async function saveUsername() {
  const newUsername = document.getElementById('new-username').value.trim();
  
  if (!newUsername) {
    alert('Ім\'я користувача не може бути порожнім');
    return;
  }
  
  try {
    // Отправляем запрос на изменение имени пользователя
    const response = await authorizedFetch('/users/update/username', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username: newUsername })
    });
    
    // Обновляем глобальную переменную с именем пользователя
    if (typeof window.currentUsername !== 'undefined') {
      window.currentUsername = newUsername;
    }
    if (currentUserData) {
      currentUserData.username = newUsername;
    }
    
    // Обновляем отображение после успешного изменения
    renderUserSettings();
    
    if (typeof addFooterMessage === 'function') {
      addFooterMessage('Ім\'я користувача успішно оновлено', 'success');
    } else {
      alert('Ім\'я користувача успішно оновлено');
    }
  } catch (error) {
    console.error('Ошибка при обновлении имени пользователя:', error);
    alert('Помилка при оновленні імені користувача');
  }
}

// Функция для отображения формы изменения пароля
function showPasswordEditForm() {
  const passwordRow = document.getElementById('password-row');
  if (!passwordRow) return;
  
  // Заменяем содержимое строки на форму редактирования
  passwordRow.innerHTML = `
    <div class="settings-label">Пароль:</div>
    <div class="settings-value">
      <div class="password-edit-form">
        <div class="form-group">
          <label for="current-password">Поточний пароль:</label>
          <input type="password" id="current-password" class="settings-input" required autocomplete="new-password" data-form-type="other" data-lpignore="true">
        </div>
        <div class="form-group">
          <label for="new-password">Новий пароль:</label>
          <input type="password" id="new-password" class="settings-input" required minlength="6" autocomplete="new-password" data-form-type="other" data-lpignore="true">
        </div>
        <div class="form-group">
          <label for="confirm-password">Підтвердіть новий пароль:</label>
          <input type="password" id="confirm-password" class="settings-input" required minlength="6" autocomplete="new-password" data-form-type="other" data-lpignore="true">
        </div>
      </div>
    </div>
    <div class="settings-action password-edit-actions">
      <button id="save-password-btn" class="save-btn">Підтвердити</button>
      <button id="cancel-password-btn" class="cancel-btn">Відміна</button>
    </div>
  `;
  
  // Предотвращаем сброс при клике на элементы формы
  const inputs = passwordRow.querySelectorAll('input');
  inputs.forEach(input => {
    input.addEventListener('click', function(e) {
      e.stopPropagation();
    });
  });
  
  // Фокусируемся на первом поле ввода
  const currentPasswordInput = document.getElementById('current-password');
  if (currentPasswordInput) {
    setTimeout(() => {
      currentPasswordInput.focus();
    }, 0);
  }
  
  // Добавляем обработчики для новых кнопок
  const saveBtn = document.getElementById('save-password-btn');
  const cancelBtn = document.getElementById('cancel-password-btn');
  
  if (saveBtn) {
    saveBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      savePassword();
    });
  }
  
  if (cancelBtn) {
    cancelBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      
      // Отменяем редактирование и восстанавливаем отображение
      renderUserSettings();
    });
  }
}

// Функция для сохранения нового пароля
async function savePassword() {
  const currentPassword = document.getElementById('current-password').value;
  const newPassword = document.getElementById('new-password').value;
  const confirmPassword = document.getElementById('confirm-password').value;
  
  if (!currentPassword || !newPassword || !confirmPassword) {
    alert('Всі поля повинні бути заповнені');
    return;
  }
  
  if (newPassword !== confirmPassword) {
    alert('Новий пароль і підтвердження не співпадають');
    return;
  }
  
  if (newPassword.length < 6) {
    alert('Новий пароль повинен містити не менше 6 символів');
    return;
  }
  
  try {
    // Отправляем запрос на изменение пароля
    const response = await authorizedFetch('/users/update/password', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        current_password: currentPassword,
        new_password: newPassword
      })
    });
    
    // Обновляем отображение после успешного изменения
    renderUserSettings();
    
    // Ждем немного перед показом сообщения
    setTimeout(() => {
      if (typeof addFooterMessage === 'function') {
        addFooterMessage('Пароль успішно змінено', 'success');
      } else {
        alert('Пароль успішно змінено');
      }
    }, 100);
    
  } catch (error) {
    console.error('Ошибка при изменении пароля:', error);
    alert('Помилка при зміні пароля. Можливо, поточний пароль введено невірно.');
  }
}

// Функция для сброса пароля
async function initiatePasswordReset() {
  if (confirm('Ви впевнені, що хочете скинути пароль? На вашу електронну пошту буде відправлено посилання для встановлення нового пароля.')) {
    try {
      // Отправляем запрос на сброс пароля
      const response = await authorizedFetch('/password/reset', {
        method: 'POST'
      });
      
      if (typeof addFooterMessage === 'function') {
        addFooterMessage('Посилання для скидання пароля відправлено на вашу електронну пошту', 'success');
      } else {
        alert('Посилання для скидання пароля відправлено на вашу електронну пошту');
      }
    } catch (error) {
      console.error('Ошибка при запросе сброса пароля:', error);
      alert('Помилка при запиті на скидання пароля');
    }
  }
}