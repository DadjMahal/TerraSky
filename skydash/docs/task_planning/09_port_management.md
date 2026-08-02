# 🔒 Task Series 9: Port/Permission Management

## Категорія: Керування відкриттям портів через хмарні сервіси
## Статус: PLANNED
## Пріоритет: HIGH

### 91. Security groups management for each cloud provider
- Опис: Централизоване управління security groups AWS, Azure, Oracle, Alibaba
- Файли: skydash/templates/security-groups.html

### 92. Inbound/Outbound rules configuration
- Опис: Налаштування правил вхідних/вихідних розрядів з валідацією
- Файли: skydash/static/js/security-rules.js

### 93. Port ranges with validation
- Опис: Безпечне введення діапазонів портів з автоматичною валідацією
- Файли: skydash/static/js/port-validator.js

### 94. IP whitelisting/blacklisting system
- Опис: Білікст та блекліст IP адрес для доступу
- Файли: skydash/templates/ip-whitelist.html

### 95. Security group templates
- Опис: Попередньо налаштовані шаблони правил (Web Server, Database, SSH Only)
- Файли: skydash/templates/sg-templates.html

### 96. Auto security group generation
- Опис: Автоматична генерація груп безпеки на основі типу сервісу
- Файли: skydash/autogen_security_groups.py

### 97. VPN tunnel management
- Опис: Налаштування та моніторинг VPN тунелів
- Файли: skydash/templates/vpn-management.html

### 98. Firewall rules history
- Опис: Історія змін правил брандмауера
- Файли: skydash/audit_trail.py

### 99. Compliance checking for security rules
- Опис: Перевірка відповідності правил (PCI-DSS, HIPAA, GDPR)
- Файли: skydash/compliance_checker.py

### 100. Breach detection and alerting
- Опис: Виявлення підозрілих дій та автоматичні сповіщення
- Файли: skydash/templates/breach-detection.html
