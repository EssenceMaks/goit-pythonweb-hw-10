async function dbAction(action) {
  let endpoint = '';
  if (action === 'init') endpoint = '/db/init';
  if (action === 'fill') endpoint = '/db/fill-fake';
  if (action === 'clear') endpoint = '/db/clear';
  let params = {};
  if (action === 'fill') params = { n: 10 };
  const btn = document.getElementById(`btn-${action}`);
  btn.disabled = true;
  btn.innerText = '...';
  try {
    const res = await fetch(endpoint + (action === 'fill' ? '?n=10' : ''), { method: 'POST' });
    const data = await res.json();
    alert(data.message || JSON.stringify(data));
  } catch (e) {
    alert('Ошибка: ' + e.message);
  }
  btn.disabled = false;
  if (action === 'init') btn.innerText = 'Создать шаблон базы';
  if (action === 'fill') btn.innerText = 'Создать случайные контакты';
  if (action === 'clear') btn.innerText = 'Удалить все контакты';
}
