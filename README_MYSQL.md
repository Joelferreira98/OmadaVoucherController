# Sistema de Vouchers - Configuração MySQL

Este documento descreve como configurar e instalar o Sistema de Vouchers com banco de dados MySQL.

## Arquivos de Configuração MySQL

### 1. `mysql_setup.sql`
Script SQL completo para configurar o banco de dados MySQL:
- Cria o banco de dados `voucher_system`
- Cria usuário `voucher_user` com senha `voucher_password_2024`
- Define todas as tabelas necessárias
- Insere usuários padrão para teste
- Configura índices para melhor performance

### 2. `.env.mysql`
Arquivo de configuração de ambiente para MySQL:
- Configurações da aplicação Flask
- String de conexão MySQL
- Configurações do Omada Controller
- Parâmetros de segurança e performance

### 3. `install_mysql.sh`
Script automatizado de instalação completo:
- Instala MySQL Server e dependências
- Configura banco de dados automaticamente
- Configura Nginx e Supervisor
- Define permissões e segurança
- Cria scripts de backup

### 4. `migrate_to_mysql.py`
Script de migração do PostgreSQL para MySQL:
- Exporta dados do PostgreSQL
- Importa dados para MySQL
- Mantém integridade referencial
- Gera log detalhado da migração

## Instalação Rápida

### Opção 1: Instalação Automatizada
```bash
# Tornar script executável
chmod +x install_mysql.sh

# Executar como root
sudo ./install_mysql.sh
```

### Opção 2: Instalação Manual

#### 1. Instalar MySQL
```bash
sudo apt update
sudo apt install mysql-server mysql-client
sudo mysql_secure_installation
```

#### 2. Configurar Banco de Dados
```bash
# Executar script SQL como root do MySQL
mysql -u root -p < mysql_setup.sql
```

#### 3. Configurar Aplicação
```bash
# Copiar configuração de ambiente
cp .env.mysql .env

# Editar configurações do Omada Controller
nano .env
```

#### 4. Instalar Dependências Python
```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install flask flask-sqlalchemy flask-login flask-wtf pymysql gunicorn
```

#### 5. Testar Aplicação
```bash
# Executar aplicação
python main.py
```

## Migração do PostgreSQL

Se você já tem dados no PostgreSQL e quer migrar para MySQL:

### 1. Preparar Arquivos
```bash
# Ter .env (PostgreSQL atual) e .env.mysql (nova configuração)
ls -la .env*
```

### 2. Executar Migração
```bash
# Instalar dependências de migração
pip install mysql-connector-python psycopg2-binary

# Executar script de migração
python migrate_to_mysql.py
```

### 3. Ativar MySQL
```bash
# Backup configuração PostgreSQL
mv .env .env.postgresql

# Ativar configuração MySQL
mv .env.mysql .env

# Testar aplicação
python main.py
```

## Configurações Importantes

### String de Conexão MySQL
```bash
DATABASE_URL=mysql+pymysql://voucher_user:voucher_password_2024@localhost:3306/voucher_system
```

### Para MySQL Remoto
```bash
DATABASE_URL=mysql+pymysql://voucher_user:password@remote-server.com:3306/voucher_system
```

### Para MySQL com SSL
```bash
DATABASE_URL=mysql+pymysql://voucher_user:password@localhost:3306/voucher_system?ssl_disabled=false
```

## Usuários Padrão

Após a instalação, os seguintes usuários estarão disponíveis:

| Usuário | Senha | Tipo | Descrição |
|---------|-------|------|-----------|
| master | admin123 | Master | Acesso total ao sistema |
| joel | admin123 | Admin | Administrador de sites |
| jota | admin123 | Vendor | Vendedor de vouchers |

**⚠️ Importante:** Altere todas as senhas padrão após o primeiro login!

## Backup e Manutenção

### Backup Manual
```bash
# Backup completo
mysqldump -u voucher_user -p voucher_system > backup_$(date +%Y%m%d).sql

# Restaurar backup
mysql -u voucher_user -p voucher_system < backup_20240124.sql
```

### Backup Automático
O script de instalação cria um backup automático diário:
```bash
# Ver script de backup
cat /usr/local/bin/backup-voucher-db.sh

# Executar backup manual
sudo /usr/local/bin/backup-voucher-db.sh
```

## Monitoramento

### Logs da Aplicação
```bash
# Logs da aplicação
tail -f /var/log/voucher-app.log

# Logs do Supervisor
tail -f /var/log/supervisor/supervisord.log

# Logs do Nginx
tail -f /var/log/nginx/error.log
```

### Status dos Serviços
```bash
# Status da aplicação
supervisorctl status voucher-app

# Status do MySQL
systemctl status mysql

# Status do Nginx
systemctl status nginx
```

### Comandos de Manutenção
```bash
# Reiniciar aplicação
supervisorctl restart voucher-app

# Reiniciar MySQL
systemctl restart mysql

# Reiniciar Nginx
systemctl restart nginx
```

## Performance MySQL

### Configurações Recomendadas

Para melhor performance, adicione ao arquivo `/etc/mysql/mysql.conf.d/mysqld.cnf`:

```ini
[mysqld]
# Configurações básicas
max_connections = 100
innodb_buffer_pool_size = 128M
innodb_log_file_size = 64M

# Configurações específicas para aplicação
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# Cache e performance
query_cache_type = 1
query_cache_size = 16M
tmp_table_size = 16M
max_heap_table_size = 16M
```

### Otimização de Índices
```sql
-- Verificar uso de índices
SHOW INDEX FROM voucher_groups;

-- Analisar queries lentas
SHOW VARIABLES LIKE 'slow_query_log';
SET GLOBAL slow_query_log = 'ON';
```

## Troubleshooting

### Problemas Comuns

#### 1. Erro de Conexão MySQL
```bash
# Verificar se MySQL está rodando
systemctl status mysql

# Testar conexão
mysql -u voucher_user -p voucher_system
```

#### 2. Erro de Importação PyMySQL
```bash
# Instalar driver MySQL
pip install pymysql cryptography
```

#### 3. Erro de Permissões
```bash
# Verificar permissões do usuário MySQL
mysql -u root -p -e "SHOW GRANTS FOR 'voucher_user'@'localhost'"
```

#### 4. Aplicação Não Inicia
```bash
# Verificar logs
tail -f /var/log/voucher-app.log

# Testar aplicação manualmente
cd /opt/voucher-system
source venv/bin/activate
python main.py
```

## Suporte

Para problemas específicos do MySQL:

1. Verifique os logs de erro: `/var/log/mysql/error.log`
2. Teste a conexão de banco de dados
3. Verifique as configurações de firewall
4. Consulte a documentação oficial do MySQL

## Diferenças do PostgreSQL

| Aspecto | PostgreSQL | MySQL |
|---------|------------|-------|
| Tipo JSON | jsonb | JSON |
| Auto Increment | SERIAL | AUTO_INCREMENT |
| Booleano | BOOLEAN | TINYINT(1) |
| Charset | UTF8 | utf8mb4 |
| Case Sensitive | Sim | Não (por padrão) |

O sistema foi adaptado para funcionar perfeitamente com ambos os bancos de dados.