// Файл для работы с аватарами пользователя

document.addEventListener('DOMContentLoaded', function() {
  // Загружаем аватары пользователя при загрузке страницы, если открыты настройки
  if (document.querySelector('.user-settings-container')) {
    loadUserAvatars();
    setupAvatarEventListeners();
  }
});

// Экспортируем функцию, которую можно вызывать извне
window.setupUserAvatars = function() {
  console.log('Setting up user avatars event handlers');
  loadUserAvatars();
  setupAvatarEventListeners();
};

/**
 * Получает токен доступа из cookie
 * @returns {string} Токен доступа или пустая строка, если токен не найден
 */
function getAccessToken() {
  const name = "access_token=";
  const decodedCookie = decodeURIComponent(document.cookie);
  const cookieArray = decodedCookie.split(';');
  for(let i = 0; i < cookieArray.length; i++) {
    let cookie = cookieArray[i].trim();
    if (cookie.indexOf(name) === 0) {
      return cookie.substring(name.length, cookie.length);
    }
  }
  return "";
}

/**
 * Устанавливает обработчики событий для кнопок аватара
 */
function setupAvatarEventListeners() {
  console.log('Setting up avatar event listeners');
  const uploadAvatarBtn = document.querySelector('.upload-avatar-btn');
  const changeAvatarBtn = document.querySelector('.change-avatar-btn');
  
  if (uploadAvatarBtn) {
    console.log('Found upload button:', uploadAvatarBtn);
    uploadAvatarBtn.addEventListener('click', function(e) {
      console.log('Upload avatar button clicked');
      e.stopPropagation();
      showAvatarUploadForm();
    });
  } else {
    console.log('Upload avatar button not found');
  }
  
  if (changeAvatarBtn) {
    console.log('Found change button:', changeAvatarBtn);
    changeAvatarBtn.addEventListener('click', function(e) {
      console.log('Change avatar button clicked');
      e.stopPropagation();
      toggleAvatarsGallery(this);
    });
  } else {
    console.log('Change avatar button not found');
  }
  
  // Добавляем обработчик закрытия формы загрузки по клику вне формы
  document.addEventListener('click', function(e) {
    const uploadForm = document.querySelector('.avatar-upload-form');
    if (uploadForm && !uploadForm.contains(e.target) && e.target.className !== 'upload-avatar-btn') {
      closeAvatarUploadForm();
    }
  });
}

/**
 * Загружает все аватары пользователя и отображает их
 */
async function loadUserAvatars() {
  try {
    // Получаем токен доступа из cookie
    const accessToken = getAccessToken();
    
    const response = await fetch('/users/avatars', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });
    
    if (!response.ok) {
      throw new Error('Не удалось загрузить аватары');
    }
    
    const data = await response.json();
    console.log('Загруженные аватары:', data);
    displayUserAvatars(data);
  } catch (error) {
    console.error('Ошибка при загрузке аватаров:', error);
    
    // Используем глобальную функцию показа уведомлений, если она доступна
    if (typeof showNotification === 'function') {
      showNotification('Ошибка загрузки аватаров', 'error');
    } else if (typeof addFooterMessage === 'function') {
      addFooterMessage('Помилка завантаження аватарів', 'error');
    }
  }
}

/**
 * Отображает аватары пользователя в интерфейсе
 * @param {Array} avatars - массив аватаров
 */
function displayUserAvatars(avatars) {
  const avatarsContainer = document.querySelector('.user_avatar_cloudinary');
  if (!avatarsContainer) return;
  
  // Создаем структуру для отображения аватаров
  avatarsContainer.innerHTML = `
    <div class="avatars-gallery">
      ${avatars.length === 0 ? '<p class="no-avatars">У вас нет загруженных аватаров</p>' : ''}
    </div>
  `;
  
  const avatarsGallery = avatarsContainer.querySelector('.avatars-gallery');
  if (!avatarsGallery || avatars.length === 0) return;
  
  avatars.forEach(avatar => {
    const avatarElement = document.createElement('div');
    avatarElement.className = 'avatar-item';
    avatarElement.dataset.id = avatar.id;
    if (avatar.is_main) {
      avatarElement.classList.add('main-avatar');
    }
    
    avatarElement.innerHTML = `
      <img src="${avatar.file_path}" alt="Аватар пользователя">
      <div class="avatar-actions">
        ${!avatar.is_main ? `<button class="set-main-avatar-btn" data-id="${avatar.id}">Сделать основным</button>` : '<span class="main-badge">Основной</span>'}
        <button class="delete-avatar-btn" data-id="${avatar.id}">Удалить</button>
      </div>
    `;
    
    avatarsGallery.appendChild(avatarElement);
  });
  
  // Добавляем обработчики событий для кнопок
  document.querySelectorAll('.set-main-avatar-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      setMainAvatar(this.dataset.id);
    });
  });
  
  document.querySelectorAll('.delete-avatar-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      deleteAvatar(this.dataset.id);
    });
  });
  
  // Также добавляем возможность выбрать аватар кликом по нему
  document.querySelectorAll('.avatar-item img').forEach(img => {
    img.addEventListener('click', function(e) {
      e.stopPropagation();
      const avatarId = this.closest('.avatar-item').dataset.id;
      if (!this.closest('.avatar-item').classList.contains('main-avatar')) {
        setMainAvatar(avatarId);
      }
    });
  });
}

/**
 * Переключает отображение галереи аватаров
 * @param {HTMLElement} buttonElement - кнопка, которая была нажата
 */
function toggleAvatarsGallery(buttonElement) {
  const avatarsContainer = document.querySelector('.user_avatar_cloudinary');
  if (!avatarsContainer) return;
  
  avatarsContainer.classList.toggle('show-avatars');
  
  if (avatarsContainer.classList.contains('show-avatars')) {
    buttonElement.textContent = 'Сховати аватари';
    loadUserAvatars(); // Обновляем список при показе
  } else {
    buttonElement.textContent = 'Змінити аватар';
  }
}

/**
 * Показывает форму для загрузки аватара
 */
function showAvatarUploadForm() {
  // Удаляем существующую форму, если она есть
  closeAvatarUploadForm();
  
  // Создаем форму для загрузки аватара
  const formHTML = `
    <div class="avatar-upload-form">
      <div class="upload-form-header">
        <h3>Загрузка аватара</h3>
        <button class="close-upload-form-btn">&times;</button>
      </div>
      <div class="upload-form-content">
        <div class="file-input-container">
          <input type="file" id="avatar-file-input" class="file-input" accept="image/*">
          <label for="avatar-file-input" class="file-label">Выбрать файл</label>
        </div>
        <div class="file-preview-container" style="display: none;">
          <img src="" alt="Превью аватара" class="avatar-preview-img">
          <button class="remove-file-btn">Удалить файл</button>
        </div>
        <div class="upload-actions">
          <button class="upload-avatar-submit-btn" disabled>Загрузить</button>
          <button class="cancel-upload-btn">Отменить</button>
        </div>
      </div>
    </div>
  `;
  
  // Добавляем форму в конец документа
  const formContainer = document.createElement('div');
  formContainer.innerHTML = formHTML;
  document.body.appendChild(formContainer.firstElementChild);
  
  // Добавляем обработчики событий
  const form = document.querySelector('.avatar-upload-form');
  const fileInput = document.getElementById('avatar-file-input');
  const previewContainer = document.querySelector('.file-preview-container');
  const previewImg = document.querySelector('.avatar-preview-img');
  const removeFileBtn = document.querySelector('.remove-file-btn');
  const submitBtn = document.querySelector('.upload-avatar-submit-btn');
  const cancelBtn = document.querySelector('.cancel-upload-btn');
  const closeBtn = document.querySelector('.close-upload-form-btn');
  
  fileInput.addEventListener('change', function(e) {
    if (this.files && this.files[0]) {
      const file = this.files[0];
      const reader = new FileReader();
      
      reader.onload = function(e) {
        previewImg.src = e.target.result;
        previewContainer.style.display = 'block';
        submitBtn.disabled = false;
      };
      
      reader.readAsDataURL(file);
    }
  });
  
  removeFileBtn.addEventListener('click', function() {
    fileInput.value = '';
    previewContainer.style.display = 'none';
    submitBtn.disabled = true;
  });
  
  submitBtn.addEventListener('click', function() {
    if (fileInput.files && fileInput.files[0]) {
      uploadAvatar(fileInput.files[0]);
      closeAvatarUploadForm();
    }
  });
  
  cancelBtn.addEventListener('click', closeAvatarUploadForm);
  closeBtn.addEventListener('click', closeAvatarUploadForm);
}

/**
 * Закрывает форму для загрузки аватара
 */
function closeAvatarUploadForm() {
  const form = document.querySelector('.avatar-upload-form');
  if (form) {
    form.remove();
  }
}

/**
 * Загружает аватар на сервер
 * @param {File} file - файл изображения
 */
async function uploadAvatar(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    // Показываем индикатор загрузки
    showLoading(true, 'Загрузка аватара...');
    
    // Получаем токен доступа из cookie
    const accessToken = getAccessToken();
    
    // Используем FormData для загрузки файла
    const response = await fetch('/users/avatars/upload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      },
      body: formData
    });
    
    // Скрываем индикатор загрузки
    showLoading(false);
    
    if (!response.ok) {
      throw new Error('Не удалось загрузить аватар');
    }
    
    const data = await response.json();
    console.log('Ответ при загрузке аватара:', data);
    
    // Используем доступные функции для уведомлений
    if (typeof showNotification === 'function') {
      showNotification('Аватар успешно загружен', 'success');
    } else if (typeof addFooterMessage === 'function') {
      addFooterMessage('Аватар успішно завантажено', 'success');
    }
    
    // Обновляем аватар в превью если это первый аватар или если он сделан основным
    if (!data.is_main && data.file_path) {
      updateUserAvatarPreview(data.file_path);
    }
    
    // Перезагружаем список аватаров и показываем галерею
    loadUserAvatars();
    document.querySelector('.user_avatar_cloudinary').classList.add('show-avatars');
    const changeAvatarBtn = document.querySelector('.change-avatar-btn');
    if (changeAvatarBtn) {
      changeAvatarBtn.textContent = 'Сховати аватари';
    }
    
  } catch (error) {
    console.error('Ошибка при загрузке аватара:', error);
    
    // Скрываем индикатор загрузки
    showLoading(false);
    
    if (typeof showNotification === 'function') {
      showNotification('Ошибка загрузки аватара', 'error');
    } else if (typeof addFooterMessage === 'function') {
      addFooterMessage('Помилка завантаження аватара', 'error');
    }
  }
}

/**
 * Показывает или скрывает индикатор загрузки
 * @param {boolean} show - показать или скрыть индикатор
 * @param {string} message - сообщение для отображения
 */
function showLoading(show, message = 'Загрузка...') {
  const existingLoader = document.querySelector('.loading-indicator');
  
  if (show) {
    // Если индикатор уже существует, просто обновляем сообщение
    if (existingLoader) {
      existingLoader.textContent = message;
      return;
    }
    
    // Иначе создаем новый индикатор
    const loader = document.createElement('div');
    loader.className = 'loading-indicator';
    loader.textContent = message;
    document.body.appendChild(loader);
  } else {
    // Удаляем индикатор если он существует
    if (existingLoader) {
      existingLoader.remove();
    }
  }
}

/**
 * Обновляет превью аватара в интерфейсе
 * @param {string} avatarUrl - URL аватара
 */
function updateUserAvatarPreview(avatarUrl) {
  const avatarPreview = document.querySelector('.avatar-preview img');
  if (avatarPreview) {
    avatarPreview.src = avatarUrl;
  }
}

/**
 * Устанавливает аватар как основной
 * @param {string} avatarId - ID аватара
 */
async function setMainAvatar(avatarId) {
  try {
    // Показываем индикатор загрузки
    showLoading(true, 'Установка основного аватара...');
    
    // Получаем токен доступа из cookie
    const accessToken = getAccessToken();
    
    const response = await fetch(`/users/avatars/${avatarId}/set-main`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    // Скрываем индикатор загрузки
    showLoading(false);
    
    if (!response.ok) {
      throw new Error('Не удалось установить основной аватар');
    }
    
    // Показываем уведомление
    if (typeof showNotification === 'function') {
      showNotification('Аватар установлен как основной', 'success');
    } else if (typeof addFooterMessage === 'function') {
      addFooterMessage('Аватар встановлено як основний', 'success');
    }
    
    // Обновляем аватар в превью и отмечаем его как основной
    const avatarItem = document.querySelector(`.avatar-item[data-id="${avatarId}"]`);
    if (avatarItem && avatarItem.querySelector('img')) {
      updateUserAvatarPreview(avatarItem.querySelector('img').src);
      
      // Убираем отметку основного со всех аватаров
      document.querySelectorAll('.avatar-item').forEach(item => {
        item.classList.remove('main-avatar');
      });
      
      // Отмечаем текущий аватар как основной
      avatarItem.classList.add('main-avatar');
    }
    
    // Перезагружаем список для обновления статусов
    loadUserAvatars();
    
    // Обновляем аватар в главном меню, если есть функция
    // Функция loadUserProfile должна быть определена в другом файле
    const avatarInMenu = document.querySelector('.avatar-in-menu img');
    if (avatarInMenu && typeof loadUserProfile === 'function') {
      loadUserProfile();
    }
  } catch (error) {
    console.error('Ошибка при установке основного аватара:', error);
    
    // Скрываем индикатор загрузки
    showLoading(false);
    
    if (typeof showNotification === 'function') {
      showNotification('Ошибка установки основного аватара', 'error');
    } else if (typeof addFooterMessage === 'function') {
      addFooterMessage('Помилка встановлення основного аватара', 'error');
    }
  }
}

/**
 * Удаляет аватар
 * @param {string} avatarId - ID аватара
 */
async function deleteAvatar(avatarId) {
  if (!confirm('Ви впевнені, що хочете видалити цей аватар?')) {
    return;
  }
  
  try {
    // Показываем индикатор загрузки
    showLoading(true, 'Удаление аватара...');
    
    // Получаем токен доступа из cookie
    const accessToken = getAccessToken();
    
    const response = await fetch(`/users/avatars/${avatarId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    // Скрываем индикатор загрузки
    showLoading(false);
    
    if (!response.ok) {
      throw new Error('Не удалось удалить аватар');
    }
    
    // Показываем уведомление
    if (typeof showNotification === 'function') {
      showNotification('Аватар успешно удален', 'success');
    } else if (typeof addFooterMessage === 'function') {
      addFooterMessage('Аватар успішно видалено', 'success');
    }
    
    loadUserAvatars(); // Перезагружаем список аватаров
    
    // Если удалили текущий аватар в меню, обновляем интерфейс
    const avatarInMenu = document.querySelector('.avatar-in-menu img');
    if (avatarInMenu && typeof loadUserProfile === 'function') {
      loadUserProfile();
    }
    
  } catch (error) {
    console.error('Ошибка при удалении аватара:', error);
    
    // Скрываем индикатор загрузки
    showLoading(false);
    
    if (typeof showNotification === 'function') {
      showNotification('Ошибка удаления аватара', 'error');
    } else if (typeof addFooterMessage === 'function') {
      addFooterMessage('Помилка видалення аватара', 'error');
    }
  }
}