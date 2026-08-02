# 🎨 Task Series 2: UI/UX - Детальні сторінки інстансів

## Категорія: Покращення UI/UX
## Статус: PLANNED
## Пріоритет: HIGH

### 11. Інтерфейс детальної сторінки з табами
- Опис: 4 активні таби (Overview, Hardware, Network, Actions) з анімацією переключення
- Файли: skydash/templates/detail.html

### 12. Progress loader для дій інстанса
- Опис: Візуальний індикатор для start/stop/reboot операцій
- Файли: skydash/static/js/actions-loader.js

### 13. Hardware specs visualization
- Опис: Інтерактивна візуалізація CPU/RAM/Disk у вигляді анімованих графіків
- Файли: skydash/templates/detail.html, skydash/static/js/specs-visualization.js

### 14. Network topology map
- Опис: Візуалізація мережі з public/private IP, security groups
- Файли: skydash/templates/detail.html

### 15. Timeline історії zmian статусу
- Опис: Горизонтальна лінія з часом змін статусу інстанса
- Файли: skydash/templates/detail.html, skydash/static/js/status-timeline.js

### 16. SSH terminal вбудований у інтерфейс
- Опис: Web-based SSH термінал через веб- socket
- Бібліотека: xterm.js
- Файли: skydash/templates/detail.html, skydash/static/js/ssh-terminal.js

### 17. Log viewer з syntax highlighting
- Опис: Кольорове підсвічування логів за рівнями (INFO, WARN, ERROR)
- Бібліотека: Prism.js
- Файли: skydash/static/js/log-viewer.js

### 18. Metrics charts для інстанса
- Опис: Gрафіки навантаження, трафіку, дискового простору
- Бібліотека: Chart.js
- Файли: skydash/templates/detail.html, skydash/static/js/metrics-charts.js

### 19. Custom domain mapping UI
- Опис: Інтерфейс для прив’язки доменів до інстансів
- Файли: skydash/templates/detail.html

### 20. Resource usage heatmap
- Опис: Теплова карта використання ресурсів серед всіх інстансів
- Файли: skydash/templates/index.html, skydash/static/js/heatmap.js
