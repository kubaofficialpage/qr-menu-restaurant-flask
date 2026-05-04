# 🚀 Deploy Flask + MySQL на Timeweb Cloud (Ubuntu)

## 📦 Стек

* Python 3
* Flask
* MySQL
* Gunicorn
* Nginx
* SSL (Let's Encrypt)

---

# 1. 🔧 Подключение к серверу

```bash
ssh root@YOUR_SERVER_IP
```

Обновление системы:

```bash
apt update && apt upgrade -y
```

---

# 2. 🧱 Установка зависимостей

```bash
apt install -y python3 python3-venv python3-pip nginx mysql-server
```

---

# 3. 📁 Создание проекта

```bash
mkdir -p /var/www/flaskapp
cd /var/www/flaskapp
```

Загрузка проекта:

```bash
git clone YOUR_REPO .
# или загрузка через SFTP
```

---

# 4. 🐍 Виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

# 5. 🗄️ Настройка MySQL

```bash
sudo mysql
```

```sql
CREATE DATABASE flaskapp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'flaskuser'@'localhost' IDENTIFIED BY 'StrongPassword123!';
GRANT ALL PRIVILEGES ON flaskapp.* TO 'flaskuser'@'localhost';

FLUSH PRIVILEGES;
EXIT;
```

---

# 6. ⚙️ .env файл

```bash
nano .env
```

```env
DB_HOST=localhost
DB_USER=flaskuser
DB_PASSWORD=StrongPassword123!
DB_NAME=flaskapp
SECRET_KEY=supersecretkey
```

---

# 7. 🧬 Миграции базы

```bash
source venv/bin/activate

flask db init
flask db migrate -m "init"
flask db upgrade
```

---

# 8. 🔥 Gunicorn

```bash
pip install gunicorn
```

Тест:

```bash
gunicorn --bind 127.0.0.1:8000 app:app
```

---

# 9. ⚙️ systemd сервис

```bash
nano /etc/systemd/system/flaskapp.service
```

```ini
[Unit]
Description=Flask App
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/flaskapp
Environment="PATH=/var/www/flaskapp/venv/bin"
EnvironmentFile=/var/www/flaskapp/.env
ExecStart=/var/www/flaskapp/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
systemctl daemon-reload
systemctl start flaskapp
systemctl enable flaskapp
```

Проверка:

```bash
systemctl status flaskapp
```

---

# 10. 🌐 Nginx

```bash
nano /etc/nginx/sites-available/flaskapp
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 50M;

    location /static/ {
        alias /var/www/flaskapp/static/;
    }

    location /uploads/ {
        alias /var/www/flaskapp/uploads/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активировать:

```bash
ln -s /etc/nginx/sites-available/flaskapp /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

---

# 11. 🔐 SSL (HTTPS)

```bash
apt install certbot python3-certbot-nginx -y
```

```bash
certbot --nginx -d your-domain.com -d www.your-domain.com
```

---

# 12. 🔄 Автопродление SSL

```bash
systemctl status certbot.timer
```

---

# 13. 📂 Загрузка файлов

```bash
mkdir -p /var/www/flaskapp/uploads
chmod 755 /var/www/flaskapp/uploads
```

Flask:

```python
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
```

---

# 14. 📊 Проверка

```bash
curl http://127.0.0.1:8000
curl -I https://your-domain.com
```

---

# 🎉 Готово

Теперь работает:

* Flask
* MySQL
* Gunicorn
* Nginx
* HTTPS
* Upload файлов

---

# ⚡ Полезные команды

```bash
systemctl restart flaskapp
systemctl restart nginx

journalctl -u flaskapp -f
nginx -t
```

---

# 🔥 Рекомендации

* Не использовать root → создать пользователя
* Добавить firewall
* Настроить backup MySQL
* Использовать CDN (Cloudflare)

---
