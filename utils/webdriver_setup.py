# -*- coding: utf-8 -*-
"""
WebDriver Setup Module

Este módulo fornece funcionalidades para configuração e inicialização
do WebDriver do Selenium com opções otimizadas para automação web.

Funcionalidades principais:
- Configuração do Chrome WebDriver
- Opções de desempenho e segurança
- Modo headless opcional
- Configurações para diferentes ambientes
"""

import logging
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException


class WebDriverConfig:
    """Configurações para o WebDriver."""
    
    # Opções padrão do Chrome
    DEFAULT_CHROME_OPTIONS = [
        "--disable-gpu",
        "--no-sandbox", 
        "--disable-dev-shm-usage",
        "--disable-extensions",
        "--disable-plugins",
        "--disable-images",
        "--disable-javascript-harmony-shipping",
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-backgrounding-occluded-windows",
        "--disable-ipc-flooding-protection",
        "--window-size=1920,1080"
    ]
    
    # Opções para modo headless
    HEADLESS_OPTIONS = [
        "--headless=new"
    ]
    
    # Opções para modo debug (com interface gráfica)
    DEBUG_OPTIONS = [
        "--start-maximized"
    ]


class WebDriverSetupError(Exception):
    """Exceção customizada para erros de configuração do WebDriver."""
    pass


def setup_webdriver(headless: bool = False, debug: bool = False, 
                   chrome_driver_path: Optional[str] = None) -> webdriver.Chrome:
    """
    Configura e inicializa o WebDriver Chrome com opções otimizadas.
    
    Args:
        headless (bool): Se True, executa em modo headless (sem interface gráfica)
        debug (bool): Se True, adiciona opções de debug e maximiza janela
        chrome_driver_path (Optional[str]): Caminho para o executável do ChromeDriver
        
    Returns:
        webdriver.Chrome: Instância configurada do WebDriver
        
    Raises:
        WebDriverSetupError: Se falhar ao inicializar o WebDriver
    """
    try:
        logging.info("Iniciando configuração do WebDriver...")
        
        # Cria opções do Chrome
        chrome_options = _create_chrome_options(headless, debug)
        
        # Configura serviço se caminho específico for fornecido
        service = None
        if chrome_driver_path:
            service = Service(chrome_driver_path)
            logging.info(f"Usando ChromeDriver em: {chrome_driver_path}")
        
        # Inicializa WebDriver
        logging.info("Iniciando navegador Chrome...")
        
        if service:
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
        
        # Configura timeouts
        _configure_timeouts(driver)
        
        logging.info("WebDriver configurado com sucesso")
        
        if debug:
            logging.info("Modo debug ativado - janela maximizada")
        if headless:
            logging.info("Modo headless ativado - execução sem interface gráfica")
            
        return driver
        
    except WebDriverException as e:
        error_msg = f"Erro ao inicializar WebDriver: {e}"
        logging.error(error_msg)
        raise WebDriverSetupError(error_msg) from e
    except Exception as e:
        error_msg = f"Erro inesperado na configuração do WebDriver: {e}"
        logging.error(error_msg)
        raise WebDriverSetupError(error_msg) from e


def _create_chrome_options(headless: bool, debug: bool) -> Options:
    """
    Cria e configura as opções do Chrome.
    
    Args:
        headless (bool): Se deve executar em modo headless
        debug (bool): Se deve adicionar opções de debug
        
    Returns:
        Options: Objeto com as opções configuradas
    """
    chrome_options = Options()
    
    # Adiciona opções padrão
    for option in WebDriverConfig.DEFAULT_CHROME_OPTIONS:
        chrome_options.add_argument(option)
    
    # Adiciona opções específicas do modo
    if headless:
        for option in WebDriverConfig.HEADLESS_OPTIONS:
            chrome_options.add_argument(option)
    elif debug:
        for option in WebDriverConfig.DEBUG_OPTIONS:
            chrome_options.add_argument(option)
    
    # Configurações adicionais de preferências
    prefs = {
        "profile.default_content_setting_values": {
            "notifications": 2,  # Bloqueia notificações
            "geolocation": 2,    # Bloqueia geolocalização
        },
        "profile.managed_default_content_settings": {
            "images": 2  # Bloqueia imagens para melhor performance
        }
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Desabilita logs desnecessários
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    return chrome_options


def _configure_timeouts(driver: webdriver.Chrome) -> None:
    """
    Configura os timeouts padrão do WebDriver.
    
    Args:
        driver (webdriver.Chrome): Instância do WebDriver
    """
    # Timeout implícito para encontrar elementos
    driver.implicitly_wait(10)
    
    # Timeout para carregamento de página
    driver.set_page_load_timeout(30)
    
    # Timeout para execução de scripts
    driver.set_script_timeout(30)


def cleanup_webdriver(driver: Optional[webdriver.Chrome]) -> None:
    """
    Limpa e encerra o WebDriver de forma segura.
    
    Args:
        driver (Optional[webdriver.Chrome]): Instância do WebDriver para encerrar
    """
    if driver:
        try:
            logging.info("Encerrando WebDriver...")
            driver.quit()
            logging.info("WebDriver encerrado com sucesso")
        except Exception as e:
            logging.warning(f"Erro ao encerrar WebDriver: {e}")


def get_webdriver_info(driver: webdriver.Chrome) -> dict:
    """
    Obtém informações sobre o WebDriver em execução.
    
    Args:
        driver (webdriver.Chrome): Instância do WebDriver
        
    Returns:
        dict: Informações sobre o WebDriver
    """
    try:
        capabilities = driver.capabilities
        return {
            "browser_name": capabilities.get("browserName"),
            "browser_version": capabilities.get("browserVersion"),
            "platform": capabilities.get("platformName"),
            "session_id": driver.session_id,
            "current_url": driver.current_url
        }
    except Exception as e:
        logging.warning(f"Erro ao obter informações do WebDriver: {e}")
        return {}


# Função de compatibilidade para manter API existente
def setup_driver(headless: bool = False) -> webdriver.Chrome:
    """
    Função de compatibilidade que mantém a API original.
    
    Args:
        headless (bool): Se deve executar em modo headless
        
    Returns:
        webdriver.Chrome: Instância configurada do WebDriver
    """
    return setup_webdriver(headless=headless)
