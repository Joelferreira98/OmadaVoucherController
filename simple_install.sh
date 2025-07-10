#!/bin/bash

# Script de instalação simplificado para resolver problemas de travamento
# Use este script se a instalação normal falhar

set -e

echo "🚀 Instalação Simplificada - Omada Voucher Controller"
echo "=================================================="

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo "❌ Execute como root: sudo bash simple_install.sh"
    exit 1
fi

# Função para debug
debug() {
    echo "🔍 DEBUG: $1"
}

# Configurações pré-definidas (edite conforme necessário)
echo "📋 Configurações:"
echo "   MySQL Host: 194.163.133.179"
echo "   MySQL Port: 3306"
echo "   MySQL Database: omada_voucher_system"
echo "   MySQL User: JOEL"
echo ""

# Solicitar apenas a senha
read -s -p "Digite a senha do MySQL para o usuário JOEL: " DB_PASSWORD
echo ""

# Configurar URLs
DATABASE_URL="mysql+pymysql://JOEL:$DB_PASSWORD@194.163.133.179:3306/omada_voucher_system"
SESSION_SECRET=$(openssl rand -hex 32)

echo "✅ Configurações definidas"

# Atualizar sistema
debug "Atualizando sistema..."
apt update -y > /dev/null 2>&1
apt install -y python3 python3-pip python3-venv git nginx supervisor mysql-client > /dev/null 2>&1

# Testar conexão MySQL
debug "Testando conexão MySQL..."
if ! mysql -h194.163.133.179 -P3306 -uJOEL -p$DB_PASSWORD -e "SELECT 1;" omada_voucher_system > /dev/null 2>&1; then
    echo "❌ Erro na conexão MySQL!"
    exit 1
fi
echo "✅ Conexão MySQL OK"

# Criar usuário
debug "Criando usuário voucher..."
useradd -m -s /bin/bash voucher 2>/dev/null || true

# Baixar código
debug "Baixando código..."
rm -rf /tmp/voucher-install
git clone https://github.com/Joelferreira98/OmadaVoucherController.git /tmp/voucher-install > /dev/null 2>&1

# Instalar aplicação
debug "Instalando aplicação..."
rm -rf /opt/voucher-app
mkdir -p /opt/voucher-app
cp -r /tmp/voucher-install/* /opt/voucher-app/
chown -R voucher:voucher /opt/voucher-app/

# Configurar ambiente
debug "Configurando ambiente..."
cd /opt/voucher-app

# Criar venv
sudo -u voucher python3 -m venv venv
sudo -u voucher ./venv/bin/pip install --upgrade pip > /dev/null 2>&1

# Instalar dependências essenciais
debug "Instalando dependências..."
sudo -u voucher ./venv/bin/pip install Flask==3.0.0 > /dev/null 2>&1
sudo -u voucher ./venv/bin/pip install Flask-SQLAlchemy==3.1.1 > /dev/null 2>&1
sudo -u voucher ./venv/bin/pip install PyMySQL==1.1.0 > /dev/null 2>&1
sudo -u voucher ./venv/bin/pip install gunicorn==21.2.0 > /dev/null 2>&1

# Instalar outras dependências
sudo -u voucher ./venv/bin/pip install Flask-Login Flask-WTF WTForms email-validator Werkzeug SQLAlchemy reportlab requests PyJWT oauthlib > /dev/null 2>&1

# Criar configuração
debug "Criando configuração..."
cat > /opt/voucher-app/.env << EOF
DATABASE_URL=$DATABASE_URL
SESSION_SECRET=$SESSION_SECRET
OMADA_CONTROLLER_URL=https://controller.local:8043
OMADA_CLIENT_ID=
OMADA_CLIENT_SECRET=
OMADA_OMADAC_ID=
EOF

chown voucher:voucher /opt/voucher-app/.env

# Testar aplicação
debug "Testando aplicação..."
cd /opt/voucher-app

# Teste básico
if ! sudo -u voucher ./venv/bin/python -c "
import os
os.environ['DATABASE_URL'] = '$DATABASE_URL'
os.environ['SESSION_SECRET'] = '$SESSION_SECRET'
os.environ['OMADA_CONTROLLER_URL'] = 'https://controller.local:8043'
os.environ['OMADA_CLIENT_ID'] = ''
os.environ['OMADA_CLIENT_SECRET'] = ''
os.environ['OMADA_OMADAC_ID'] = ''
from app import app, db
with app.app_context():
    db.create_all()
print('✅ Aplicação OK')
"; then
    echo "❌ Erro ao testar aplicação!"
    exit 1
fi

echo "✅ Aplicação testada com sucesso"

# Configurar Gunicorn
debug "Configurando Gunicorn..."
cat > /opt/voucher-app/gunicorn.conf.py << 'EOF'
bind = "127.0.0.1:5000"
workers = 2
worker_class = "sync"
timeout = 30
keepalive = 2
max_requests = 1000
preload_app = True
EOF

chown voucher:voucher /opt/voucher-app/gunicorn.conf.py

# Configurar Supervisor
debug "Configurando Supervisor..."
cat > /etc/supervisor/conf.d/voucher-app.conf << EOF
[program:voucher-app]
command=/opt/voucher-app/venv/bin/gunicorn --config /opt/voucher-app/gunicorn.conf.py main:app
directory=/opt/voucher-app
user=voucher
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/voucher-app.log
environment=DATABASE_URL="$DATABASE_URL",SESSION_SECRET="$SESSION_SECRET",OMADA_CONTROLLER_URL="https://controller.local:8043",OMADA_CLIENT_ID="",OMADA_CLIENT_SECRET="",OMADA_OMADAC_ID=""
EOF

# Configurar Nginx
debug "Configurando Nginx..."
cat > /etc/nginx/sites-available/voucher-app << 'EOF'
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /opt/voucher-app/static/;
    }
}
EOF

ln -sf /etc/nginx/sites-available/voucher-app /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Reiniciar serviços
debug "Iniciando serviços..."
systemctl restart nginx
systemctl restart supervisor
supervisorctl reread > /dev/null 2>&1
supervisorctl update > /dev/null 2>&1
supervisorctl start voucher-app > /dev/null 2>&1

# Aguardar
sleep 5

# Verificar
if supervisorctl status voucher-app | grep -q "RUNNING"; then
    echo "✅ Aplicação iniciada com sucesso!"
else
    echo "❌ Erro ao iniciar aplicação!"
    supervisorctl status voucher-app
    exit 1
fi

# Testar resposta
if curl -s http://localhost:5000 > /dev/null; then
    echo "✅ Aplicação responde corretamente!"
else
    echo "⚠️  Aplicação pode estar iniciando..."
fi

# Limpar
rm -rf /tmp/voucher-install

echo ""
echo "========================================="
echo "🎉 INSTALAÇÃO CONCLUÍDA!"
echo "========================================="
echo ""
echo "🌐 Acesso: http://$(curl -s ifconfig.me)"
echo "👤 Usuário: master"
echo "🔑 Senha: admin123"
echo ""
echo "📋 Comandos úteis:"
echo "   Status: supervisorctl status voucher-app"
echo "   Logs: tail -f /var/log/voucher-app.log"
echo "   Reiniciar: supervisorctl restart voucher-app"
echo ""
echo "⚙️  Configure o Omada Controller através da interface web"
echo "   Acesse: Menu Master > Configurar Omada"
echo ""