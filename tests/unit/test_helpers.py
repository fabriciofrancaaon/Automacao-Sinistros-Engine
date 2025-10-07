# -*- coding: utf-8 -*-
"""
Testes unitários para o módulo de utilitários.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import sys
import os

# Adicionar o diretório raiz ao path para importações
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from automacao_sinistros.utils.helpers import setup_logger, log_and_print


class TestHelpers:
    """Testes para funções utilitárias."""
    
    def test_setup_logger(self):
        """Testa a configuração do logger."""
        # Act
        logger = setup_logger()
        
        # Assert
        assert logger is not None
        assert logger.name == "automacao_sinistros"
    
    @patch('builtins.print')
    def test_log_and_print_info(self, mock_print):
        """Testa log_and_print com nível info."""
        # Arrange
        mock_logger = Mock()
        message = "Teste de mensagem"
        
        # Act
        log_and_print(message, mock_logger)
        
        # Assert
        mock_logger.info.assert_called_once_with(message)
        mock_print.assert_called_once_with(message)
    
    @patch('builtins.print')
    def test_log_and_print_error(self, mock_print):
        """Testa log_and_print com nível error."""
        # Arrange
        mock_logger = Mock()
        message = "Teste de erro"
        
        # Act
        log_and_print(message, mock_logger, level="error")
        
        # Assert
        mock_logger.error.assert_called_once_with(message)
        mock_print.assert_called_once_with(message)


if __name__ == '__main__':
    pytest.main([__file__])
