#!/bin/bash

# Script de instalação para VPS Ubuntu/Debian
# Voucher Management System - Instalação Automática

echo "=== Instalação do Sistema de Gerenciamento de Vouchers ==="
echo "Iniciando instalação na VPS..."

# Atualizar sistema
echo "Atualizando sistema..."
sudo apt update && sudo apt upgrade -y

# Instalar dependências do sistema
echo "Instalando dependências..."
sudo apt install -y python3 python3-pip python3-venv nginx mysql-server supervisor git curl

# Criar usuário para a aplicação
echo "Criando usuário voucher..."
sudo useradd -m -s /bin/bash voucher
sudo usermod -aG sudo voucher

# Configurar MySQL
echo "Configurando MySQL..."
sudo systemctl start mysql
sudo systemctl enable mysql

# Configurar MySQL para aceitar conexões locais
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root_password_123';"
sudo mysql -u root -proot_password_123 -e "FLUSH PRIVILEGES;"

# Criar banco de dados e usuário
sudo mysql -u root -proot_password_123 -e "CREATE DATABASE voucher_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -u root -proot_password_123 -e "CREATE USER 'voucher'@'localhost' IDENTIFIED BY 'voucher_password_123';"
sudo mysql -u root -proot_password_123 -e "GRANT ALL PRIVILEGES ON voucher_db.* TO 'voucher'@'localhost';"
sudo mysql -u root -proot_password_123 -e "FLUSH PRIVILEGES;"

# Criar diretório da aplicação
echo "Criando diretório da aplicação..."
sudo mkdir -p /opt/voucher-app
sudo chown voucher:voucher /opt/voucher-app

# Copiar arquivos da aplicação (assumindo que já estão no servidor)
echo "Configurando aplicação..."
cd /opt/voucher-app

# Criar ambiente virtual
sudo -u voucher python3 -m venv venv
sudo -u voucher ./venv/bin/pip install --upgrade pip

# Instalar dependências Python
sudo -u voucher ./venv/bin/pip install Flask==3.0.0
sudo -u voucher ./venv/bin/pip install Flask-SQLAlchemy==3.1.1
sudo -u voucher ./venv/bin/pip install Flask-Login==0.6.3
sudo -u voucher ./venv/bin/pip install Flask-WTF==1.2.1
sudo -u voucher ./venv/bin/pip install WTForms==3.1.0
sudo -u voucher ./venv/bin/pip install email-validator==2.1.0
sudo -u voucher ./venv/bin/pip install Werkzeug==3.0.1
sudo -u voucher ./venv/bin/pip install gunicorn==21.2.0
sudo -u voucher ./venv/bin/pip install PyMySQL==1.1.0
sudo -u voucher ./venv/bin/pip install SQLAlchemy==2.0.23
sudo -u voucher ./venv/bin/pip install reportlab==4.0.7
sudo -u voucher ./venv/bin/pip install requests==2.31.0
sudo -u voucher ./venv/bin/pip install PyJWT==2.8.0
sudo -u voucher ./venv/bin/pip install oauthlib==3.2.2

# Criar arquivo de configuração de ambiente
echo "Criando arquivo de configuração..."
sudo -u voucher cat > /opt/voucher-app/.env << 'EOF'
# Configurações da aplicação
SESSION_SECRET=sua_chave_secreta_muito_forte_aqui_123456789
DATABASE_URL=mysql+pymysql://voucher:voucher_password_123@localhost:3306/voucher_db

# Configurações do Omada Controller (configure conforme necessário)
OMADA_CONTROLLER_URL=https://seu-omada-controller.com:8043
OMADA_CLIENT_ID=seu_client_id
OMADA_CLIENT_SECRET=seu_client_secret
OMADA_OMADAC_ID=seu_omadac_id
EOF

# Criar arquivo de configuração do Gunicorn
sudo -u voucher cat > /opt/voucher-app/gunicorn.conf.py << 'EOF'
import multiprocessing

# Configuração do Gunicorn para produção
bind = "127.0.0.1:5000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
reload = False
daemon = False

# Logging
accesslog = "/var/log/voucher-app/access.log"
errorlog = "/var/log/voucher-app/error.log"
loglevel = "info"
access_log_format = '%h %l %u %t "%r" %s %b "%{Referer}i" "%{User-Agent}i"'
EOF

# Criar diretório de logs
sudo mkdir -p /var/log/voucher-app
sudo chown voucher:voucher /var/log/voucher-app

# Configurar Supervisor para gerenciar a aplicação
echo "Configurando Supervisor..."
sudo cat > /etc/supervisor/conf.d/voucher-app.conf << 'EOF'
[program:voucher-app]
command=/opt/voucher-app/venv/bin/gunicorn --config /opt/voucher-app/gunicorn.conf.py main:app
directory=/opt/voucher-app
user=voucher
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/voucher-app/supervisor.log
environment=PATH="/opt/voucher-app/venv/bin"
EOF

# Configurar Nginx
echo "Configurando Nginx..."
sudo cat > /etc/nginx/sites-available/voucher-app << 'EOF'
server {
    listen 80;
    server_name _;  # Substitua pelo seu domínio

    client_max_body_size 50M;
    
    # Logs
    access_log /var/log/nginx/voucher-app-access.log;
    error_log /var/log/nginx/voucher-app-error.log;

    # Arquivos estáticos
    location /static/ {
        alias /opt/voucher-app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Proxy para a aplicação
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
    }
}
EOF

# Ativar site no Nginx
sudo ln -s /etc/nginx/sites-available/voucher-app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Testar configuração do Nginx
sudo nginx -t

# Reiniciar serviços
echo "Reiniciando serviços..."
sudo systemctl restart nginx
sudo systemctl enable nginx
sudo systemctl restart supervisor
sudo systemctl enable supervisor

# Configurar firewall (se necessário)
echo "Configurando firewall..."
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

echo "=== Instalação concluída! ==="
echo ""
echo "Próximos passos:"
echo "1. Copie os arquivos da aplicação para /opt/voucher-app/"
echo "2. Configure o arquivo .env com suas credenciais reais"
echo "3. Execute: sudo supervisorctl reread && sudo supervisorctl update"
echo "4. Execute: sudo supervisorctl start voucher-app"
echo "5. Acesse sua aplicação no navegador"
echo ""
echo "Comandos úteis:"
echo "- Status da aplicação: sudo supervisorctl status voucher-app"
echo "- Reiniciar aplicação: sudo supervisorctl restart voucher-app"
echo "- Ver logs: sudo tail -f /var/log/voucher-app/supervisor.log"
echo "- Status do Nginx: sudo systemctl status nginx"
echo ""
echo "Configuração de domínio:"
echo "- Edite /etc/nginx/sites-available/voucher-app"
echo "- Substitua 'server_name _;' por 'server_name seudominio.com;'"
echo "- Reinicie o Nginx: sudo systemctl reload nginx"