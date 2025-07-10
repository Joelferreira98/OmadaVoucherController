# Correção do Erro CSRF no VPS

## Problema Identificado
O erro `RuntimeError: A secret key is required to use CSRF` acontece porque o arquivo `.env` não existe no servidor VPS ou não tem a chave `SESSION_SECRET`.

## Solução Rápida

### 1. Conecte-se ao VPS via SSH

### 2. Criar o arquivo .env no servidor
```bash
sudo nano /opt/voucher-app/.env
```

### 3. Cole o seguinte conteúdo:
```env
# Database Configuration - MySQL Local
DATABASE_URL=mysql+pymysql://JOEL:admin123@localhost:3306/omada_voucher_system

# Flask Security Configuration
SESSION_SECRET=f7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8

# Omada Controller Configuration
OMADA_CONTROLLER_URL=
OMADA_CLIENT_ID=
OMADA_CLIENT_SECRET=
OMADA_OMADAC_ID=
```

### 4. Salve o arquivo (Ctrl+X, Y, Enter)

### 5. Reinicie o serviço
```bash
sudo systemctl restart voucher-app
```

### 6. Verifique se está funcionando
```bash
sudo systemctl status voucher-app
curl -I http://localhost:5000
```

## Verificação
- O serviço deve estar `active (running)`
- O curl deve retornar `HTTP/1.1 302 FOUND`
- A aplicação deve estar acessível via navegador

## Observações Importantes
1. **Chave SESSION_SECRET**: Gerada automaticamente, não altere
2. **Banco MySQL**: Ajuste usuário/senha conforme sua configuração
3. **Omada Controller**: Configure após a aplicação estar funcionando
4. **Arquivo .env**: Deve estar em `/opt/voucher-app/.env`

## Próximos Passos
Após corrigir o CSRF:
1. Fazer login com `master` / `admin123`
2. Configurar Omada Controller
3. Sincronizar sites
4. Criar administradores e vendedores

## Solução Alternativa
Se o problema persistir, instale o python-dotenv:
```bash
cd /opt/voucher-app
source venv/bin/activate
pip install python-dotenv
sudo systemctl restart voucher-app
```