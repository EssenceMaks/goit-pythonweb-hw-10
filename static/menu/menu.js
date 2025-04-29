// JS для меню

// Открытие попапа создания контакта
function openPopup(id) {
  document.getElementById(id).style.display = 'block';
}
function closePopup(id) {
  document.getElementById(id).style.display = 'none';
}

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
    const resp = await fetch('/db/check-state');
    const data = await resp.json();
    if (data.status === 'no_db' || data.status === 'no_tables' || data.status === 'no_contacts') {
      addFooterMessage(data.message, data.status === 'no_db' ? 'error' : 'warn');
    } else if (data.status === 'ok') {
      addFooterMessage(`Контактів у базі: ${data.count}`, 'success');
    } else if (data.status === 'noenv') {
      addFooterMessage(data.message, 'error');
    }
  } catch (e) {}
}
window.checkDBState = checkDBState;

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
  checkDBState();
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
        // 1. Создать базу
        const resp = await fetch('/db/create-db', {method:'POST'});
        const data = await resp.json();
        if (resp.ok && (data.status === 'created' || data.status === 'exists')) {
          addFooterMessage(data.message, 'success');
          // 2. Инициализировать таблицы
          const resp2 = await fetch('/db/init', {method:'POST'});
          const data2 = await resp2.json();
          if (resp2.ok && (data2.status === 'created' || data2.status === 'exists')) {
            addFooterMessage('База и таблицы готовы!', 'success');
            window.resetAndRenderContacts();
          } else {
            addFooterMessage('Ошибка инициализации таблиц', 'error');
          }
        } else if (data.status === 'noenv') {
          addFooterMessage(data.message, 'error');
        } else {
          addFooterMessage(data.message || 'Ошибка создания базы', 'error');
        }
      } catch (e) {
        addFooterMessage('Ошибка при создании базы', 'error');
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
        const resp = await fetch('/db/drop-db', {method:'POST'});
        const data = await resp.json();
        if (resp.ok && data.status === 'dropped') {
          addFooterMessage(data.message, 'success');
          window.resetAndRenderContacts();
        } else {
          addFooterMessage(data.message || 'Ошибка удаления базы', 'error');
        }
      } catch (e) {
        addFooterMessage('Ошибка при удалении базы', 'error');
      }
      btnDropDB.disabled = false;
    });
    btnDropDB.addEventListener('click', ()=>setTimeout(checkDBState, 1000));
  }

  if (btnInit) {
    btnInit.addEventListener('click', async function() {
      btnInit.disabled = true;
      try {
        const resp = await fetch('/db/init', {method:'POST'});
        if (resp.ok) {
          addFooterMessage('База успешно инициализирована', 'success');
          window.resetAndRenderContacts();
        } else {
          addFooterMessage('Ошибка инициализации базы', 'error');
        }
      } catch {
        addFooterMessage('Ошибка сети при инициализации', 'error');
      }
      btnInit.disabled = false;
    });
  }

  if (btnFill) {
    btnFill.addEventListener('click', async function() {
      btnFill.disabled = true;
      try {
        const resp = await fetch('/db/fill-fake?n=10', {method:'POST'});
        if (resp.ok) {
          addFooterMessage('Контакты успешно добавлены', 'success');
          window.resetAndRenderContacts();
        } else {
          addFooterMessage('Ошибка добавления контактов', 'error');
        }
      } catch {
        addFooterMessage('Ошибка сети при добавлении', 'error');
      }
      btnFill.disabled = false;
    });
  }

  if (btnClear) {
    btnClear.addEventListener('click', async function() {
      btnClear.disabled = true;
      try {
        const resp = await fetch('/db/clear', {method:'POST'});
        if (resp.ok) {
          addFooterMessage('Все контакты удалены', 'success');
          window.resetAndRenderContacts();
        } else {
          addFooterMessage('Ошибка удаления контактов', 'error');
        }
      } catch {
        addFooterMessage('Ошибка сети при удалении', 'error');
      }
      btnClear.disabled = false;
    });
    btnClear.addEventListener('click', ()=>setTimeout(checkDBState, 1000));
  }
});
