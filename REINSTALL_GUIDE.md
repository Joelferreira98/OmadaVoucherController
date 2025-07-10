# Guia de Remoção e Reinstalação - Omada Voucher Controller

## 🗑️ Remoção Completa da Instalação

Se você precisa remover completamente a instalação para fazer uma nova instalação limpa, siga estes passos:

### Opção 1: Remoção Padrão (Recomendada)

```bash
# Baixar e executar script de remoção
curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/uninstall.sh | sudo bash
```

### Opção 2: Limpeza Completa (Se ainda houver problemas)

```bash
# Baixar e executar script de limpeza completa
curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/cleanup.sh | sudo bash
```

### Opção 3: Remoção Manual

Se os scripts não funcionarem, execute manualmente:

```bash
# Parar serviços
sudo supervisorctl stop voucher-app
sudo systemctl stop supervisor
sudo systemctl stop nginx

# Remover configurações
sudo rm -f /etc/supervisor/conf.d/voucher-app.conf
sudo rm -f /etc/nginx/sites-available/voucher-app
sudo rm -f /etc/nginx/sites-enabled/voucher-app

# Remover aplicação
sudo rm -rf /opt/voucher-app

# Remover logs
sudo rm -rf /var/log/voucher-app
sudo rm -f /var/log/voucher-app.log

# Remover usuário
sudo userdel -r voucher

# Remover arquivos temporários
sudo rm -rf /tmp/voucher-install
sudo rm -rf /tmp/OmadaVoucherController*

# Reiniciar serviços
sudo systemctl restart nginx
sudo systemctl restart supervisor
```

## 🔍 Verificação da Remoção

Após a remoção, verifique se tudo foi removido corretamente:

```bash
# Verificar se não há processos rodando
ps aux | grep voucher
ps aux | grep gunicorn | grep main:app

# Verificar se arquivos foram removidos
ls -la /opt/ | grep voucher
ls -la /etc/supervisor/conf.d/ | grep voucher
ls -la /etc/nginx/sites-available/ | grep voucher

# Verificar se porta 5000 está livre
netstat -tlnp | grep :5000
```

## 🚀 Nova Instalação Limpa

Após a remoção completa, você pode fazer uma nova instalação:

### Instalação Rápida (Recomendada)

```bash
curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/quick_install.sh | sudo bash
```

### Instalação com Debug

```bash
curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/debug_install.sh | sudo bash
```

### Instalação Simplificada

```bash
curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/simple_install.sh | sudo bash
```

## 🔧 Resolução de Problemas

### Problema: Instalação anterior não foi completamente removida

**Solução:**
```bash
# Execute a limpeza completa
curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/cleanup.sh | sudo bash

# Aguarde alguns segundos
sleep 10

# Faça nova instalação
curl -fsSL https://raw.githubusercontent.com/Joelferreira98/OmadaVoucherController/main/quick_install.sh | sudo bash
```

### Problema: Porta 5000 ainda em uso

**Solução:**
```bash
# Matar processos na porta 5000
sudo fuser -k 5000/tcp

# Ou identificar e matar processo específico
sudo netstat -tlnp | grep :5000
sudo kill -9 [PID_DO_PROCESSO]
```

### Problema: Erro de permissão

**Solução:**
```bash
# Remover arquivos com sudo
sudo rm -rf /opt/voucher-app
sudo rm -rf /var/log/voucher-app*

# Verificar se usuário foi removido
sudo userdel -r voucher 2>/dev/null || true
```

### Problema: Nginx ou Supervisor não reinicia

**Solução:**
```bash
# Testar configuração do nginx
sudo nginx -t

# Forçar reinicialização
sudo systemctl restart nginx
sudo systemctl restart supervisor

# Verificar status
sudo systemctl status nginx
sudo systemctl status supervisor
```

## 📋 Checklist de Remoção

Antes de fazer nova instalação, verifique:

- [ ] Processos do voucher-app foram terminados
- [ ] Diretório `/opt/voucher-app` foi removido
- [ ] Configurações do nginx foram removidas
- [ ] Configurações do supervisor foram removidas
- [ ] Logs foram limpos
- [ ] Usuário `voucher` foi removido
- [ ] Porta 5000 está livre
- [ ] Nginx e Supervisor estão funcionando normalmente

## 💡 Dicas Importantes

1. **Preserve os dados**: A remoção não afeta o banco de dados MySQL, então seus dados ficam seguros.

2. **Aguarde entre operações**: Espere alguns segundos entre a remoção e a nova instalação para garantir que todos os serviços foram limpos.

3. **Use instalação rápida**: Para evitar problemas, use o script `quick_install.sh` que tem todas as correções aplicadas.

4. **Monitore os logs**: Durante a nova instalação, monitore os logs para identificar problemas rapidamente.

5. **Backup das configurações**: Se você tinha configurações específicas do Omada Controller, anote-as antes da remoção.

## 📞 Suporte

Se ainda houver problemas após seguir este guia:

1. Execute o script de limpeza completa (`cleanup.sh`)
2. Aguarde 30 segundos
3. Execute a instalação rápida (`quick_install.sh`)
4. Monitore os logs: `sudo tail -f /var/log/voucher-app.log`

Os scripts foram testados e incluem todas as correções necessárias para uma instalação bem-sucedida.