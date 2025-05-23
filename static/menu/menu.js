// JS для меню

// Открытие попапа создания контакта
function openPopup(id) {
  document.getElementById(id).style.display = 'block';
}
function closePopup(id) {
  document.getElementById(id).style.display = 'none';
}

// --- Функция для загрузки профиля пользователя и обновления аватара в меню ---
async function loadUserProfile() {
  try {
    console.log('Загрузка профиля пользователя для аватара в меню...');
    
    // Проверяем наличие функции для выполнения авторизованных запросов
    const fetchFunction = window.authorizedFetch || window.authorizedRequest;
    
    if (!fetchFunction) {
      console.error('Функции authorizedFetch или authorizedRequest не найдены!');
      return;
    }
    
    // Выполняем запрос к API для получения информации о текущем пользователе
    const userData = await fetchFunction('/users/me');
    
    if (!userData) {
      console.error('Не удалось получить данные пользователя для обновления аватара');
      return;
    }
    
    console.log('Получены данные пользователя для аватара:', userData);
    
    // Обновляем аватар в меню, если он есть
    if (userData.avatar_url) {
      const menuAvatarElement = document.querySelector('.avatar-section img');
      if (menuAvatarElement) {
        menuAvatarElement.src = userData.avatar_url;
        menuAvatarElement.alt = userData.username || 'User Avatar';
      }
    }
    
    // Обновляем имя пользователя в меню
    if (userData.username) {
      // Обновляем имя в выпадающем меню
      const usernameInMenu = document.querySelector('.username-in-menu');
      if (usernameInMenu) {
        usernameInMenu.textContent = userData.username;
      }
      
      // Обновляем имя в блоке верхнего меню (div.user-info .username)
      const usernameElement = document.querySelector('.user-info .username');
      if (usernameElement) {
        usernameElement.textContent = userData.username;
      }
      
      // Обновляем глобальную переменную с именем пользователя, если она существует
      if (typeof window.currentUsername !== 'undefined') {
        window.currentUsername = userData.username;
      }
    }
    
  } catch (error) {
    console.error('Ошибка при загрузке профиля пользователя:', error);
  }
}

// Экспортируем функцию для использования в других модулях
window.loadUserProfile = loadUserProfile;

// --- Логика для сообщений в футере ---
function addFooterMessage(msg, type = 'info') {
  let log = JSON.parse(localStorage.getItem('footerLog') || '[]');
  log.push({msg, type, ts: Date.now()});
  localStorage.setItem('footerLog', JSON.stringify(log));
  renderFooterMessages();
}
function renderFooterMessages(showAll = false) {
  let log = JSON.parse(localStorage.getItem('footerLog') || '[]');
  const footer = document.getElementById('footer-message');
  const btn = document.getElementById('footer-log-toggle');
  if (!footer) return;
  if (!log.length) {
    footer.style.display = 'none';
    if (btn) btn.style.display = 'none';
    return;
  }
  footer.style.display = 'block';
  let toShow = showAll ? log.slice(-15) : log.slice(-5);
  // Новые сверху
  toShow = toShow.reverse();
  footer.innerHTML = toShow.map(l => `<div class="footer-row ${l.type}">${l.msg}</div>`).join('');
  if (btn) {
    btn.style.display = log.length > 5 ? 'inline-block' : 'none';
    btn.textContent = showAll ? 'Скрыть' : 'Показать все';
    btn.onclick = () => {
      footer.classList.toggle('expanded', !showAll);
      renderFooterMessages(!showAll);
    };
    // Управляем высотой футера
    footer.classList.toggle('expanded', showAll);
  }
  // Скроллим к последнему сообщению, если expanded
  if (showAll) footer.scrollTop = footer.scrollHeight;
}
window.addFooterMessage = addFooterMessage;
window.renderFooterMessages = renderFooterMessages;
document.addEventListener('DOMContentLoaded', ()=>renderFooterMessages());

// --- Модификация checkDBState для футера ---
async function checkDBState() {
  try {
    console.log('Проверка состояния базы данных...');
    
    // Используем обновленную функцию getAuthHeader для получения заголовка авторизации
    const authHeader = getAuthHeader();
    
    const response = await fetch('/db/check-state', {
      method: 'GET',
      headers: {
        ...authHeader,
        'Accept': 'application/json'
      },
      credentials: 'include' // Важно для включения cookies
    });
    
    if (!response.ok) {
      console.error('Ошибка при проверке состояния БД:', response.statusText);
      return;
    }
    
    const resp = await response.json();
    
    if (resp.status === 'no_db' || resp.status === 'no_tables' || resp.status === 'no_contacts') {
      addFooterMessage(resp.message, resp.status === 'no_db' ? 'error' : 'warn');
    } else if (resp.status === 'ok') {
      addFooterMessage(`Контактів у базі: ${resp.count}`, 'success');
    } else if (resp.status === 'noenv') {
      addFooterMessage(resp.message, 'error');
    }
  } catch (e) {
    console.error('Ошибка при проверке состояния базы данных:', e);
  }
}

// Получение токена для авторизованных запросов
function getAuthHeader() {
  const tokenMatch = document.cookie.match(/access_token=([^;]*)/);
  if (!tokenMatch) return {};
  
  // Токен может быть уже с префиксом "Bearer " или без него
  const tokenValue = tokenMatch[1];
  if (tokenValue.startsWith('Bearer ')) {
    return {'Authorization': tokenValue};
  } else {
    return {'Authorization': `Bearer ${tokenValue}`};
  }
}

// Обновленная функция для выполнения авторизованных запросов
async function authorizedRequest(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...getAuthHeader(),
        'Content-Type': 'application/json',
        ...options.headers
      },
      credentials: 'include' // Включаем cookies
    });
    
    if (!response.ok) {
      console.error(`Ошибка запроса ${url}:`, response.statusText);
      return null;
    }
    
    return await response.json();
  } catch (error) {
    console.error(`Ошибка при запросе ${url}:`, error);
    return null;
  }
}

// Вывод сообщения в футер
function showFooterMessage(msg, type = 'info') {
  addFooterMessage(msg, type);
}

// --- Глобальная функция для сброса фильтров и обновления контактов ---
window.resetAndRenderContacts = function() {
  // Сбросить фильтры поиска, сортировки, дней рождения
  if (window.resetContactsUI) window.resetContactsUI();
  if (window.fetchAndRenderContacts) window.fetchAndRenderContacts();
};

// Кнопки меню для работы с БД
document.addEventListener('DOMContentLoaded', function() {
  // Проверяем наличие функции authorizedFetch перед вызовом checkDBState
  if (window.authorizedFetch) {
    checkDBState();
    
    // Загружаем профиль пользователя при загрузке страницы
    loadUserProfile();
  } else {
    console.error('authorizedFetch не найден! Убедитесь, что auth.js загружен до menu.js');
    setTimeout(() => {
      if (window.authorizedFetch) {
        console.log('authorizedFetch появился с задержкой, выполняем checkDBState');
        checkDBState();
        
        // Загружаем профиль пользователя с задержкой
        loadUserProfile();
      }
    }, 500);
  }
  
  const btnCreate = document.getElementById('btn-create-contact');
  if (btnCreate) {
    btnCreate.addEventListener('click', function() {
      openPopup('popup-create-contact');
    });
  }

  const btnCreateDB = document.getElementById('btn-create-db');
  const btnInit = document.getElementById('btn-init');
  const btnDropDB = document.getElementById('btn-drop-db');
  const btnFill = document.getElementById('btn-fill');
  const btnClear = document.getElementById('btn-clear');

  if (btnCreateDB) {
    btnCreateDB.addEventListener('click', async function() {
      btnCreateDB.disabled = true;
      addFooterMessage('Создание базы...', 'info');
      try {
        // 1. Создать базу - используем authorizedRequest
        const resp = await authorizedRequest('/db/create-db', {method:'POST'});
        if (!resp) {
          addFooterMessage('Ошибка авторизации при создании базы', 'error');
          btnCreateDB.disabled = false;
          return;
        }
        
        if (resp.status === 'created' || resp.status === 'exists') {
          addFooterMessage(resp.message, 'success');
          // 2. Инициализировать таблицы - используем authorizedRequest
          const resp2 = await authorizedRequest('/db/init', {method:'POST'});
          if (!resp2) {
            addFooterMessage('Ошибка авторизации при инициализации таблиц', 'error');
            btnCreateDB.disabled = false;
            return;
          }
          
          if (resp2.status === 'created' || resp2.status === 'exists') {
            addFooterMessage('База и таблицы готовы!', 'success');
            window.resetAndRenderContacts();
          } else {
            addFooterMessage('Ошибка инициализации таблиц', 'error');
          }
        } else if (resp.status === 'noenv') {
          addFooterMessage(resp.message, 'error');
        } else {
          addFooterMessage(resp.message || 'Ошибка создания базы', 'error');
        }
      } catch (e) {
        console.error('Ошибка при создании базы:', e);
        addFooterMessage('Ошибка при создании базы: ' + e.message, 'error');
      }
      btnCreateDB.disabled = false;
    });
    btnCreateDB.addEventListener('click', ()=>setTimeout(checkDBState, 1000));
  }

  if (btnDropDB) {
    btnDropDB.addEventListener('click', async function() {
      if (!confirm('Вы уверены, что хотите УДАЛИТЬ базу данных полностью?')) return;
      btnDropDB.disabled = true;
      addFooterMessage('Удаление базы...', 'info');
      try {
        // Используем authorizedRequest
        const resp = await authorizedRequest('/db/drop-db', {method:'POST'});
        if (!resp) {
          addFooterMessage('Ошибка авторизации при удалении базы', 'error');
          btnDropDB.disabled = false;
          return;
        }
        
        if (resp.status === 'dropped') {
          addFooterMessage(resp.message, 'success');
          window.resetAndRenderContacts();
        } else {
          addFooterMessage(resp.message || 'Ошибка удаления базы', 'error');
        }
      } catch (e) {
        console.error('Ошибка при удалении базы:', e);
        addFooterMessage('Ошибка при удалении базы: ' + e.message, 'error');
      }
      btnDropDB.disabled = false;
    });
    btnDropDB.addEventListener('click', ()=>setTimeout(checkDBState, 1000));
  }

  if (btnInit) {
    btnInit.addEventListener('click', async function() {
      btnInit.disabled = true;
      try {
        // Используем authorizedRequest
        const resp = await authorizedRequest('/db/init', {method:'POST'});
        if (!resp) {
          addFooterMessage('Ошибка авторизации при инициализации базы', 'error');
          btnInit.disabled = false;
          return;
        }
        
        addFooterMessage('База успешно инициализирована', 'success');
        window.resetAndRenderContacts();
      } catch (e) {
        console.error('Ошибка при инициализации базы:', e);
        addFooterMessage('Ошибка сети при инициализации: ' + e.message, 'error');
      }
      btnInit.disabled = false;
    });
  }

  if (btnFill) {
    btnFill.addEventListener('click', async function() {
      btnFill.disabled = true;
      try {
        // Используем authorizedRequest
        const resp = await authorizedRequest('/db/fill-fake?n=10', {method:'POST'});
        if (!resp) {
          addFooterMessage('Ошибка авторизации при добавлении контактов', 'error');
          btnFill.disabled = false;
          return;
        }
        
        addFooterMessage('Контакты успешно добавлены', 'success');
        window.resetAndRenderContacts();
      } catch (e) {
        console.error('Ошибка при добавлении контактов:', e);
        addFooterMessage('Ошибка сети при добавлении: ' + e.message, 'error');
      }
      btnFill.disabled = false;
    });
  }

  if (btnClear) {
    btnClear.addEventListener('click', async function() {
      btnClear.disabled = true;
      try {
        // Используем authorizedRequest
        const resp = await authorizedRequest('/db/clear', {method:'POST'});
        if (!resp) {
          addFooterMessage('Ошибка авторизации при удалении контактов', 'error');
          btnClear.disabled = false;
          return;
        }
        
        addFooterMessage('Все контакты удалены', 'success');
        window.resetAndRenderContacts();
      } catch (e) {
        console.error('Ошибка при удалении контактов:', e);
        addFooterMessage('Ошибка сети при удалении: ' + e.message, 'error');
      }
      btnClear.disabled = false;
    });
    btnClear.addEventListener('click', ()=>setTimeout(checkDBState, 1000));
  }
});

// Функции для управления несколькими аккаунтами
let knownAccounts = [];

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Добавление обработчика клика для выпадающего меню
    const accountDropdown = document.querySelector('.account-dropdown');
    if (accountDropdown) {
        accountDropdown.addEventListener('click', function(e) {
            // Предотвращаем всплытие события
            e.stopPropagation();
            
            // Переключаем видимость выпадающего меню
            const dropdownContent = this.querySelector('.dropdown-content');
            if (dropdownContent) {
                dropdownContent.classList.toggle('show');
            }
        });
    }
    
    // Закрываем меню при клике вне его
    document.addEventListener('click', function() {
        const dropdownContent = document.querySelector('.dropdown-content');
        if (dropdownContent && dropdownContent.classList.contains('show')) {
            dropdownContent.classList.remove('show');
        }
    });
    
    // Загрузка сохраненных аккаунтов из localStorage
    loadKnownAccounts();
    
    // Проверяем текущего пользователя и добавляем его в список
    const currentUser = {
        id: window.currentUserId || '',
        username: window.currentUsername || '',
        email: window.currentEmail || '',
        role: window.userRole || 'user'
    };
    
    console.log("Текущий пользователь:", currentUser);
    
    // Если у нас есть данные о текущем пользователе, добавляем его в список известных аккаунтов
    if (currentUser.id && (currentUser.email || currentUser.username)) {
        addToKnownAccounts(currentUser);
    }
    
    // Обновляем дропдаун меню
    updateAccountsDropdown();
});

// Загрузка известных аккаунтов из localStorage
function loadKnownAccounts() {
    const savedAccounts = localStorage.getItem('knownAccounts');
    if (savedAccounts) {
        try {
            knownAccounts = JSON.parse(savedAccounts);
            console.log('Загружены сохраненные аккаунты:', knownAccounts);
        } catch (e) {
            console.error('Ошибка при загрузке сохраненных аккаунтов:', e);
            knownAccounts = [];
        }
    } else {
        knownAccounts = [];
    }
}

// Сохранение списка аккаунтов в localStorage
function saveKnownAccounts() {
    localStorage.setItem('knownAccounts', JSON.stringify(knownAccounts));
}

// Добавление аккаунта в список известных
function addToKnownAccounts(account) {
    // Проверяем, есть ли уже такой аккаунт в списке
    const existingAccountIndex = knownAccounts.findIndex(acc => acc.id === account.id);
    
    if (existingAccountIndex !== -1) {
        // Обновляем существующий аккаунт
        knownAccounts[existingAccountIndex] = {
            ...knownAccounts[existingAccountIndex],
            ...account
        };
    } else {
        // Добавляем новый аккаунт
        knownAccounts.push(account);
    }
    
    // Сохраняем обновленный список
    saveKnownAccounts();
}

// Обновление выпадающего меню с аккаунтами
function updateAccountsDropdown() {
    const dropdownContent = document.querySelector('.dropdown-content');
    if (!dropdownContent) return;
    
    // Очищаем текущее содержимое
    dropdownContent.innerHTML = '';
    
    console.log('Обновление выпадающего меню аккаунтов:', knownAccounts);
    
    // Добавляем каждый известный аккаунт
    knownAccounts.forEach(account => {
        // Проверяем наличие ID для сравнения
        const isCurrentAccount = account.id === window.currentUserId;
        
        // Обрезаем длинный email до 15 символов и добавляем многоточие
        let displayName = account.email || account.username || 'Неизвестный пользователь';
        if (displayName.length > 15) {
            displayName = displayName.substring(0, 15) + '...';
        }
        
        const accountItem = document.createElement('div');
        accountItem.className = 'account-item' + (isCurrentAccount ? ' active-account' : '');
        accountItem.innerHTML = `
            <div class="account-info">
                <div class="account-name">${displayName}</div>
                <div class="account-role">${account.role || 'user'}</div>
            </div>
            ${isCurrentAccount ? '<div class="current-marker">✓</div>' : ''}
        `;
        
        // Добавляем обработчик клика для переключения на этот аккаунт
        if (!isCurrentAccount) {
            accountItem.addEventListener('click', () => switchAccount(account));
        }
        
        dropdownContent.appendChild(accountItem);
    });
    
    // Добавляем разделитель, если есть какие-то аккаунты
    if (knownAccounts.length > 0) {
        const divider = document.createElement('div');
        divider.className = 'dropdown-divider';
        dropdownContent.appendChild(divider);
    }
    
    // Добавляем кнопку "Add Login"
    const addLoginLink = document.createElement('a');
    addLoginLink.href = '/login';
    addLoginLink.className = 'add-login-link';
    addLoginLink.textContent = 'Add Login';
    dropdownContent.appendChild(addLoginLink);
}

// Переключение на другой аккаунт
function switchAccount(account) {
    // Предотвращаем всплытие события клика
    event.stopPropagation();
    
    // Здесь отправляем запрос на сервер для переключения на выбранный аккаунт
    window.location.href = `/switch_account/${account.id}`;
}
