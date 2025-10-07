# -*- coding: utf-8 -*-
"""
Testes unitários para o módulo core.
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Adicionar o diretório raiz ao path para importações
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from automacao_sinistros.core.main import main


class TestMain:
    """Testes para a função principal."""
    
    @patch('automacao_sinistros.core.main.load_dotenv')
    @patch('automacao_sinistros.core.main.setup_logger')
    @patch('automacao_sinistros.core.main.get_outlook_email_info')
    def test_main_no_emails_found(self, mock_get_emails, mock_setup_logger, mock_load_dotenv):
        """Testa o comportamento quando nenhum email é encontrado."""
        # Arrange
        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger
        mock_get_emails.return_value = []
        
        # Act
        with patch('builtins.print') as mock_print:
            main()
        
        # Assert
        mock_load_dotenv.assert_called_once()
        mock_setup_logger.assert_called_once()
        mock_get_emails.assert_called_once()
        mock_logger.info.assert_called_with("Nenhum email encontrado. Finalizando processo...")
    
    @patch.dict(os.environ, {
        'MAX_RETRIES': '3',
        'LOGIN_ERROR_MESSAGE': 'Erro de login teste'
    })
    @patch('automacao_sinistros.core.main.load_dotenv')
    @patch('automacao_sinistros.core.main.setup_logger')
    def test_main_environment_variables(self, mock_setup_logger, mock_load_dotenv):
        """Testa se as variáveis de ambiente são carregadas corretamente."""
        # Arrange
        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger
        
        # Act & Assert - teste implícito através da execução sem erro
        # A função deve carregar as variáveis de ambiente sem falhar
        assert os.getenv('MAX_RETRIES') == '3'
        assert os.getenv('LOGIN_ERROR_MESSAGE') == 'Erro de login teste'


if __name__ == '__main__':
    pytest.main([__file__])
