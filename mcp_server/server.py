"""
Atalho para rodar o servidor MCP a partir do repositório clonado, sem instalar:

    python mcp_server/server.py

(A lógica vive no pacote saudeemdado_mcp, para também ser publicável no PyPI e
instalável com `uvx saudeemdado-mcp`.)
"""
from saudeemdado_mcp import main

if __name__ == "__main__":
    main()
