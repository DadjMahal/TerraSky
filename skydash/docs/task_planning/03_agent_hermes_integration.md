# 🤖 Task Series 3: Hermes Agent Integration

## Категорія: Адміністрування через агентів
## Статус: PLANNED
## Пріоритет: HIGH

### 26. State indicator widget for Hermes agent
- Опис: Ємність статусу агента на дашборді (online/offline/connecting)
- Файли: skydash/templates/base.html, skydash/static/js/agent-status.js

### 27. Built-in SSH terminal interface
- Опис: Web-based SSH термінал з підтримкою сесій
- Бібліотека: xterm.js + socket.io
- Файли: skydash/templates/detail.html, skydash/hermes_agent.py

### 28. Remote command execution with history
- Опис: Виконання команд на віддаленому сервері з історією
- Файли: skydash/templates/detail.html, skydash/static/js/remote-commands.js

### 29. SSH file manager
- Опис: Просмотр, завантаження, відправка файлів через SSH
- Файли: skydash/templates/file-manager.html

### 30. File upload/download functionality
- Опис: Drag-and-drop файлів для завантаження/скачування
- Файли: skydash/static/js/file-transfer.js

### 31. Process monitor in real-time
- Опис: Список процесів з CPU%, MEM%, PID
- Файли: skydash/static/js/process-monitor.js

### 32. Network activity graphs
- Опис: Моніторинг трафіку за інтерфейсами (RX/TX)
- Файли: skydash/static/js/network-monitor.js

### 33. System resource usage (CPU, RAM, Disk I/O)
- Опис: Live графіки використання системних ресурсів
- Файли: skydash/static/js/resource-monitor.js

### 34. System restart/shutdown control
- Опис: Кнопки перезагрузки/вимкнення системи
- Файли: skydash/templates/detail.html, skydash/hermes_agent.py

### 35. Configuration cloning capability
- Опис: Клонування конфігурації сервера до іншого інстанса
- Файли: skydash/templates/snapshot.html

### 36. System settings backup/restore
- Опис: Резервне копіювання/відновлення налаштувань ОС
- Файли: skydash/templates/backup-restore.html

### 37. Multi-agent manager dashboard
- Опис: Центральний інтерфейс для управління кількома агентами
- Файли: skydash/templates/agents.html

### 38. Agent audit trail logging
- Опис: Журнал всіх дій агента
- Файли: skydash/static/js/audit-log.js

### 39. Emergency stop button
- Опис: Негайна зупинка агента при критичній помилці
- Файли: skydash/templates/detail.html

### 40. Agent health check automation
- Опис: Автоматичні перевірки здоров’я агента
- Файли: skydash/hermes_agent.py
