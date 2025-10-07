# -*- coding: utf-8 -*-
"""
Módulo de autenticação para o sistema Aon Access.

Este módulo contém a classe AonLoginManager que gerencia o processo
de login no sistema Aon Access com tratamento robusto de erros e
fallback para JavaScript quando necessário.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    ElementNotInteractableException,
    NoSuchElementException,
    WebDriverException
)
from time import sleep
import random
import sys
import os
# Adicionar o diretório raiz ao path se necessário
if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.screenshot_manager import ScreenshotManager


class AonLoginConfig:
    """Configuraç[EMOJI]es para o processo de login no Aon Access."""
    
    # Seletores dos elementos
    USER_FIELD_ID = "DefaultHeader_tfUser"
    PASSWORD_FIELD_ID = "DefaultHeader_tfPass" 
    LOGIN_BUTTON_ID = "DefaultHeader_imgBtnLogin"
    DASHBOARD_ID = "dashboard"
    
    # Timeouts (otimizados para MÁXIMA velocidade)
    DEFAULT_TIMEOUT = 2  # Reduzido de 3 para 2
    LONG_TIMEOUT = 5     # Reduzido de 8 para 5
    SHORT_TIMEOUT = 1    # Reduzido de 2 para 1
    
    # Delays (otimizados para MÁXIMA velocidade)
    MIN_DELAY = 0.05     # Reduzido de 0.1 para 0.05
    MAX_DELAY = 0.15     # Reduzido de 0.3 para 0.15
    TYPING_DELAY = 0.01  # Reduzido de 0.02 para 0.01


class AonLoginManager:
    """
    Gerenciador de login para o sistema Aon Access.
    
    Esta classe encapsula toda a lógica de autenticação no sistema,
    incluindo tratamento de erros específicos e fallbacks usando JavaScript.
    """
    
    def __init__(self, driver, logger):
        """
        Inicializa o gerenciador de login.
        
        Args:
            driver: Instância do WebDriver do Selenium
            logger: Logger para registrar as operaç[EMOJI]es
        """
        self.driver = driver
        self.logger = logger
        self.config = AonLoginConfig()
        self.screenshot_manager = ScreenshotManager(driver, logger)
    
    def login(self, url, username, password):
        """
        Executa o processo completo de login com tratamento robusto de erros.
        
        Args:
            url (str): URL do sistema Aon Access
            username (str): Nome de usuário
            password (str): Senha do usuário
            
        Returns:
            bool: True se login foi bem-sucedido, False caso contrário
            
        Raises:
            Exception: Se falha crítica ocorrer durante o login
        """
        try:
            print("[LOGIN] Iniciando processo de login no Aon Access...")
            self.logger.info("=== Iniciando processo de login no Aon Access ===")
            
            # 1. Navegar para a URL
            print("[NAVEGADOR] Navegando para a URL do sistema...")
            if not self._navigate_to_url(url):
                return False
            
            # 2. Preencher campo de usuário
            print("[EMOJI] Preenchendo campo de usuário...")
            if not self._fill_username_field(username):
                return False
            
            # 3. Preencher campo de senha
            print("[CREDENCIAIS] Preenchendo campo de senha...")
            if not self._fill_password_field(password):
                return False
            
            # 4. Clicar no botão de login
            print("[INICIO] Clicando no botão de login...")
            if not self._click_login_button():
                return False
            
            # 5. Verificar sucesso do login
            print("[SUCESSO] Verificando sucesso do login...")
            if not self._verify_login_success():
                return False
            
            print("[CONCLUIDO] Login realizado com sucesso!")
            self.logger.info("=== Login realizado com sucesso ===")
            return True
            
        except Exception as e:
            print(f"[ERRO] Falha crítica durante o login: {e}")
            self.logger.error(f"Falha crítica durante o login: {e}")
            
            # Captura screenshot do erro
            self.screenshot_manager.take_error_screenshot("erro_critico_login")
            
            raise
    
    def _navigate_to_url(self, url):
        """
        Navega para a URL do sistema.
        
        Args:
            url (str): URL de destino
            
        Returns:
            bool: True se navegação foi bem-sucedida
        """
        try:
            self.logger.info(f"Navegando para URL: {url}")
            self.driver.get(url)
            
            # Aguarda página carregar
            WebDriverWait(self.driver, self.config.DEFAULT_TIMEOUT).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            self.logger.info("Página carregada com sucesso")
            self._random_delay()
            return True
            
        except TimeoutException:
            self.logger.error(f"Timeout ao carregar a página: {url}")
            self.screenshot_manager.take_error_screenshot("timeout_carregamento_pagina")
            return False
        except WebDriverException as e:
            self.logger.error(f"Erro do WebDriver ao navegar: {e}")
            self.screenshot_manager.take_error_screenshot("erro_webdriver_navegacao")
            return False
        except Exception as e:
            self.logger.error(f"Erro inesperado ao navegar: {e}")
            return False
    
    def _fill_username_field(self, username):
        """
        Preenche o campo de nome de usuário com fallback para JavaScript.
        
        Args:
            username (str): Nome de usuário
            
        Returns:
            bool: True se preenchimento foi bem-sucedido
        """
        try:
            self.logger.info("Localizando campo de usuário...")
            
            # Tentativa 1: Método padrão do Selenium
            try:
                user_field = WebDriverWait(self.driver, self.config.DEFAULT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.ID, self.config.USER_FIELD_ID))
                )
                
                # Limpa campo antes de preencher
                user_field.clear()
                self._random_delay(0.05, 0.1)  # Reduzido de (0.1, 0.2)
                
                # Preenche com delay entre caracteres para parecer mais humano
                self._type_with_delay(user_field, username)
                
                self.logger.info(f"Campo de usuário preenchido (método padrão): {username}")
                return True
                
            except (TimeoutException, ElementNotInteractableException) as e:
                self.logger.warning(f"Método padrão falhou: {e}. Tentando JavaScript...")
                
                # Captura screenshot do erro antes de tentar fallback
                self.screenshot_manager.take_error_screenshot("falha_preenchimento_usuario_metodo_padrao")
                
                # Tentativa 2: Fallback usando JavaScript
                return self._fill_field_with_javascript(
                    self.config.USER_FIELD_ID, 
                    username, 
                    "campo de usuário"
                )
                
        except Exception as e:
            self.logger.error(f"Erro ao preencher campo de usuário: {e}")
            self.screenshot_manager.take_error_screenshot("erro_critico_preenchimento_usuario")
            return False
    
    def _fill_password_field(self, password):
        """
        Preenche o campo de senha com fallback para JavaScript.
        
        Args:
            password (str): Senha do usuário
            
        Returns:
            bool: True se preenchimento foi bem-sucedido
        """
        try:
            self.logger.info("Localizando campo de senha...")
            
            # Tentativa 1: Método padrão do Selenium
            try:
                password_field = WebDriverWait(self.driver, self.config.DEFAULT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.ID, self.config.PASSWORD_FIELD_ID))
                )
                
                # Limpa campo antes de preencher
                password_field.clear()
                self._random_delay(0.05, 0.1)  # Reduzido de (0.1, 0.2)
                
                # Preenche com delay entre caracteres
                self._type_with_delay(password_field, password)
                
                self.logger.info("Campo de senha preenchido (método padrão)")
                return True
                
            except (TimeoutException, ElementNotInteractableException) as e:
                self.logger.warning(f"Método padrão falhou: {e}. Tentando JavaScript...")
                
                # Captura screenshot do erro antes de tentar fallback
                self.screenshot_manager.take_error_screenshot("falha_preenchimento_senha_metodo_padrao")
                
                # Tentativa 2: Fallback usando JavaScript
                return self._fill_field_with_javascript(
                    self.config.PASSWORD_FIELD_ID, 
                    password, 
                    "campo de senha"
                )
                
        except Exception as e:
            self.logger.error(f"Erro ao preencher campo de senha: {e}")
            self.screenshot_manager.take_error_screenshot("erro_critico_preenchimento_senha")
            return False
    
    def _click_login_button(self):
        """
        Clica no botão de login com fallback para JavaScript.
        
        Returns:
            bool: True se clique foi bem-sucedido
        """
        try:
            self.logger.info("Localizando botão de login...")
            
            # Tentativa 1: Método padrão do Selenium
            try:
                login_button = WebDriverWait(self.driver, self.config.DEFAULT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.ID, self.config.LOGIN_BUTTON_ID))
                )
                
                self._random_delay()
                login_button.click()
                
                self.logger.info("Botão de login clicado (método padrão)")
                return True
                
            except (TimeoutException, ElementNotInteractableException) as e:
                self.logger.warning(f"Método padrão falhou: {e}. Tentando JavaScript...")
                
                # Captura screenshot do erro antes de tentar fallback
                self.screenshot_manager.take_error_screenshot("falha_clique_botao_login_metodo_padrao")
                
                # Tentativa 2: Fallback usando JavaScript
                return self._click_element_with_javascript(
                    self.config.LOGIN_BUTTON_ID,
                    "botão de login"
                )
                
        except Exception as e:
            self.logger.error(f"Erro ao clicar no botão de login: {e}")
            self.screenshot_manager.take_error_screenshot("erro_critico_clique_botao_login")
            return False
    
    def _verify_login_success(self):
        """
        Verifica se o login foi bem-sucedido com verificação ULTRA RÁPIDA.
        
        Returns:
            bool: True se login foi bem-sucedido
        """
        try:
            self.logger.info("Verificação ultra rápida de login...")
            
            # Verificação instantânea de erro
            if self._check_login_error_instant():
                return False
            
            # Verificação ultra rápida de sucesso
            return self._verify_success_instant()
            
        except Exception as e:
            if "Login ou senha incorretos" in str(e):
                raise e
            self.logger.error(f"Erro na verificação: {e}")
            return False
    
    def _check_login_error_instant(self):
        """
        Verificação instantânea de erros - sem waits.
        
        Returns:
            bool: True se erro foi detectado
        """
        try:
            # Verifica apenas elementos já presentes na página
            error_elements = self.driver.find_elements(By.ID, "ext-gen119")
            if error_elements and error_elements[0].is_displayed():
                error_text = error_elements[0].text
                if "incorreto" in error_text.lower() or "login" in error_text.lower():
                    self.logger.error(f"Erro de login: {error_text}")
                    print(f"[ERRO] Login incorreto: {error_text}")
                    raise Exception("Login ou senha incorretos.")
            return False
        except Exception as e:
            if "Login ou senha incorretos" in str(e):
                raise e
            return False
    
    def _verify_success_instant(self):
        """
        Verificação EXTREMAMENTE rápida - timeout máximo de 0.5s total.
        
        Returns:
            bool: True se sucesso confirmado
        """
        print("[SUCESSO] Verificação ultra rápida de login...")
        
        # Estratégia 1: Verificação direta (0.3s apenas)
        try:
            WebDriverWait(self.driver, 0.3).until(
                EC.presence_of_element_located((By.ID, "Repeater1_IShortCutModule2_0"))
            )
            print("[SUCESSO] Menu encontrado - Login OK!")
            return True
        except TimeoutException:
            pass
        
        # Estratégia 2: Menu alternativo (0.2s apenas)
        try:
            WebDriverWait(self.driver, 0.2).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@id, 'ShortCutModule')]"))
            )
            print("[SUCESSO] Menu alternativo encontrado - Login OK!")
            return True
        except TimeoutException:
            pass
        
        # Estratégia 3: Verificação instantânea de URL
        current_url = self.driver.current_url.lower()
        if any(word in current_url for word in ['main', 'dashboard', 'home']):
            print("[SUCESSO] URL indica sucesso - Login OK!")
            return True
        
        # Verificação instantânea de título
        try:
            page_title = self.driver.title.lower()
            if page_title and 'login' not in page_title:
                print("[SUCESSO] Título indica sucesso - Login OK!")
                return True
        except:
            pass
        
        # Se chegou aqui, provavelmente falhou
        print("[ERRO] Verificação ultra rápida: Login falhou")
        return False
    
    def _fill_field_with_javascript(self, field_id, value, field_name):
        """
        Preenche um campo usando JavaScript como fallback.
        
        Args:
            field_id (str): ID do elemento
            value (str): Valor a ser preenchido
            field_name (str): Nome do campo para logs
            
        Returns:
            bool: True se preenchimento foi bem-sucedido
        """
        try:
            # Verifica se elemento existe
            script_check = f"return document.getElementById('{field_id}') !== null;"
            if not self.driver.execute_script(script_check):
                self.logger.error(f"Elemento {field_name} não encontrado via JavaScript")
                return False
            
            # Preenche o campo
            script_fill = f"""
                var element = document.getElementById('{field_id}');
                element.value = '{value}';
                element.dispatchEvent(new Event('input', {{bubbles: true}}));
                element.dispatchEvent(new Event('change', {{bubbles: true}}));
                return true;
            """
            
            result = self.driver.execute_script(script_fill)
            if result:
                self.logger.info(f"{field_name} preenchido via JavaScript")
                return True
            else:
                self.logger.error(f"Falha ao preencher {field_name} via JavaScript")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro no JavaScript para {field_name}: {e}")
            return False
    
    def _click_element_with_javascript(self, element_id, element_name):
        """
        Clica em um elemento usando JavaScript como fallback.
        
        Args:
            element_id (str): ID do elemento
            element_name (str): Nome do elemento para logs
            
        Returns:
            bool: True se clique foi bem-sucedido
        """
        try:
            script = f"""
                var element = document.getElementById('{element_id}');
                if (element) {{
                    element.click();
                    return true;
                }} else {{
                    return false;
                }}
            """
            
            result = self.driver.execute_script(script)
            if result:
                self.logger.info(f"{element_name} clicado via JavaScript")
                return True
            else:
                self.logger.error(f"Elemento {element_name} não encontrado via JavaScript")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro no JavaScript para {element_name}: {e}")
            return False
    
    def _type_with_delay(self, element, text):
        """
        Digita texto com delay entre caracteres para simular digitação humana.
        
        Args:
            element: Elemento web onde digitar
            text (str): Texto a ser digitado
        """
        for char in text:
            element.send_keys(char)
            sleep(self.config.TYPING_DELAY + random.uniform(0, 0.01))
    
    def _random_delay(self, min_delay=None, max_delay=None):
        """
        Aplica delay aleatório para simular comportamento humano.
        
        Args:
            min_delay (float, optional): Delay mínimo em segundos
            max_delay (float, optional): Delay máximo em segundos
        """
        min_d = min_delay or self.config.MIN_DELAY
        max_d = max_delay or self.config.MAX_DELAY
        delay = random.uniform(min_d, max_d)
        sleep(delay)


# --- Função de compatibilidade para manter API existente ---
def login(driver, url, username, password, logger):
    """
    Função de compatibilidade que mantém a API original.
    
    Args:
        driver: Instância do WebDriver do Selenium
        url (str): URL do sistema Aon Access
        username (str): Nome de usuário
        password (str): Senha do usuário
        logger: Logger para registrar as operaç[EMOJI]es
        
    Returns:
        bool: True se login foi bem-sucedido
        
    Raises:
        Exception: Se falha crítica ocorrer durante o login
    """
    login_manager = AonLoginManager(driver, logger)
    success = login_manager.login(url, username, password)
    
    if not success:
        raise Exception("Falha no processo de login")
    
    return success


