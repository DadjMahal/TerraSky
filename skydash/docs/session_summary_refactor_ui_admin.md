# SkyDash Session Handoff — UI Refactor & Admin Panel

## 📋 Оригінальний промпт (для відновлення контексту)

**Повний текст запиту:**
> "1. Refactor the entire project UI in style like you did Login page. 1.1. Design should be stylish 1.2. Emoji Friendly 1.3. All pages should be formated 2. Add also pages like: 2.1. 404 Not Found 2.2. Server temporary unavailable 3. Add admin page: 3.1. Global settings 3.1.1. Site name / Meta tags / favicon / logo and other SEO friendly zone. 3.1.2. Edit profile / change password / add or edit email. 3.2. Add / Remove / Edit instances 3.2.1. Think on all necessary function we will need atm."

---

## ✅ Що ВЖЕ ЗРОБЛЕНО (Completed)

### 1. UI Refactor (п.1, 1.1, 1.2, 1.3)
- [x] **`templates/base.html`** — створено базовий шаблон з:
  - Темним градієнтним фоном (`#1a1a2e` → `#16213e` → `#0f3460`)
  - Navbar з назвою сайту, логотипом, навігацією
  - Кнопки Logout 🚪 та Admin ⚙️ в navbar
  - Emoji-friendly дизайн у всіх елементах
  - Flash-повідомлення, тост, модальне вікно завантаження
  - Футер
- [x] **`templates/index.html`** — переписано, extends base.html:
  - Бейджі статусу з emoji: 🟢 Running, 🔴 Stopped, 🟡 Starting, 🟠 Stopping, ❌ Error, ❓ Unknown
  - Кнопки з emoji: 🚀 Start, ⛔ Stop, 🔄 Refresh
  - Пошук 🔍, фільтр за провайдером 🌐, фільтр за статусом 🚦, сортування 🔤
  - Всі функції JS збережені (pollStatuses, pollUntilSettled, loader modal)
- [x] **`templates/detail.html`** — переписано, extends base.html:
  - Розділи з emoji: 📋 Overview, 💻 Hardware, 🌐 Network, ⚙️ Actions, 📁 Logs
  - Hermes Agent секція з кнопками та кольоровими логами
  - Секція логів з скануванням помилок/попереджень
- [x] **`templates/login.html`** — оновлено, стильний дизайн (standalone)

### 2. Сторінки помилок (п.2.1, 2.2)
- [x] **`templates/404.html`** — extends base.html, emoji 🔍, кнопка "🏠 Back to Dashboard"
- [x] **`templates/503.html`** — extends base.html, emoji 🔧, кнопка "🔄 Retry"
- [x] **`app.py`** — додано обробники помилок:
  - `@app.errorhandler(404)` → `not_found_error()` → render 404.html
  - `@app.errorhandler(500)` → `internal_error()` → render 503.html

### 3. Admin Panel — Site Settings (п.3.1, 3.1.1)
- [x] **`templates/admin.html`** — вкладка "🌍 Site Settings":
  - 🏷️ Site Name (input)
  - 📝 Meta Description (input) — SEO ready
  - 🎨 Favicon URL (input)
  - 🖼️ Logo URL (input)
  - Кнопка "💾 Save Settings"
- [x] **`app.py`** — маршрут `POST /admin/settings` → `config_store.update_site_settings()`
- [x] **`config_store.py`** — функції `update_site_settings()`, `get_site_settings()`
- [x] **Context processor** — `site_name`, `site_description`, `favicon_url`, `logo_url` доступні в усіх шаблонах

### 4. Admin Panel — Profile (п.3.1.2)
- [x] **`templates/admin.html`** — вкладка "👤 Profile":
  - Username (input)
  - 📧 Email (input)
  - Кнопка "💾 Save Profile"
  - 🔑 Change Password: Current Password, New Password, Confirm Password
  - Перевірка: current password має співпадати, new password >= 6 символів, confirm має співпадати
- [x] **`app.py`** — маршрути:
  - `POST /admin/profile` → `config_store.update_profile()`
  - `POST /admin/password` → `config_store.set_password()` (з валідацією)
- [x] **`auth.py`** — використовує `config_store.verify_password()` (перевіряє збережений hash, потім env var)

### 5. Admin Panel — Instances (п.3.2, ЧАСТКОВО)
- [x] **Hide/Unhide**: кнопки "🙈 Hide" та "👁️ Show" в таблиці інстансів
- [x] **Add Custom Instance**: форма з полями Provider, Instance ID, Name, Region, Type
- [x] **Remove Custom Instance**: кнопка "🗑️" для видалення
- [x] **`app.py`** — маршрути:
  - `GET /admin/instance/<slug>/hide`
  - `GET /admin/instance/<slug>/unhide`
  - `POST /admin/instance/add`
  - `GET /admin/instance/<id>/remove`
- [x] **`config_store.py`** — функції: `hide_instance()`, `unhide_instance()`, `get_hidden_instances()`, `add_custom_instance()`, `remove_custom_instance()`, `get_custom_instances()`

---

## ❌ Що НЕ ДОРОБЛЕНО (потрібно завершити)

### 1. Edit Instance (п.3.2 — НЕ РЕАЛІЗОВАНО) ⚠️
**Проблема**: Немає UI для редагування інстансу.
**Що є в коді, але не має UI**:
- `config_store.set_instance_override(slug, display_name, description, tags)` — функція існує
- `config_store.get_instance_override(slug)` — функція існує  
- `config_store.delete_instance_override(slug)` — функція існує
- `instance_overrides` застосовуються в `app.py` в маршруті `instance_detail()`

**Що потрібно зробити**:
1. Додати кнопку "✏️ Edit" в таблицю інстансів в `admin.html`
2. Створити модальне вікно або сторінку для редагування:
   - Display Name (назва, що відображається в дашборді)
   - Description (опис)
   - Tags (теги, key:value)
3. Додати маршрут `POST /admin/instance/<slug>/edit` в `app.py`
4. Підключити до `config_store.set_instance_override()`

### 2. Можливі покращення (п.3.2.1)
- **Bulk actions**: вибрати кілька інстансів і сховати/показати всі разом
- **Instance search**: пошук по інстансах в адмін-панелі
- **Instance details preview**: показувати IP, статус, тип для кожного інстансу в адмін-панелі
- **Export/Import**: експорт конфігурації інстансів в JSON
- **Audit log**: логування змін (хто і коли приховав/редагував інстанс)

---

## 📁 СТАН ФАЙЛІВ (поточний)

### Шаблони (templates/)
| Файл | Статус | Розмір | Примітки |
|------|--------|--------|----------|
| `base.html` | ✅ Готово | 3.5 KB | Спільний layout, navbar, footer, toast, loader modal |
| `index.html` | ✅ Переписано | 14 KB | Розширює base.html, всі JS функції збережені |
| `detail.html` | ✅ Переписано | 27 KB | Розширює base.html, Hermes Agent, logs |
| `admin.html` | ✅ Готово | 6.5 KB | 3 вкладки, але БЕЗ "Edit Instance" |
| `login.html` | ✅ Готово | 3.5 KB | Standalone, стильний дизайн |
| `404.html` | ✅ Готово | 0.5 KB | Розширює base.html |
| `503.html` | ✅ Готово | 0.5 KB | Розширює base.html |

### Python модулі
| Файл | Статус | Розмір | Примітки |
|------|--------|--------|----------|
| `app.py` | ✅ Готово | 7 KB | 22 маршрути, всі з `@login_required` |
| `auth.py` | ✅ Готово | 3 KB | Використовує `config_store.verify_password()` |
| `config_store.py` | ✅ Готово | 6 KB | 23 функції, JSON-сховище |
| `hermes_agent.py` | ✅ Готово | 12 KB | SSH-based log retrieval |
| `models.py` | ✅ Готово | 3 KB | Instance dataclass |
| `state_reader.py` | ✅ Готово | 9 KB | Terraform state parser |
| `instance_specs.py` | ✅ Готово | 7 KB | CPU/RAM lookup |

### Провідери (providers/)
| Файл | Статус | Примітки |
|------|--------|----------|
| `base.py` | ✅ Готово | Abstract CloudProvider + get_logs |
| `aws.py` | ✅ Готово | Live IP fix (63.179.97.116) |
| `azure.py` | ✅ Готово | Кешовані клієнти, live IP |
| `oracle.py` | ✅ Готово | Кешовані клієнти, VNIC IP |
| `alibaba.py` | ✅ Готово | EIP support |
| `registry.py` | ✅ Готово | Provider registry |

---

## 🔗 API МАРШРУТИ (22 всього)

### Auth (2)
- `GET /login` — сторінка входу
- `POST /login` — аутентифікація (username/password)
- `GET /logout` — вихід

### Dashboard & Instances (6)
- `GET /` — дашборд (захищено)
- `GET /instance/<slug>` — деталі інстансу
- `POST /instance/<slug>/start` — старт
- `POST /instance/<slug>/stop` — стоп
- `GET /api/statuses` — всі статуси (паралельно)
- `GET /api/status/<slug>` — один статус

### Admin (8)
- `GET /admin` — адмін-панель
- `POST /admin/settings` — зберегти налаштування сайту
- `POST /admin/profile` — зберегти профіль
- `POST /admin/password` — змінити пароль
- `GET /admin/instance/<slug>/hide` — сховати інстанс
- `GET /admin/instance/<slug>/unhide` — показати інстанс
- `POST /admin/instance/add` — додати кастомний інстанс
- `GET /admin/instance/<id>/remove` — видалити кастомний інстанс

### Logs & Hermes (6)
- `GET /logs/<slug>` — логи (legacy)
- `GET /logs/<slug>/scan` — сканування логів
- `GET /hermes/<slug>/logs/<type>` — Hermes логи
- `GET /hermes/<slug>/disk` — диск
- `GET /hermes/<slug>/test` — тест SSH
- `GET /refresh` — очистити кеш

---

## 🚀 ЯК ЗАПУСТИТИ

```bash
cd /home/volodro/skydash
pkill -f '[a]pp.py' 2>/dev/null
setsid bash -c 'cd /home/volodro/skydash && set -a && source /home/volodro/terraform/.env && set +a && exec venv/bin/python app.py' > flask.log 2>&1 &
# http://localhost:8080, login: admin / admin
```

---

## 📍 ТОЧКА ПРОДОВЖЕННЯ

### Наступний крок: Додати "Edit Instance" в адмін-панель

**Що конкретно зробити:**
1. В `admin.html` додати кнопку "✏️ Edit" до кожного рядка в таблиці інстансів
2. Створити модальне вікно (Bootstrap Modal) для редагування:
   - Display Name (input)
   - Description (textarea)
   - Tags (dynamic key-value pairs)
3. В `app.py` додати маршрут `POST /admin/instance/<slug>/edit`
4. Підключити `config_store.set_instance_override()`
5. Додати флеш-повідомлення про успіх/помилку

**Після цього можна:**
- Налаштувати SSH для Hermes Agent (створити ключ, додати до `authorized_keys` на сервері)
- Встановити безпечний пароль `SKYDASH_ADMIN_PASSWORD` в `.env`
- Додати HTTPS, rate limiting, CSRF захист
- Додати bulk actions (сховати/показати всі)
- Додати пошук по інстансах в адмін-панелі

---

## 📄 Документація

- `/home/volodro/Documentation/README.md` — повна пам'ять проекту
- `/home/volodro/skydash/docs/session_summary_refactor_ui_admin.md` — цей файл
- `/home/volodro/Documentation/logs/2026-07-30_auth-hermes-agent-disk.md` — лог сесії

---

*Створено: 2026-07-31. Для використання в новій сесії Cline/Hermes.*
