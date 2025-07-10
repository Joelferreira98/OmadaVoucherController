#!/bin/bash

# Script de debug para identificar onde a instalação trava
# Execute este script se a instalação normal falhar

echo "🔍 Script de Debug - Instalação Omada Voucher Controller"
echo "========================================================="

set -e  # Para no primeiro erro
set -x  # Mostra todos os comandos executados

# Função para logs
log_info() {
    echo "ℹ️  $1"
}

log_error() {
    echo "❌ ERRO: $1"
}

log_success() {
    echo "✅ $1"
}

# Função para input seguro
read_input() {
    local prompt="$1"
    local default="$2"
    local input
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        echo "${input:-$default}"
    else
        read -p "$prompt: " input
        echo "$input"
    fi
}

# Função para senha
read_password() {
    local prompt="$1"
    local password
    
    read -s -p "$prompt: " password
    echo ""
    echo "$password"
}

# Verificar se é root
if [[ $EUID -ne 0 ]]; then
    log_error "Este script deve ser executado como root!"
    exit 1
fi

# Verificar sistema
log_info "Verificando sistema..."
if ! command -v lsb_release &> /dev/null; then
    log_error "Sistema não suportado. Use Ubuntu 18.04+ ou Debian 9+"
    exit 1
fi

OS_VERSION=$(lsb_release -rs)
log_info "Sistema detectado: $(lsb_release -ds)"

# Atualizar pacotes
log_info "Atualizando pacotes do sistema..."
apt update -y
apt upgrade -y

# Instalar dependências básicas
log_info "Instalando dependências básicas..."
apt install -y python3 python3-pip python3-venv git curl wget gnupg2 software-properties-common

# Instalar nginx e supervisor
log_info "Instalando Nginx e Supervisor..."
apt install -y nginx supervisor

# Criar usuário
log_info "Criando usuário voucher..."
if ! id "voucher" &>/dev/null; then
    useradd -m -s /bin/bash voucher
    log_success "Usuário voucher criado"
else
    log_info "Usuário voucher já existe"
fi

# Configurar banco de dados
echo ""
echo "=== CONFIGURAÇÃO DO BANCO DE DADOS ==="
echo "Testando configuração com MySQL remoto..."
echo ""

# Perguntar credenciais MySQL
DB_HOST=$(read_input "Host do MySQL" "194.163.133.179")
DB_PORT=$(read_input "Porta do MySQL" "3306")
DB_NAME=$(read_input "Nome do banco" "omada_voucher_system")
DB_USER=$(read_input "Usuário do MySQL" "JOEL")
DB_PASSWORD=$(read_password "Senha do MySQL")

log_info "Testando conexão com banco de dados..."
# Instalar cliente MySQL se necessário
if ! command -v mysql &> /dev/null; then
    log_info "Instalando cliente MySQL..."
    apt install -y mysql-client
fi

# Testar conexão
log_info "Testando conexão: mysql -h$DB_HOST -P$DB_PORT -u$DB_USER -p"
if mysql -h$DB_HOST -P$DB_PORT -u$DB_USER -p$DB_PASSWORD -e "SELECT 1;" "$DB_NAME" 2>/dev/null; then
    log_success "Conexão com banco de dados OK!"
else
    log_error "Erro na conexão com banco de dados!"
    log_info "Verifique:"
    log_info "1. Host: $DB_HOST"
    log_info "2. Porta: $DB_PORT"
    log_info "3. Usuário: $DB_USER"
    log_info "4. Banco: $DB_NAME"
    log_info "5. Senha está correta?"
    exit 1
fi

DATABASE_URL="mysql+pymysql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
log_info "DATABASE_URL: $DATABASE_URL"

# Configurar aplicação
echo ""
echo "=== CONFIGURAÇÃO DA APLICAÇÃO ==="
SESSION_SECRET=$(openssl rand -hex 32)
log_success "Chave secreta gerada: ${SESSION_SECRET:0:16}..."

# Configurar Omada
echo ""
echo "=== CONFIGURAÇÃO DO OMADA CONTROLLER ==="
OMADA_URL=$(read_input "URL do Omada Controller" "https://controller.local:8043")
OMADA_CLIENT_ID=$(read_input "Client ID do Omada" "")
OMADA_CLIENT_SECRET=$(read_input "Client Secret do Omada" "")
OMADA_OMADAC_ID=$(read_input "Omadac ID" "")

# Baixar aplicação
log_info "Baixando aplicação do GitHub..."
REPO_URL="https://github.com/Joelferreira98/OmadaVoucherController.git"
INSTALL_DIR="/tmp/voucher-install"

rm -rf "$INSTALL_DIR"
if ! git clone "$REPO_URL" "$INSTALL_DIR"; then
    log_error "Erro ao baixar aplicação do GitHub!"
    log_info "Verifique se o repositório existe e tem os arquivos necessários."
    exit 1
fi

# Verificar arquivos
cd "$INSTALL_DIR"
if [ ! -f "app.py" ] || [ ! -f "main.py" ]; then
    log_error "Arquivos da aplicação não encontrados!"
    ls -la
    exit 1
fi

log_success "Aplicação baixada com sucesso!"

# Instalar aplicação
log_info "Copiando arquivos para /opt/voucher-app..."
mkdir -p /opt/voucher-app
cp -r "$INSTALL_DIR"/* /opt/voucher-app/
chown -R voucher:voucher /opt/voucher-app/

cd /opt/voucher-app

# Criar ambiente virtual
log_info "Criando ambiente virtual..."
sudo -u voucher python3 -m venv venv
if [ ! -d "venv" ]; then
    log_error "Erro ao criar ambiente virtual!"
    exit 1
fi

# Atualizar pip
log_info "Atualizando pip..."
sudo -u voucher ./venv/bin/pip install --upgrade pip

# Instalar dependências
log_info "Instalando dependências Python..."
sudo -u voucher ./venv/bin/pip install Flask==3.0.0 || { log_error "Erro ao instalar Flask"; exit 1; }
sudo -u voucher ./venv/bin/pip install Flask-SQLAlchemy==3.1.1 || { log_error "Erro ao instalar Flask-SQLAlchemy"; exit 1; }
sudo -u voucher ./venv/bin/pip install PyMySQL==1.1.0 || { log_error "Erro ao instalar PyMySQL"; exit 1; }
sudo -u voucher ./venv/bin/pip install gunicorn==21.2.0 || { log_error "Erro ao instalar Gunicorn"; exit 1; }

# Instalar outras dependências
log_info "Instalando dependências restantes..."
sudo -u voucher ./venv/bin/pip install Flask-Login Flask-WTF WTForms email-validator Werkzeug SQLAlchemy reportlab requests PyJWT oauthlib

# Criar arquivo de configuração
log_info "Criando arquivo de configuração..."
cat > /opt/voucher-app/.env << EOF
DATABASE_URL=$DATABASE_URL
SESSION_SECRET=$SESSION_SECRET
OMADA_CONTROLLER_URL=$OMADA_URL
OMADA_CLIENT_ID=$OMADA_CLIENT_ID
OMADA_CLIENT_SECRET=$OMADA_CLIENT_SECRET
OMADA_OMADAC_ID=$OMADA_OMADAC_ID
EOF

chown voucher:voucher /opt/voucher-app/.env

# Testar importação
log_info "Testando importação da aplicação..."
cd /opt/voucher-app

# Criar script de teste
cat > test_import.py << EOF
#!/usr/bin/env python3
import os
import sys

# Configurar variáveis
os.environ['DATABASE_URL'] = '$DATABASE_URL'
os.environ['SESSION_SECRET'] = '$SESSION_SECRET'
os.environ['OMADA_CONTROLLER_URL'] = '$OMADA_URL'
os.environ['OMADA_CLIENT_ID'] = '$OMADA_CLIENT_ID'
os.environ['OMADA_CLIENT_SECRET'] = '$OMADA_CLIENT_SECRET'
os.environ['OMADA_OMADAC_ID'] = '$OMADA_OMADAC_ID'

try:
    print("Testando importação...")
    from app import app, db
    print("✅ Importação OK!")
    
    print("Testando banco de dados...")
    with app.app_context():
        db.create_all()
        print("✅ Banco de dados OK!")
        
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("✅ Teste completo!")
EOF

chmod +x test_import.py
chown voucher:voucher test_import.py

# Executar teste
log_info "Executando teste de importação..."
if sudo -u voucher ./venv/bin/python test_import.py; then
    log_success "Teste de importação passou!"
else
    log_error "Erro no teste de importação!"
    exit 1
fi

# Configurar Gunicorn
log_info "Configurando Gunicorn..."
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
log_info "Configurando Supervisor..."
cat > /etc/supervisor/conf.d/voucher-app.conf << EOF
[program:voucher-app]
command=/opt/voucher-app/venv/bin/gunicorn --config /opt/voucher-app/gunicorn.conf.py main:app
directory=/opt/voucher-app
user=voucher
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/voucher-app.log
environment=DATABASE_URL="$DATABASE_URL",SESSION_SECRET="$SESSION_SECRET",OMADA_CONTROLLER_URL="$OMADA_URL",OMADA_CLIENT_ID="$OMADA_CLIENT_ID",OMADA_CLIENT_SECRET="$OMADA_CLIENT_SECRET",OMADA_OMADAC_ID="$OMADA_OMADAC_ID"
EOF

# Configurar Nginx
log_info "Configurando Nginx..."
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
log_info "Reiniciando serviços..."
systemctl restart nginx
systemctl restart supervisor
supervisorctl reread
supervisorctl update
supervisorctl start voucher-app

# Verificar status
log_info "Verificando status..."
sleep 5

if supervisorctl status voucher-app | grep -q "RUNNING"; then
    log_success "Aplicação está rodando!"
    
    # Testar resposta
    if curl -s http://localhost:5000 > /dev/null; then
        log_success "Aplicação responde corretamente!"
    else
        log_error "Aplicação não responde na porta 5000"
    fi
else
    log_error "Aplicação não está rodando!"
    supervisorctl status voucher-app
    echo "--- Logs ---"
    tail -20 /var/log/voucher-app.log
fi

# Limpar
rm -rf "$INSTALL_DIR"
rm -f test_import.py

echo ""
echo "========================================="
echo "🎉 INSTALAÇÃO CONCLUÍDA!"
echo "========================================="
echo ""
echo "Acesso: http://$(curl -s ifconfig.me || hostname -I | awk '{print $1}')"
echo "Usuário: master"
echo "Senha: admin123"
echo ""
echo "Logs: tail -f /var/log/voucher-app.log"
echo "Status: supervisorctl status voucher-app"
echo ""