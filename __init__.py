# -*- coding: utf-8 -*-
"""
Automacao Sinistros - Sistema de automação para processamento de sinistros AON.

Este pacote contém as funcionalidades principais para:
- Monitoramento de pastas de rede
- Processamento automatizado de emails
- Navegação e interação com sistemas web
- Geração de relatórios e logs
"""

__version__ = "1.0.0"
__author__ = "AON Innovation Lab"
__email__ = "innovation.lab@aon.com"

from .core.main import main
# Importações diretas das funções principais
from .services.email_service import get_outlook_email_info, send_claim_email, send_summary_email
from .services.login_service import AonLoginManager
from .services.navigation_service import NavigationManager

__all__ = [
    "main",
    "get_outlook_email_info",
    "send_claim_email", 
    "send_summary_email",
    "AonLoginManager",
    "NavigationManager"
]
