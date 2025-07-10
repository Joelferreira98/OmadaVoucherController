#!/bin/bash

# Quick Install Script - Omada Voucher Controller
# Script otimizado para instalação rápida com correções para Gunicorn

set -e

echo "🚀 Instalação Rápida - Omada Voucher Controller"
echo "============================================="
echo ""

# Verificar root
if [[ $EUID -ne 0 ]]; then
    echo "❌ Execute como root:"
    echo "   curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/quick_install.sh | sudo bash"
    exit 1
fi

# Configurações pré-definidas
echo "📋 Configurações MySQL:"
echo "   Host: 194.163.133.179"
echo "   Port: 3306"
echo "   Database: omada_voucher_system"
echo "   User: JOEL"
echo ""

# Solicitar senha
read -s -p "Digite a senha do MySQL: " DB_PASSWORD
echo ""

# Configurar variáveis
DATABASE_URL="mysql+pymysql://JOEL:$DB_PASSWORD@194.163.133.179:3306/omada_voucher_system"
SESSION_SECRET=$(openssl rand -hex 32)

echo "✅ Configurações definidas"

# Instalar dependências
echo "📦 Instalando dependências..."
apt update -y > /dev/null
apt install -y python3 python3-pip python3-venv git nginx supervisor mysql-client > /dev/null 2>&1

# Testar MySQL
echo "🔍 Testando conexão MySQL..."
if ! mysql -h194.163.133.179 -P3306 -uJOEL -p$DB_PASSWORD -e "SELECT 1;" omada_voucher_system > /dev/null 2>&1; then
    echo "❌ Erro na conexão MySQL!"
    exit 1
fi
echo "✅ Conexão MySQL OK"

# Criar usuário
echo "👤 Criando usuário..."
useradd -m -s /bin/bash voucher 2>/dev/null || true

# Baixar código
echo "📥 Baixando código..."
rm -rf /tmp/voucher-install
git clone https://github.com/Joelferreira98/OmadaVoucherController.git /tmp/voucher-install > /dev/null 2>&1

# Instalar aplicação
echo "🔧 Instalando aplicação..."
rm -rf /opt/voucher-app
mkdir -p /opt/voucher-app
cp -r /tmp/voucher-install/* /opt/voucher-app/
chown -R voucher:voucher /opt/voucher-app/
cd /opt/voucher-app

# Configurar Python
echo "🐍 Configurando Python..."
sudo -u voucher python3 -m venv venv
sudo -u voucher ./venv/bin/pip install --upgrade pip > /dev/null 2>&1

# Instalar dependências Python
echo "📚 Instalando dependências Python..."
sudo -u voucher ./venv/bin/pip install -r app_requirements.txt > /dev/null 2>&1 || {
    # Fallback se não houver requirements.txt
    sudo -u voucher ./venv/bin/pip install Flask Flask-SQLAlchemy Flask-Login Flask-WTF PyMySQL gunicorn > /dev/null 2>&1
}

# Configurar aplicação
echo "⚙️  Configurando aplicação..."
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
echo "🧪 Testando aplicação..."
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
" > /dev/null 2>&1; then
    echo "❌ Erro no teste da aplicação!"
    exit 1
fi

echo "✅ Aplicação testada"

# Configurar Supervisor
echo "📋 Configurando Supervisor..."
cat > /etc/supervisor/conf.d/voucher-app.conf << EOF
[program:voucher-app]
command=/opt/voucher-app/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 30 --keep-alive 2 --max-requests 1000 --preload main:app
directory=/opt/voucher-app
user=voucher
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/voucher-app.log
environment=DATABASE_URL="$DATABASE_URL",SESSION_SECRET="$SESSION_SECRET",OMADA_CONTROLLER_URL="https://controller.local:8043",OMADA_CLIENT_ID="",OMADA_CLIENT_SECRET="",OMADA_OMADAC_ID=""
EOF

# Configurar Nginx
echo "🌐 Configurando Nginx..."
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

# Iniciar serviços
echo "🚀 Iniciando serviços..."
systemctl restart nginx
systemctl restart supervisor
supervisorctl reread > /dev/null 2>&1
supervisorctl update > /dev/null 2>&1
supervisorctl start voucher-app > /dev/null 2>&1

# Aguardar
echo "⏳ Aguardando aplicação iniciar..."
sleep 8

# Verificar
if supervisorctl status voucher-app | grep -q "RUNNING"; then
    echo "✅ Aplicação iniciada com sucesso!"
    
    # Testar resposta
    if curl -s http://localhost:5000 > /dev/null; then
        echo "✅ Aplicação respondendo corretamente!"
    else
        echo "⚠️  Aplicação pode estar ainda carregando..."
    fi
else
    echo "❌ Erro ao iniciar aplicação!"
    supervisorctl status voucher-app
    echo "--- Logs recentes ---"
    tail -10 /var/log/voucher-app.log
    exit 1
fi

# Limpar
rm -rf /tmp/voucher-install

echo ""
echo "========================================="
echo "🎉 INSTALAÇÃO CONCLUÍDA!"
echo "========================================="
echo ""
echo "🌐 Acesso: http://$(curl -s ifconfig.me 2>/dev/null || echo 'SEU-IP')"
echo "👤 Usuário: master"
echo "🔑 Senha: admin123"
echo ""
echo "📋 Comandos úteis:"
echo "   Status: supervisorctl status voucher-app"
echo "   Logs: tail -f /var/log/voucher-app.log"
echo "   Reiniciar: supervisorctl restart voucher-app"
echo ""
echo "⚙️  Configure o Omada Controller na interface web:"
echo "   Menu Master → Configurar Omada"
echo ""
echo "🔧 Em caso de problemas, execute o script de correção:"
echo "   curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/fix_gunicorn.sh | sudo bash"
echo ""