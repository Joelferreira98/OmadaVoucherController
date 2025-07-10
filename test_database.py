#!/usr/bin/env python3
"""
Script para testar conexão com banco de dados MySQL
Diagnóstica problemas de conectividade e configuração
"""

import sys
import socket
import pymysql
from urllib.parse import urlparse

def test_network_connectivity(host, port):
    """Testa conectividade de rede"""
    print(f"🔍 Testando conectividade de rede para {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        
        if result == 0:
            print(f"✅ Conectividade de rede OK para {host}:{port}")
            return True
        else:
            print(f"❌ Não consegue conectar na porta {port} do host {host}")
            print(f"   Código de erro: {result}")
            return False
    except socket.gaierror as e:
        print(f"❌ Erro de resolução DNS para {host}: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro de conectividade: {e}")
        return False

def test_mysql_connection(host, port, user, password, database):
    """Testa conexão MySQL"""
    print(f"🔍 Testando conexão MySQL")
    
    try:
        connection = pymysql.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connect_timeout=10,
            charset='utf8mb4'
        )
        
        # Testar query simples
        cursor = connection.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result and result[0] == 1:
            print(f"✅ Conexão MySQL OK")
            return True
        else:
            print(f"❌ Erro na query de teste")
            return False
            
    except pymysql.Error as e:
        print(f"❌ Erro MySQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False

def test_database_permissions(host, port, user, password, database):
    """Testa permissões do banco"""
    print(f"🔍 Testando permissões do banco")
    
    try:
        connection = pymysql.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connect_timeout=10
        )
        
        cursor = connection.cursor()
        
        # Testar permissão de leitura
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"✅ Permissão de leitura OK - {len(tables)} tabelas encontradas")
        
        # Testar permissão de criação
        try:
            cursor.execute("CREATE TABLE test_permissions (id INT)")
            cursor.execute("DROP TABLE test_permissions")
            print(f"✅ Permissão de criação/exclusão OK")
        except pymysql.Error as e:
            print(f"❌ Sem permissão para criar tabelas: {e}")
            
        cursor.close()
        connection.close()
        return True
        
    except pymysql.Error as e:
        print(f"❌ Erro de permissões: {e}")
        return False

def diagnose_database_url(database_url):
    """Diagnóstica URL do banco"""
    print("🔍 Analisando URL do banco de dados")
    
    try:
        parsed = urlparse(database_url)
        
        print(f"   Protocolo: {parsed.scheme}")
        print(f"   Host: {parsed.hostname}")
        print(f"   Porta: {parsed.port}")
        print(f"   Usuário: {parsed.username}")
        print(f"   Senha: {'*' * len(parsed.password) if parsed.password else 'Não definida'}")
        print(f"   Banco: {parsed.path.lstrip('/')}")
        
        if not parsed.hostname:
            print("❌ Host não definido na URL")
            return False
            
        if not parsed.port:
            print("❌ Porta não definida na URL")
            return False
            
        if not parsed.username:
            print("❌ Usuário não definido na URL")
            return False
            
        if not parsed.password:
            print("❌ Senha não definida na URL")
            return False
            
        if not parsed.path.lstrip('/'):
            print("❌ Nome do banco não definido na URL")
            return False
            
        print("✅ Estrutura da URL válida")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao analisar URL: {e}")
        return False

def main():
    if len(sys.argv) != 6:
        print("Uso: python3 test_database.py <host> <port> <user> <password> <database>")
        print("Exemplo: python3 test_database.py 194.163.133.179 3306 JOEL senha123 omada_voucher_system")
        sys.exit(1)
    
    host = sys.argv[1]
    port = sys.argv[2]
    user = sys.argv[3]
    password = sys.argv[4]
    database = sys.argv[5]
    
    print("🔍 DIAGNÓSTICO DE CONEXÃO COM BANCO DE DADOS")
    print("=" * 50)
    print(f"Host: {host}")
    print(f"Porta: {port}")
    print(f"Usuário: {user}")
    print(f"Banco: {database}")
    print("=" * 50)
    print()
    
    # Testar conectividade de rede
    network_ok = test_network_connectivity(host, port)
    print()
    
    if not network_ok:
        print("❌ FALHA NA CONECTIVIDADE DE REDE")
        print("Possíveis causas:")
        print("   - Firewall bloqueando a porta")
        print("   - Host/porta incorretos")
        print("   - Problema de DNS")
        print("   - Servidor MySQL não está rodando")
        sys.exit(1)
    
    # Testar conexão MySQL
    mysql_ok = test_mysql_connection(host, port, user, password, database)
    print()
    
    if not mysql_ok:
        print("❌ FALHA NA CONEXÃO MYSQL")
        print("Possíveis causas:")
        print("   - Credenciais incorretas")
        print("   - Banco de dados não existe")
        print("   - Usuário não tem permissão para acessar o banco")
        print("   - Configuração do MySQL não permite conexões remotas")
        sys.exit(1)
    
    # Testar permissões
    permissions_ok = test_database_permissions(host, port, user, password, database)
    print()
    
    if not permissions_ok:
        print("❌ FALHA NAS PERMISSÕES")
        print("Possíveis causas:")
        print("   - Usuário não tem permissões suficientes")
        print("   - Banco de dados é somente leitura")
        sys.exit(1)
    
    print("=" * 50)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("✅ Conexão com banco de dados está funcionando corretamente")
    print("=" * 50)
    
    # Testar URL completa
    database_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    print(f"URL do banco: {database_url}")

if __name__ == "__main__":
    main()