#!/bin/bash

# Script para corrigir problema do Gunicorn na VPS
# Execute este script na sua VPS se a aplicação não iniciar

set -e

echo "🔧 Corrigindo problema do Gunicorn..."

# Verificar se é root
if [[ $EUID -ne 0 ]]; then
    echo "❌ Execute como root: sudo bash fix_gunicorn.sh"
    exit 1
fi

# Parar aplicação
echo "⏹️  Parando aplicação..."
supervisorctl stop voucher-app || true

# Backup dos arquivos atuais
echo "💾 Fazendo backup..."
cp /opt/voucher-app/main.py /opt/voucher-app/main.py.backup || true

# Criar novo main.py corrigido
echo "🔧 Criando main.py corrigido..."
cat > /opt/voucher-app/main.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up environment for production
if 'gunicorn' in os.environ.get('SERVER_SOFTWARE', ''):
    logger.info("Running under Gunicorn")
else:
    logger.info("Running in development mode")

try:
    # Import the Flask app
    from app import app
    
    # Import routes to register them
    import routes
    
    # Ensure the app is available for Gunicorn
    logger.info("Flask app imported successfully")
    
    # For Gunicorn, we need to expose the app object
    application = app
    
    if __name__ == "__main__":
        logger.info("Starting Flask development server...")
        app.run(host="0.0.0.0", port=5000, debug=True)
        
except Exception as e:
    logger.error(f"Error importing Flask app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

# Definir permissões
chown voucher:voucher /opt/voucher-app/main.py
chmod +x /opt/voucher-app/main.py

# Testar importação
echo "🧪 Testando importação..."
cd /opt/voucher-app

# Criar script de teste
cat > test_gunicorn.py << 'EOF'
#!/usr/bin/env python3
import os
import sys

# Configurar variáveis de ambiente (ajuste conforme necessário)
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'mysql+pymysql://JOEL:@194.163.133.179:3306/omada_voucher_system')
os.environ['SESSION_SECRET'] = os.environ.get('SESSION_SECRET', 'fallback-secret-key')
os.environ['OMADA_CONTROLLER_URL'] = os.environ.get('OMADA_CONTROLLER_URL', 'https://controller.local:8043')
os.environ['OMADA_CLIENT_ID'] = os.environ.get('OMADA_CLIENT_ID', '')
os.environ['OMADA_CLIENT_SECRET'] = os.environ.get('OMADA_CLIENT_SECRET', '')
os.environ['OMADA_OMADAC_ID'] = os.environ.get('OMADA_OMADAC_ID', '')

try:
    print("Testando importação do main.py...")
    import main
    print("✅ main.py importado com sucesso!")
    
    print("Testando se 'app' está disponível...")
    app = getattr(main, 'app', None)
    if app is None:
        app = getattr(main, 'application', None)
    
    if app is not None:
        print("✅ Objeto 'app' encontrado!")
        print(f"   Tipo: {type(app)}")
        print(f"   Nome: {app.name}")
    else:
        print("❌ Objeto 'app' não encontrado!")
        sys.exit(1)
        
    print("✅ Teste completo!")
    
except Exception as e:
    print(f"❌ Erro no teste: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

# Executar teste
if sudo -u voucher ./venv/bin/python test_gunicorn.py; then
    echo "✅ Teste de importação passou!"
else
    echo "❌ Erro no teste de importação!"
    echo "Verificando logs..."
    cat test_gunicorn.py
    exit 1
fi

# Limpar arquivo de teste
rm -f test_gunicorn.py

# Atualizar configuração do supervisor
echo "⚙️  Atualizando configuração do supervisor..."
cat > /etc/supervisor/conf.d/voucher-app.conf << 'EOF'
[program:voucher-app]
command=/opt/voucher-app/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 30 --keep-alive 2 --max-requests 1000 --preload main:app
directory=/opt/voucher-app
user=voucher
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/voucher-app.log
environment=DATABASE_URL="%(ENV_DATABASE_URL)s",SESSION_SECRET="%(ENV_SESSION_SECRET)s",OMADA_CONTROLLER_URL="%(ENV_OMADA_CONTROLLER_URL)s",OMADA_CLIENT_ID="%(ENV_OMADA_CLIENT_ID)s",OMADA_CLIENT_SECRET="%(ENV_OMADA_CLIENT_SECRET)s",OMADA_OMADAC_ID="%(ENV_OMADA_OMADAC_ID)s"
EOF

# Recarregar supervisor
echo "🔄 Recarregando supervisor..."
supervisorctl reread
supervisorctl update

# Iniciar aplicação
echo "🚀 Iniciando aplicação..."
supervisorctl start voucher-app

# Aguardar e verificar
echo "⏱️  Aguardando aplicação iniciar..."
sleep 5

# Verificar status
if supervisorctl status voucher-app | grep -q "RUNNING"; then
    echo "✅ Aplicação iniciada com sucesso!"
    
    # Testar resposta
    echo "🧪 Testando resposta HTTP..."
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 | grep -q "200"; then
        echo "✅ Aplicação responde corretamente na porta 5000!"
    else
        echo "⚠️  Aplicação pode estar ainda iniciando..."
        echo "   Aguarde alguns segundos e teste: curl http://localhost:5000"
    fi
else
    echo "❌ Aplicação não está rodando!"
    echo ""
    echo "--- Status do Supervisor ---"
    supervisorctl status voucher-app
    echo ""
    echo "--- Últimos logs ---"
    tail -20 /var/log/voucher-app.log
    echo ""
    echo "Para debug adicional, execute:"
    echo "  tail -f /var/log/voucher-app.log"
    exit 1
fi

echo ""
echo "========================================="
echo "🎉 CORREÇÃO CONCLUÍDA!"
echo "========================================="
echo ""
echo "✅ main.py foi corrigido para trabalhar com Gunicorn"
echo "✅ Configuração do supervisor atualizada"
echo "✅ Aplicação está rodando"
echo ""
echo "📋 Comandos úteis:"
echo "   Status: supervisorctl status voucher-app"
echo "   Logs: tail -f /var/log/voucher-app.log"
echo "   Reiniciar: supervisorctl restart voucher-app"
echo "   Parar: supervisorctl stop voucher-app"
echo ""
echo "🌐 Teste a aplicação em:"
echo "   http://$(curl -s ifconfig.me 2>/dev/null || echo 'SEU-IP')"
echo ""