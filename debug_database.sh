#!/bin/bash

# Script para diagnosticar problemas de conexão com banco de dados
# Testa conectividade, credenciais e permissões

echo "🔍 DIAGNÓSTICO DE CONEXÃO COM BANCO DE DADOS"
echo "============================================"

# Função para input
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

# Coletar informações do banco
echo "📋 Digite as informações do banco de dados:"
echo ""

DB_HOST=$(read_input "Host do MySQL" "194.163.133.179")
DB_PORT=$(read_input "Porta do MySQL" "3306")
DB_NAME=$(read_input "Nome do banco de dados" "omada_voucher_system")
DB_USER=$(read_input "Usuário do MySQL" "JOEL")
DB_PASSWORD=$(read_password "Senha do MySQL")

echo ""
echo "🔍 Testando conexão com:"
echo "   Host: $DB_HOST"
echo "   Porta: $DB_PORT"
echo "   Banco: $DB_NAME"
echo "   Usuário: $DB_USER"
echo ""

# Teste 1: Conectividade de rede
echo "🔍 TESTE 1: Conectividade de rede"
echo "================================="

if command -v nc >/dev/null 2>&1; then
    if nc -z -v -w5 "$DB_HOST" "$DB_PORT" 2>/dev/null; then
        echo "✅ Conectividade de rede OK"
        NETWORK_OK=true
    else
        echo "❌ Não consegue conectar na porta $DB_PORT do host $DB_HOST"
        NETWORK_OK=false
    fi
else
    # Fallback usando telnet
    if timeout 5 bash -c "echo >/dev/tcp/$DB_HOST/$DB_PORT" 2>/dev/null; then
        echo "✅ Conectividade de rede OK"
        NETWORK_OK=true
    else
        echo "❌ Não consegue conectar na porta $DB_PORT do host $DB_HOST"
        NETWORK_OK=false
    fi
fi

echo ""

# Teste 2: Resolução DNS
echo "🔍 TESTE 2: Resolução DNS"
echo "========================="

if nslookup "$DB_HOST" >/dev/null 2>&1; then
    echo "✅ Resolução DNS OK"
    IP_ADDRESS=$(nslookup "$DB_HOST" | grep -A1 "Name:" | grep "Address:" | awk '{print $2}' | head -1)
    if [ -n "$IP_ADDRESS" ]; then
        echo "   IP resolvido: $IP_ADDRESS"
    fi
else
    echo "❌ Erro na resolução DNS para $DB_HOST"
fi

echo ""

# Teste 3: Ping
echo "🔍 TESTE 3: Ping"
echo "================"

if ping -c 1 -W 5 "$DB_HOST" >/dev/null 2>&1; then
    echo "✅ Ping OK"
else
    echo "❌ Host não responde ao ping (pode estar bloqueado)"
fi

echo ""

# Teste 4: MySQL Client
echo "🔍 TESTE 4: Cliente MySQL"
echo "========================="

if command -v mysql >/dev/null 2>&1; then
    echo "✅ Cliente MySQL instalado"
    
    # Testar conexão
    echo "🔍 Testando conexão MySQL..."
    
    if mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1 as test;" "$DB_NAME" 2>/dev/null; then
        echo "✅ Conexão MySQL OK"
        MYSQL_OK=true
    else
        echo "❌ Falha na conexão MySQL"
        echo "🔍 Tentando conexão com mais detalhes..."
        
        # Tentar com output de erro
        mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1;" "$DB_NAME" 2>&1 | head -5
        MYSQL_OK=false
    fi
else
    echo "❌ Cliente MySQL não instalado"
    echo "   Instalando cliente MySQL..."
    
    if command -v apt >/dev/null 2>&1; then
        apt update >/dev/null 2>&1
        apt install -y mysql-client >/dev/null 2>&1
        echo "✅ Cliente MySQL instalado"
    elif command -v yum >/dev/null 2>&1; then
        yum install -y mysql >/dev/null 2>&1
        echo "✅ Cliente MySQL instalado"
    else
        echo "❌ Não foi possível instalar cliente MySQL automaticamente"
    fi
fi

echo ""

# Teste 5: PyMySQL
echo "🔍 TESTE 5: PyMySQL (Python)"
echo "============================"

if command -v python3 >/dev/null 2>&1; then
    echo "✅ Python3 instalado"
    
    # Instalar PyMySQL se necessário
    if python3 -c "import pymysql" 2>/dev/null; then
        echo "✅ PyMySQL instalado"
    else
        echo "⚠️  PyMySQL não instalado, instalando..."
        pip3 install pymysql >/dev/null 2>&1
        
        if python3 -c "import pymysql" 2>/dev/null; then
            echo "✅ PyMySQL instalado com sucesso"
        else
            echo "❌ Falha ao instalar PyMySQL"
        fi
    fi
    
    # Testar conexão Python
    echo "🔍 Testando conexão Python..."
    
    DATABASE_URL="mysql+pymysql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
    
    python3 - <<EOF
import pymysql
import sys

try:
    connection = pymysql.connect(
        host='$DB_HOST',
        port=int('$DB_PORT'),
        user='$DB_USER',
        password='$DB_PASSWORD',
        database='$DB_NAME',
        connect_timeout=10
    )
    
    cursor = connection.cursor()
    cursor.execute("SELECT 1 as test")
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    
    if result and result[0] == 1:
        print("✅ Conexão Python OK")
    else:
        print("❌ Erro na query de teste")
        
except Exception as e:
    print(f"❌ Erro Python: {e}")
    sys.exit(1)
EOF

else
    echo "❌ Python3 não instalado"
fi

echo ""

# Resumo dos testes
echo "📊 RESUMO DOS TESTES"
echo "==================="

if [ "$NETWORK_OK" = true ]; then
    echo "✅ Conectividade de rede: OK"
else
    echo "❌ Conectividade de rede: FALHA"
fi

if [ "$MYSQL_OK" = true ]; then
    echo "✅ Conexão MySQL: OK"
else
    echo "❌ Conexão MySQL: FALHA"
fi

echo ""

# Diagnóstico de problemas
if [ "$NETWORK_OK" != true ]; then
    echo "🔧 PROBLEMAS DE CONECTIVIDADE DETECTADOS"
    echo "======================================="
    echo ""
    echo "Possíveis causas:"
    echo "   1. Firewall bloqueando a porta $DB_PORT"
    echo "   2. Host/porta incorretos"
    echo "   3. Servidor MySQL não está rodando"
    echo "   4. Problema de rede/internet"
    echo ""
    echo "Soluções:"
    echo "   1. Verifique se o servidor MySQL está rodando"
    echo "   2. Verifique se a porta $DB_PORT está aberta"
    echo "   3. Teste com telnet: telnet $DB_HOST $DB_PORT"
    echo "   4. Verifique configurações de firewall"
    echo ""
elif [ "$MYSQL_OK" != true ]; then
    echo "🔧 PROBLEMAS DE AUTENTICAÇÃO DETECTADOS"
    echo "======================================="
    echo ""
    echo "Possíveis causas:"
    echo "   1. Credenciais incorretas"
    echo "   2. Banco de dados '$DB_NAME' não existe"
    echo "   3. Usuário '$DB_USER' não tem permissão"
    echo "   4. MySQL não permite conexões remotas"
    echo ""
    echo "Soluções:"
    echo "   1. Verifique usuário e senha"
    echo "   2. Crie o banco: CREATE DATABASE $DB_NAME;"
    echo "   3. Dê permissões: GRANT ALL ON $DB_NAME.* TO '$DB_USER'@'%';"
    echo "   4. Configure MySQL para aceitar conexões remotas"
    echo ""
else
    echo "🎉 TODOS OS TESTES PASSARAM!"
    echo "=========================="
    echo ""
    echo "✅ Conexão com banco de dados está funcionando"
    echo "✅ URL do banco: $DATABASE_URL"
    echo ""
    echo "Pode prosseguir com a instalação da aplicação."
fi

echo ""
echo "💡 Para mais ajuda, execute:"
echo "   python3 test_database.py $DB_HOST $DB_PORT $DB_USER [senha] $DB_NAME"
echo ""