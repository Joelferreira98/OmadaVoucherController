# Guia de Deployment - Sistema de Vouchers

## Pré-requisitos da VPS

### Especificações Mínimas Recomendadas:
- **RAM**: 2GB mínimo (4GB recomendado)
- **CPU**: 1 core mínimo (2 cores recomendado)
- **Armazenamento**: 20GB mínimo
- **Sistema Operacional**: Ubuntu 20.04+ ou Debian 11+
- **Conexão**: Banda larga estável

## Método 1: Instalação Automática (Recomendado)

### 1. Preparar a VPS
```bash
# Conectar à VPS via SSH
ssh root@SEU_IP_DA_VPS

# Baixar script de instalação
wget https://raw.githubusercontent.com/seu-usuario/voucher-app/main/install_vps.sh
chmod +x install_vps.sh

# Executar instalação
./install_vps.sh
```

### 2. Copiar arquivos da aplicação
```bash
# Criar diretório temporário
mkdir ~/voucher-temp
cd ~/voucher-temp

# Copiar arquivos da aplicação (via SCP, SFTP ou Git)
# Exemplo com SCP:
scp -r /caminho/local/da/aplicacao/* root@SEU_IP_DA_VPS:~/voucher-temp/

# Mover arquivos para diretório final
sudo cp -r ~/voucher-temp/* /opt/voucher-app/
sudo chown -R voucher:voucher /opt/voucher-app/
```

### 3. Configurar ambiente
```bash
# Editar arquivo de configuração
sudo nano /opt/voucher-app/.env

# Configurar credenciais do Omada Controller
SESSION_SECRET=sua_chave_secreta_muito_forte_aqui_123456789
DATABASE_URL=postgresql://voucher:voucher_password_123@localhost:5432/voucher_db
OMADA_CONTROLLER_URL=https://seu-omada-controller.com:8043
OMADA_CLIENT_ID=seu_client_id
OMADA_CLIENT_SECRET=seu_client_secret
OMADA_OMADAC_ID=seu_omadac_id
```

### 4. Iniciar aplicação
```bash
# Atualizar supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Iniciar aplicação
sudo supervisorctl start voucher-app

# Verificar status
sudo supervisorctl status voucher-app
```

## Método 2: Instalação Manual

### 1. Atualizar sistema
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Instalar dependências
```bash
sudo apt install -y python3 python3-pip python3-venv nginx mysql-server supervisor git curl
```

### 3. Configurar MySQL
```bash
sudo systemctl start mysql
sudo systemctl enable mysql

# Configurar MySQL
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root_password_123';"
sudo mysql -u root -proot_password_123 -e "FLUSH PRIVILEGES;"

# Criar usuário e banco
sudo mysql -u root -proot_password_123 -e "CREATE DATABASE voucher_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -u root -proot_password_123 -e "CREATE USER 'voucher'@'localhost' IDENTIFIED BY 'voucher_password_123';"
sudo mysql -u root -proot_password_123 -e "GRANT ALL PRIVILEGES ON voucher_db.* TO 'voucher'@'localhost';"
sudo mysql -u root -proot_password_123 -e "FLUSH PRIVILEGES;"
```

### 4. Configurar aplicação
```bash
# Criar usuário
sudo useradd -m -s /bin/bash voucher

# Criar diretório
sudo mkdir -p /opt/voucher-app
sudo chown voucher:voucher /opt/voucher-app

# Copiar arquivos da aplicação
cd /opt/voucher-app

# Criar ambiente virtual
sudo -u voucher python3 -m venv venv
sudo -u voucher ./venv/bin/pip install --upgrade pip

# Instalar dependências
sudo -u voucher ./venv/bin/pip install Flask Flask-SQLAlchemy Flask-Login Flask-WTF WTForms email-validator Werkzeug gunicorn PyMySQL SQLAlchemy reportlab requests PyJWT oauthlib
```

### 5. Configurar Nginx
```bash
# Criar configuração
sudo nano /etc/nginx/sites-available/voucher-app

# Conteúdo do arquivo (ver install_vps.sh para detalhes)
# Ativar site
sudo ln -s /etc/nginx/sites-available/voucher-app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Configurar Supervisor
```bash
# Criar configuração
sudo nano /etc/supervisor/conf.d/voucher-app.conf

# Conteúdo do arquivo (ver install_vps.sh para detalhes)
# Reiniciar supervisor
sudo systemctl restart supervisor
```

## Configuração de Domínio e SSL

### 1. Configurar domínio
```bash
# Editar configuração do Nginx
sudo nano /etc/nginx/sites-available/voucher-app

# Alterar linha:
server_name seudominio.com www.seudominio.com;

# Reiniciar Nginx
sudo systemctl reload nginx
```

### 2. Instalar SSL com Certbot
```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado
sudo certbot --nginx -d seudominio.com -d www.seudominio.com

# Configurar renovação automática
sudo crontab -e
# Adicionar linha:
0 12 * * * /usr/bin/certbot renew --quiet
```

## Monitoramento e Manutenção

### Comandos úteis:
```bash
# Status da aplicação
sudo supervisorctl status voucher-app

# Reiniciar aplicação
sudo supervisorctl restart voucher-app

# Ver logs da aplicação
sudo tail -f /var/log/voucher-app/supervisor.log

# Ver logs do Nginx
sudo tail -f /var/log/nginx/voucher-app-access.log
sudo tail -f /var/log/nginx/voucher-app-error.log

# Status do banco de dados
sudo systemctl status mysql

# Backup do banco
mysqldump -u voucher -pvoucher_password_123 voucher_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Problemas comuns:

1. **Aplicação não inicia**: Verificar logs do supervisor
2. **Erro de banco**: Verificar se MySQL está rodando
3. **Erro 502**: Verificar se Gunicorn está rodando na porta 5000
4. **Arquivos estáticos não carregam**: Verificar permissões em /opt/voucher-app/static/

## Backup e Restauração

### Backup automático:
```bash
# Criar script de backup
sudo nano /opt/voucher-app/backup.sh

#!/bin/bash
BACKUP_DIR="/opt/voucher-app/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Criar diretório de backup
mkdir -p $BACKUP_DIR

# Backup do banco
mysqldump -u voucher -pvoucher_password_123 voucher_db > $BACKUP_DIR/db_$DATE.sql

# Backup dos arquivos
tar -czf $BACKUP_DIR/files_$DATE.tar.gz /opt/voucher-app --exclude=/opt/voucher-app/backups

# Manter apenas os últimos 7 backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

# Tornar executável
chmod +x /opt/voucher-app/backup.sh

# Agendar backup diário
sudo crontab -e
# Adicionar linha:
0 2 * * * /opt/voucher-app/backup.sh
```

## Configuração de Produção

### Variáveis de ambiente importantes:
```bash
# /opt/voucher-app/.env
SESSION_SECRET=chave_muito_forte_e_unica
DATABASE_URL=mysql+pymysql://voucher:senha_forte@localhost:3306/voucher_db
OMADA_CONTROLLER_URL=https://seu-controller.com:8043
OMADA_CLIENT_ID=seu_client_id
OMADA_CLIENT_SECRET=seu_client_secret
OMADA_OMADAC_ID=seu_omadac_id
```

### Segurança:
- Alterar senhas padrão
- Configurar firewall
- Manter sistema atualizado
- Backup regular
- Monitoramento de logs

## Suporte

Para problemas ou dúvidas:
1. Verificar logs da aplicação
2. Consultar documentação do Omada Controller
3. Verificar conectividade de rede
4. Revisar configurações de firewall