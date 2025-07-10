#!/bin/bash

# Script de instalação para VPS Ubuntu/Debian
# Voucher Management System - Instalação Automática

set -e  # Parar em caso de erro

echo "========================================================="
echo "  Sistema de Gerenciamento de Vouchers - Instalação VPS"
echo "========================================================="
echo ""

# Função para input seguro
read_input() {
    local prompt="$1"
    local default="$2"
    local value
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " value
        echo "${value:-$default}"
    else
        read -p "$prompt: " value
        echo "$value"
    fi
}

# Função para input de senha
read_password() {
    local prompt="$1"
    local password
    
    read -s -p "$prompt: " password
    echo ""
    echo "$password"
}

echo "Este script irá instalar o sistema completo na VPS."
echo "Você precisará fornecer algumas configurações durante a instalação."
echo ""

# Verificar se está rodando como root
#if [ "$EUID" -eq 0 ]; then
#    echo "⚠️  Este script não deve ser #executado como root."
#    echo "Execute: bash install_vps.sh"
#    exit 1
#fi

echo "✓ Iniciando instalação..."

# Solicitar configurações do banco de dados primeiro
echo ""
echo "=== Configuração do Banco de Dados ==="
echo "Escolha o tipo de banco de dados:"
echo "1. MySQL Local (instalar na VPS)"
echo "2. MySQL/MariaDB Remoto (banco online)"
echo "3. PostgreSQL Remoto"
echo ""

while true; do
    read -p "Digite sua escolha (1-3): " DB_CHOICE
    case $DB_CHOICE in
        1|2|3) break;;
        *) echo "Opção inválida. Digite 1, 2 ou 3.";;
    esac
done

# Atualizar sistema
echo ""
echo "Atualizando sistema..."
sudo apt update && sudo apt upgrade -y

# Instalar dependências do sistema
echo "Instalando dependências básicas..."
sudo apt install -y python3 python3-pip python3-venv nginx supervisor git curl

# Instalar banco de dados específico
if [ "$DB_CHOICE" = "1" ]; then
    echo "Instalando MySQL local..."
    sudo apt install -y mysql-server
elif [ "$DB_CHOICE" = "2" ]; then
    echo "Instalando cliente MySQL para conexão remota..."
    sudo apt install -y mysql-client
elif [ "$DB_CHOICE" = "3" ]; then
    echo "Instalando cliente PostgreSQL para conexão remota..."
    sudo apt install -y postgresql-client
fi

# Criar usuário para a aplicação
echo "Criando usuário voucher..."
sudo useradd -m -s /bin/bash voucher
sudo usermod -aG sudo voucher

# Configurar MySQL local se necessário
if [ "$DB_CHOICE" = "1" ]; then
    echo "Configurando MySQL local..."
    sudo systemctl start mysql
    sudo systemctl enable mysql
fi

# Configurar conexão do banco de dados
echo ""
echo "=== Configuração da Conexão do Banco ==="

if [ "$DB_CHOICE" = "1" ]; then
    # MySQL Local
    echo "Configurando MySQL Local..."
    DB_HOST="localhost"
    DB_PORT="3306"
    DB_ROOT_PASSWORD=$(read_password "Digite a senha para o usuário root do MySQL")
    DB_NAME=$(read_input "Nome do banco de dados" "voucher_db")
    DB_USER=$(read_input "Usuário do banco de dados" "voucher")
    DB_PASSWORD=$(read_password "Senha do usuário do banco de dados")
    
    # Configurar MySQL Local
    echo "Configurando MySQL local..."
    sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '$DB_ROOT_PASSWORD';"
    sudo mysql -u root -p$DB_ROOT_PASSWORD -e "FLUSH PRIVILEGES;"
    
    # Criar banco de dados e usuário
    sudo mysql -u root -p$DB_ROOT_PASSWORD -e "CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    sudo mysql -u root -p$DB_ROOT_PASSWORD -e "CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';"
    sudo mysql -u root -p$DB_ROOT_PASSWORD -e "GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';"
    sudo mysql -u root -p$DB_ROOT_PASSWORD -e "FLUSH PRIVILEGES;"
    
    DATABASE_URL="mysql+pymysql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
    
elif [ "$DB_CHOICE" = "2" ]; then
    # MySQL/MariaDB Remoto
    echo "Configurando MySQL/MariaDB Remoto..."
    DB_HOST=$(read_input "Host do banco de dados" "")
    DB_PORT=$(read_input "Porta do banco de dados" "3306")
    DB_NAME=$(read_input "Nome do banco de dados" "voucher_db")
    DB_USER=$(read_input "Usuário do banco de dados" "")
    DB_PASSWORD=$(read_password "Senha do banco de dados")
    
    # Validar campos obrigatórios
    if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
        echo "❌ Host, usuário e senha são obrigatórios para banco remoto!"
        exit 1
    fi
    
    DATABASE_URL="mysql+pymysql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
    
    # Teste de conexão
    echo "Testando conexão com banco remoto..."
    if command -v mysql &> /dev/null; then
        mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "SELECT 1;" &>/dev/null
        if [ $? -eq 0 ]; then
            echo "✓ Conexão com banco remoto bem-sucedida!"
        else
            echo "⚠️  Não foi possível testar a conexão. Continuando mesmo assim..."
        fi
    else
        echo "ℹ️  Cliente MySQL não disponível para teste. Continuando..."
    fi
    
elif [ "$DB_CHOICE" = "3" ]; then
    # PostgreSQL Remoto
    echo "Configurando PostgreSQL Remoto..."
    DB_HOST=$(read_input "Host do banco de dados" "")
    DB_PORT=$(read_input "Porta do banco de dados" "5432")
    DB_NAME=$(read_input "Nome do banco de dados" "voucher_db")
    DB_USER=$(read_input "Usuário do banco de dados" "")
    DB_PASSWORD=$(read_password "Senha do banco de dados")
    
    # Validar campos obrigatórios
    if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
        echo "❌ Host, usuário e senha são obrigatórios para banco remoto!"
        exit 1
    fi
    
    DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
    
    # Teste de conexão
    echo "Testando conexão com PostgreSQL remoto..."
    if command -v psql &> /dev/null; then
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &>/dev/null
        if [ $? -eq 0 ]; then
            echo "✓ Conexão com PostgreSQL remoto bem-sucedida!"
        else
            echo "⚠️  Não foi possível testar a conexão. Continuando mesmo assim..."
        fi
    else
        echo "ℹ️  Cliente PostgreSQL não disponível para teste. Continuando..."
    fi
fi

# Criar diretório da aplicação
echo "Criando diretório da aplicação..."
sudo mkdir -p /opt/voucher-app
sudo chown voucher:voucher /opt/voucher-app

# Solicitar configurações da aplicação
echo ""
echo "=== Configuração da Aplicação ==="
SESSION_SECRET=$(read_input "Chave secreta da aplicação (deixe vazio para gerar automaticamente)")
if [ -z "$SESSION_SECRET" ]; then
    SESSION_SECRET=$(openssl rand -hex 32)
    echo "✓ Chave secreta gerada automaticamente"
fi

echo ""
echo "=== Configuração do Omada Controller ==="
OMADA_URL=$(read_input "URL do Omada Controller" "https://controller.local:8043")
OMADA_CLIENT_ID=$(read_input "Client ID do Omada")
OMADA_CLIENT_SECRET=$(read_input "Client Secret do Omada")
OMADA_OMADAC_ID=$(read_input "Omadac ID")

echo ""
echo "=== Configuração do Domínio ==="
DOMAIN_NAME=$(read_input "Nome do domínio (deixe vazio para usar IP)" "")

# Verificar se os arquivos da aplicação estão presentes
echo ""
echo "=== Copiando Arquivos da Aplicação ==="

# Verificar se estamos executando de dentro da pasta da aplicação
if [ -f "app.py" ] && [ -f "main.py" ] && [ -f "requirements.txt" ]; then
    echo "✓ Arquivos da aplicação encontrados no diretório atual"
    echo "Copiando arquivos para /opt/voucher-app..."
    sudo cp -r . /opt/voucher-app/
    sudo chown -R voucher:voucher /opt/voucher-app/
elif [ -d "voucher-app" ]; then
    echo "✓ Pasta voucher-app encontrada"
    echo "Copiando arquivos para /opt/voucher-app..."
    sudo cp -r voucher-app/* /opt/voucher-app/
    sudo chown -R voucher:voucher /opt/voucher-app/
else
    echo "❌ Arquivos da aplicação não encontrados!"
    echo ""
    echo "Para usar este script, você deve:"
    echo "1. Fazer upload dos arquivos da aplicação para a VPS"
    echo "2. Executar o script de dentro da pasta da aplicação"
    echo ""
    echo "Exemplo:"
    echo "  scp -r * usuario@vps:/tmp/voucher-app/"
    echo "  ssh usuario@vps"
    echo "  cd /tmp/voucher-app"
    echo "  bash install_vps.sh"
    exit 1
fi

echo "Configurando aplicação..."
cd /opt/voucher-app

# Criar ambiente virtual
sudo -u voucher python3 -m venv venv
sudo -u voucher ./venv/bin/pip install --upgrade pip

# Instalar dependências Python básicas
echo "Instalando dependências Python..."
sudo -u voucher ./venv/bin/pip install Flask==3.0.0
sudo -u voucher ./venv/bin/pip install Flask-SQLAlchemy==3.1.1
sudo -u voucher ./venv/bin/pip install Flask-Login==0.6.3
sudo -u voucher ./venv/bin/pip install Flask-WTF==1.2.1
sudo -u voucher ./venv/bin/pip install WTForms==3.1.0
sudo -u voucher ./venv/bin/pip install email-validator==2.1.0
sudo -u voucher ./venv/bin/pip install Werkzeug==3.0.1
sudo -u voucher ./venv/bin/pip install gunicorn==21.2.0
sudo -u voucher ./venv/bin/pip install SQLAlchemy==2.0.23
sudo -u voucher ./venv/bin/pip install reportlab==4.0.7
sudo -u voucher ./venv/bin/pip install requests==2.31.0
sudo -u voucher ./venv/bin/pip install PyJWT==2.8.0
sudo -u voucher ./venv/bin/pip install oauthlib==3.2.2

# Instalar driver de banco específico
if [ "$DB_CHOICE" = "1" ] || [ "$DB_CHOICE" = "2" ]; then
    echo "Instalando driver MySQL (PyMySQL)..."
    sudo -u voucher ./venv/bin/pip install PyMySQL==1.1.0
elif [ "$DB_CHOICE" = "3" ]; then
    echo "Instalando driver PostgreSQL (psycopg2)..."
    sudo -u voucher ./venv/bin/pip install psycopg2-binary==2.9.7
fi

# Criar arquivo de configuração de ambiente
echo "Criando arquivo de configuração..."
sudo -u voucher cat > /opt/voucher-app/.env << EOF
# Configurações da aplicação
SESSION_SECRET=$SESSION_SECRET
DATABASE_URL=$DATABASE_URL

# Configurações do Omada Controller
OMADA_CONTROLLER_URL=$OMADA_URL
OMADA_CLIENT_ID=$OMADA_CLIENT_ID
OMADA_CLIENT_SECRET=$OMADA_CLIENT_SECRET
OMADA_OMADAC_ID=$OMADA_OMADAC_ID
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
if [ -n "$DOMAIN_NAME" ]; then
    SERVER_NAME="$DOMAIN_NAME www.$DOMAIN_NAME"
else
    SERVER_NAME="_"
fi

sudo cat > /etc/nginx/sites-available/voucher-app << EOF
server {
    listen 80;
    server_name $SERVER_NAME;

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
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
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

# Inicializar a aplicação
echo ""
echo "=== Inicializando Aplicação ==="
echo "Carregando configurações do supervisor..."
sudo supervisorctl reread
sudo supervisorctl update

echo "Iniciando aplicação..."
sudo supervisorctl start voucher-app

# Verificar status
sleep 3
APP_STATUS=$(sudo supervisorctl status voucher-app | awk '{print $2}')

if [ "$APP_STATUS" = "RUNNING" ]; then
    echo "✓ Aplicação iniciada com sucesso!"
else
    echo "❌ Erro ao iniciar aplicação. Status: $APP_STATUS"
    echo "Verificando logs..."
    sudo tail -20 /var/log/voucher-app/supervisor.log
fi

# Configurar SSL se domínio foi fornecido
if [ -n "$DOMAIN_NAME" ]; then
    echo ""
    echo "=== Configuração SSL (Opcional) ==="
    read -p "Deseja instalar certificado SSL com Let's Encrypt? (y/n): " INSTALL_SSL
    
    if [ "$INSTALL_SSL" = "y" ] || [ "$INSTALL_SSL" = "Y" ]; then
        echo "Instalando Certbot..."
        sudo apt install -y certbot python3-certbot-nginx
        
        echo "Obtendo certificado SSL..."
        sudo certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME
        
        # Configurar renovação automática
        echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
        echo "✓ SSL configurado e renovação automática ativada"
    fi
fi

echo ""
echo "========================================================="
echo "            🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO! 🎉"
echo "========================================================="
echo ""
echo "📋 RESUMO DA INSTALAÇÃO:"
if [ "$DB_CHOICE" = "1" ]; then
    echo "  • Banco de dados: MySQL Local ($DB_NAME)"
elif [ "$DB_CHOICE" = "2" ]; then
    echo "  • Banco de dados: MySQL Remoto ($DB_HOST:$DB_PORT/$DB_NAME)"
elif [ "$DB_CHOICE" = "3" ]; then
    echo "  • Banco de dados: PostgreSQL Remoto ($DB_HOST:$DB_PORT/$DB_NAME)"
fi
echo "  • Usuário da aplicação: voucher"
echo "  • Localização: /opt/voucher-app"
if [ -n "$DOMAIN_NAME" ]; then
    echo "  • Domínio: https://$DOMAIN_NAME"
else
    echo "  • Acesso: http://$(curl -s ifconfig.me || hostname -I | awk '{print $1}')"
fi
echo ""
echo "🔐 CREDENCIAIS PADRÃO:"
echo "  • Usuário: master"
echo "  • Senha: admin123"
echo ""
echo "⚙️  COMANDOS ÚTEIS:"
echo "  • Status: sudo supervisorctl status voucher-app"
echo "  • Reiniciar: sudo supervisorctl restart voucher-app"
echo "  • Logs: sudo tail -f /var/log/voucher-app/supervisor.log"
echo "  • Nginx: sudo systemctl status nginx"
echo ""
echo "📁 ARQUIVOS IMPORTANTES:"
echo "  • Configuração: /opt/voucher-app/.env"
echo "  • Logs: /var/log/voucher-app/"
echo "  • Nginx: /etc/nginx/sites-available/voucher-app"
echo ""
echo "🔄 BACKUP AUTOMÁTICO:"
echo "  • Execute: /opt/voucher-app/create_backup.sh"
echo ""

# Criar script de backup
sudo -u voucher cat > /opt/voucher-app/create_backup.sh << 'EOF'
#!/bin/bash
# Script de backup automático

BACKUP_DIR="/opt/voucher-app/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup do banco
source /opt/voucher-app/.env

if [[ $DATABASE_URL == mysql* ]]; then
    # MySQL/MariaDB backup
    DB_PARAMS=$(echo $DATABASE_URL | sed -n 's/mysql+pymysql:\/\/\([^:]*\):\([^@]*\)@\([^:]*\):\([^\/]*\)\/\(.*\)/\1 \2 \3 \4 \5/p')
    DB_USER=$(echo $DB_PARAMS | awk '{print $1}')
    DB_PASS=$(echo $DB_PARAMS | awk '{print $2}')
    DB_HOST=$(echo $DB_PARAMS | awk '{print $3}')
    DB_PORT=$(echo $DB_PARAMS | awk '{print $4}')
    DB_NAME=$(echo $DB_PARAMS | awk '{print $5}')
    
    mysqldump -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS $DB_NAME > $BACKUP_DIR/db_$DATE.sql
    
elif [[ $DATABASE_URL == postgresql* ]]; then
    # PostgreSQL backup
    DB_PARAMS=$(echo $DATABASE_URL | sed -n 's/postgresql:\/\/\([^:]*\):\([^@]*\)@\([^:]*\):\([^\/]*\)\/\(.*\)/\1 \2 \3 \4 \5/p')
    DB_USER=$(echo $DB_PARAMS | awk '{print $1}')
    DB_PASS=$(echo $DB_PARAMS | awk '{print $2}')
    DB_HOST=$(echo $DB_PARAMS | awk '{print $3}')
    DB_PORT=$(echo $DB_PARAMS | awk '{print $4}')
    DB_NAME=$(echo $DB_PARAMS | awk '{print $5}')
    
    PGPASSWORD=$DB_PASS pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME > $BACKUP_DIR/db_$DATE.sql
fi

# Backup dos arquivos
tar -czf $BACKUP_DIR/files_$DATE.tar.gz /opt/voucher-app --exclude=/opt/voucher-app/backups

# Manter apenas os últimos 7 backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "✓ Backup criado: $BACKUP_DIR/db_$DATE.sql"
echo "✓ Backup criado: $BACKUP_DIR/files_$DATE.tar.gz"
EOF

sudo chmod +x /opt/voucher-app/create_backup.sh

echo "✅ Sistema pronto para uso!"
echo ""