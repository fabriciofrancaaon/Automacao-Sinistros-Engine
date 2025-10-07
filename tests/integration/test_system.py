# -*- coding: utf-8 -*-
"""
Teste de integração básico para verificar se o sistema pode ser iniciado.
"""

import pytest
from unittest.mock import patch
import sys
import os

# Adicionar o diretório raiz ao path para importações
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


@pytest.mark.integration
class TestSystemIntegration:
    """Testes de integração do sistema."""
    
    @patch.dict(os.environ, {
        'AON_USERNAME': 'test_user',
        'AON_PASSWORD': 'test_pass',
        'AON_URL': 'https://test.com'
    })
    def test_environment_setup(self):
        """Testa se as variáveis de ambiente estão configuradas."""
        from dotenv import load_dotenv
        load_dotenv()
        
        assert os.getenv('AON_USERNAME') == 'test_user'
        assert os.getenv('AON_PASSWORD') == 'test_pass'
        assert os.getenv('AON_URL') == 'https://test.com'
    
    def test_module_imports(self):
        """Testa se todos os módulos podem ser importados."""
        try:
            from automacao_sinistros.core import main
            from automacao_sinistros.services import email_service
            from automacao_sinistros.utils import helpers
            from automacao_sinistros.monitors import folder_monitor
            assert True  # Se chegou aqui, as importações funcionaram
        except ImportError as e:
            pytest.fail(f"Falha na importação dos módulos: {e}")


if __name__ == '__main__':
    pytest.main([__file__])
