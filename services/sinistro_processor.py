# -*- coding: utf-8 -*-
"""
Processador comple            # Inicializar managers
            self.login_manager = AonLoginManager(self.driver, self.logger)
            self.navigation_manager = NavigationManager(self.driver, self.logger)
            self.screenshot_manager = ScreenshotManager()e sinistros com login AON Access.

Este módulo integra todas as funcionalidades para processar um sinistro:
1. Setup do webdriver
2. Login no AON Access  
3. Navegação e inserção de dados
4. Confirmação e salvamento
"""

import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os
import sys
import importlib.util

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.login_service import AonLoginManager
from services.navigation_service import NavigationManager
from utils.screenshot_manager import ScreenshotManager

class SinistroProcessor:
    """Processador completo de sinistros com integração AON Access."""
    
    def __init__(self):
        self.driver = None
        self.login_manager = None
        self.navigation_manager = None
        self.screenshot_manager = None
        self.logger = logging.getLogger(__name__)
    
    def setup_webdriver(self):
        """Configura e inicializa o webdriver."""
        try:
            # Configurações do Chrome
            chrome_options = Options()
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Tentar usar ChromeDriver local primeiro
            try:
                # Inicializar driver com ChromeDriver local
                self.driver = webdriver.Chrome(options=chrome_options)
                self.logger.info("WebDriver configurado com ChromeDriver local")
            except Exception as local_error:
                self.logger.warning(f"ChromeDriver local falhou: {local_error}")
                # Fallback para ChromeDriverManager (online)
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.logger.info("WebDriver configurado com ChromeDriverManager")
            
            # Ocultar indicadores de automação
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Inicializar managers
            self.login_manager = AonLoginManager(self.driver, self.logger)
            self.navigation_manager = NavigationManager(self.driver, self.logger)
            self.screenshot_manager = ScreenshotManager(self.driver, self.logger)
            
            self.logger.info("WebDriver configurado com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar WebDriver: {e}")
            return False
    
    def processar_sinistro_completo(self, email_info):
        """
        Processa completamente um sinistro:
        1. Setup webdriver
        2. Login AON Access
        3. Inserção de dados
        4. Salvamento
        
        Args:
            email_info: Lista com informações do email [numero_sinistro, subject, body, ...]
            
        Returns:
            bool: True se processou com sucesso, False caso contrário
        """
        numero_sinistro = email_info[0] if email_info[0] else None
        subject = email_info[1]
        body = email_info[2] if len(email_info) > 2 else ""
        
        if not numero_sinistro or numero_sinistro == "SEM_NUMERO":
            self.logger.warning(f"❌ Sinistro sem número válido: {subject}")
            return False
        
        try:
            self.logger.info(f"🔄 Iniciando processamento do sinistro: {numero_sinistro}")
            
            # 1. Setup WebDriver
            if not self.setup_webdriver():
                return False
            
            # 2. Login no AON Access
            aon_url = os.getenv('AON_URL', 'https://aonaccess.com')
            username = os.getenv('AON_USERNAME')
            password = os.getenv('AON_PASSWORD')
            
            if not username or not password:
                self.logger.error("❌ Credenciais AON não configuradas no .env")
                return False
            
            self.logger.info(f"🔐 Fazendo login no AON Access...")
            if not self.login_manager.login(aon_url, username, password):
                self.logger.error("❌ Falha no login AON Access")
                return False
            
            # 3. Processar sinistro usando NavigationManager existente
            self.logger.info(f"📝 Processando sinistro: {numero_sinistro}")
            
            # Usar o método principal do NavigationManager com todos os parâmetros
            sucesso = self.navigation_manager.navigate_and_perform_actions(
                subject=subject,
                numero_sinistro=numero_sinistro,
                content_email=body,
                cc_addresses=[],  # Lista vazia para CC
                to_address=email_info[6] if len(email_info) > 6 else "Desconhecido",
                from_address=email_info[6] if len(email_info) > 6 else "Desconhecido"
            )
            
            if sucesso:
                self.logger.info(f"✅ Sinistro {numero_sinistro} processado com sucesso!")
            else:
                self.logger.error(f"❌ Falha no processamento do sinistro {numero_sinistro}")
                
            return sucesso
            
        except Exception as e:
            self.logger.error(f"❌ Erro no processamento do sinistro {numero_sinistro}: {e}")
            # Screenshot do erro
            if self.screenshot_manager and self.driver:
                self.screenshot_manager.take_error_screenshot(f"erro_processamento_{numero_sinistro}")
            return False
            
        finally:
            # Cleanup sempre
            self.cleanup()
    
    def cleanup(self):
        """Limpa recursos utilizados."""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
            self.logger.info("🧹 Recursos limpos com sucesso")
        except Exception as e:
            self.logger.error(f"⚠️ Erro na limpeza: {e}")
