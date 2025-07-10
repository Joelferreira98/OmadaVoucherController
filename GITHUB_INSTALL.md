# 🚀 Instalação via GitHub

Esta é a maneira mais simples de instalar o sistema de vouchers na sua VPS.

## Método 1: Instalação em Uma Linha (Recomendado)

Execute este comando na sua VPS como root:

```bash
curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/quick_install.sh | sudo bash
```

## Método 2: Instalação Manual

```bash
# 1. Baixar o script
curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/github_install.sh -o install.sh

# 2. Dar permissão
chmod +x install.sh

# 3. Executar como root
sudo ./install.sh
```

## ⚙️ O que o Script Faz Automaticamente

### Sistema
- ✅ Atualiza o sistema operacional
- ✅ Instala Python 3, pip, venv
- ✅ Instala nginx, supervisor, firewall
- ✅ Cria usuário dedicado para a aplicação

### Aplicação
- ✅ Baixa o código fonte do GitHub
- ✅ Cria ambiente virtual Python
- ✅ Instala todas as dependências
- ✅ Configura banco de dados (local ou remoto)
- ✅ Configura arquivos de ambiente

### Serviços
- ✅ Configura nginx como proxy reverso
- ✅ Configura supervisor para gerenciar a aplicação
- ✅ Configura firewall para segurança
- ✅ Opção para SSL com Let's Encrypt

## 🗄️ Opções de Banco de Dados

Durante a instalação, você pode escolher:

1. **MySQL Local** - Instalado e configurado automaticamente
2. **MySQL Remoto** - Você fornece as credenciais
3. **PostgreSQL Remoto** - Você fornece as credenciais

## 🔧 Configurações Solicitadas

O script pedirá as seguintes informações:

### Banco de Dados (se remoto)
- Host do banco
- Porta (padrão 3306 para MySQL, 5432 para PostgreSQL)
- Nome do banco
- Usuário e senha

### Aplicação
- Chave secreta (pode ser gerada automaticamente)
- URL do Omada Controller
- Client ID e Client Secret do Omada
- Omadac ID

### Domínio (opcional)
- Nome do domínio para SSL
- Configuração automática de Let's Encrypt

## 🚦 Após a Instalação

### Credenciais Padrão
- **Usuário**: master
- **Senha**: admin123

### Comandos Úteis
```bash
# Verificar status
sudo supervisorctl status voucher-app

# Ver logs
sudo tail -f /var/log/voucher-app/supervisor.log

# Reiniciar aplicação
sudo supervisorctl restart voucher-app

# Status do nginx
sudo systemctl status nginx
```

### Arquivos Importantes
- **Configuração**: `/opt/voucher-app/.env`
- **Logs**: `/var/log/voucher-app/`
- **Aplicação**: `/opt/voucher-app/`

## 🔍 Resolução de Problemas

### Aplicação não inicia
```bash
# Verificar logs
sudo tail -50 /var/log/voucher-app/supervisor.log

# Verificar configuração
sudo cat /opt/voucher-app/.env

# Testar conexão com banco
cd /opt/voucher-app
sudo -u voucher ./venv/bin/python -c "from app import db; print('DB OK')"
```

### Erro de conexão com banco
```bash
# Verificar se o banco existe
mysql -h SEU_HOST -u SEU_USER -p -e "SHOW DATABASES;"

# Verificar se o usuário tem permissões
mysql -h SEU_HOST -u SEU_USER -p -e "SELECT USER();"
```

### Problemas com SSL
```bash
# Verificar certificado
sudo certbot certificates

# Renovar certificado
sudo certbot renew --dry-run
```

## 🛡️ Segurança

O script automaticamente:
- Cria usuário dedicado sem shell
- Configura firewall básico
- Usa proxy reverso nginx
- Opção para HTTPS com Let's Encrypt

## 📱 Acesso

Após a instalação, acesse:
- **Com domínio**: `http://seudominio.com`
- **Com IP**: `http://IP_DA_VPS`

## 🆘 Suporte

Se tiver problemas:
1. Verifique os logs da aplicação
2. Confirme as credenciais do banco
3. Verifique se as portas estão abertas
4. Teste a conexão com o Omada Controller

## 🔄 Atualização

Para atualizar a aplicação:
```bash
# Parar aplicação
sudo supervisorctl stop voucher-app

# Baixar nova versão
cd /tmp
git clone https://github.com/Joelferreira98/OmadaVoucherController voucher-update
sudo cp -r voucher-update/* /opt/voucher-app/
sudo chown -R voucher:voucher /opt/voucher-app/

# Atualizar dependências se necessário
cd /opt/voucher-app
sudo -u voucher ./venv/bin/pip install --upgrade -r requirements.txt

# Reiniciar aplicação
sudo supervisorctl start voucher-app
```

---

**Pronto!** Sua aplicação estará funcionando em poucos minutos! 🎉