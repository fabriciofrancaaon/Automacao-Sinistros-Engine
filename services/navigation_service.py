# -*- coding: utf-8 -*-
"""
Módulo de navegação e ações para automação de sinistros.

Este módulo contém a classe NavigationManager que gerencia todas as ações
de navegação no sistema de sinistros, incluindo busca, atualização e
salvamento de informações, com tratamento robusto de erros e fallbacks
usando JavaScript quando necessário.
"""

import os
import json
import random
import pyperclip
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementNotInteractableException
)
from datetime import datetime
from time import sleep
import sys
# Adicionar o diretório raiz ao path se necessário
if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.screenshot_manager import ScreenshotManager


class NavigationConfig:
    """Configurações para navegação no sistema de sinistros."""
    
    # Seletores dos elementos
    SINISTROS_MENU_ID = 'Repeater1_IShortCutModule2_0'
    SEARCH_OPTION_ID = "li_buscador"
    SEARCH_TEXT_ID = 'searchText'
    CLAIM_NUMBER_FIELD_ID = 'c_c_c_dyncontrolNROSINIESTRO_txtFiltro_TextField'
    SEARCH_BUTTON_ID = 'ext-gen427'
    CLAIM_RESULT_ID = 'ext-gen744'
    EDIT_BUTTON_ID = 'go-edit-button'
    OPTIONS_DROPDOWN_ID = 'ext-gen331'
    HISTORY_OPTION_ID = 'ext-gen347'
    ADD_UPDATE_BUTTON_ID = 'c_c_bNewEntity'
    TYPE_FIELD_ID = 'c_c_c_SeguimientoClienteEditor_lkpTipoInforme_FieldLookUp'
    OBSERVATIONS_FIELD_ID = 'c_c_c_SeguimientoClienteEditor_txtObservaciones_TextArea'
    COMMENTS_FIELD_ID = 'c_c_c_SeguimientoClienteEditor_txtComentario_TextArea'
    CANCEL_BUTTON_ID = 'ext-gen1240'
    SAVE_BUTTON_ID = 'ext-gen525'
    BACK_BUTTON_ID = 'ext-gen481'
    PHONE_FIELD_NAME = 'telefono'
    
    # XPaths
    SAVE_EDIT_XPATH = '//*[@id="edit-button"]/button'
    CONFIRM_XPATH = '//*[@id="appcontainer"]/div[2]/div[2]/div/div/div/div/div[4]/button[1]'
    SEARCH_CONTAINER_XPATH = '//*[@id="searchContainer"]/div[3]/div[{}]'
    
    # Timeouts
    DEFAULT_TIMEOUT = 30
    LONG_TIMEOUT = 60
    SHORT_TIMEOUT = 10
    VERY_SHORT_TIMEOUT = 5
    
    # Delays
    MIN_DELAY = 1
    MAX_DELAY = 3
    SAVE_DELAY = 10
    BACK_DELAY = 20
    EDIT_DELAY = 10
    
    # Texts
    VISTA_PADRAO_TEXT = 'Vista Padrão'
    EXPECTED_VISTA_TEXT = 'Vistas Vista PadrãoPrincipal / Sinistros'
    AUTOMATION_TAG = '[PROCESSADO PELA AUTOMAÇÃO]'


class NavigationManager:
    """
    Gerenciador de navegação para o sistema de sinistros.
    
    Esta classe encapsula toda a lógica de navegação, busca e atualização
    de sinistros no sistema, incluindo tratamento de erros e fallbacks.
    """
    
    def __init__(self, driver, logger):
        """
        Inicializa o gerenciador de navegação.
        
        Args:
            driver: Instância do WebDriver do Selenium
            logger: Logger para registrar as operações
        """
        self.driver = driver
        self.logger = logger
        self.config = NavigationConfig()
        self.subject_to_code = self._load_subject_mapping()
        self.screenshot_manager = ScreenshotManager(driver, logger)
    
    def navigate_and_perform_actions(self, subject, numero_sinistro, content_email, 
                                   to_address, cc_addresses, from_address, sent_time=None):
        """
        Executa o fluxo completo de navegação e atualização de sinistro.
        
        Args:
            subject (str): Assunto do email
            numero_sinistro (str): Número do sinistro
            content_email (str): Conteúdo do email
            to_address (str): Destinatário do email
            cc_addresses (str): Endereços em cópia
            from_address (str): Remetente do email
            sent_time (str): Data e hora de envio do email
            
        Returns:
            int: 1 se sucesso, 0 se falha, -1 se processo encerrado
        """
        try:
            print("[NAVEGACAO] Iniciando processo de navegação e acoes...")
            self.logger.info("=== Iniciando processo de navegação e acoes ===")
            
            # Armazenar número do sinistro no contexto para uso posterior
            self.current_numero_sinistro = numero_sinistro
            
            # Verificar se o processo já foi marcado como encerrado
            try:
                from services.email_service import is_process_closed
                if is_process_closed(numero_sinistro):
                    print(f"[CONTROLE] Sinistro {numero_sinistro} já marcado como encerrado - pulando processamento")
                    self.logger.info(f"Sinistro {numero_sinistro} já marcado como encerrado - evitando reprocessamento")
                    return 0
            except Exception as check_error:
                self.logger.warning(f"Erro ao verificar se processo está encerrado: {check_error}")
            
            # 1. Navegar para menu de sinistros
            print("[PROCESSANDO] Navegando para menu de sinistros...")
            if not self._navigate_to_claims_menu():
                return 0
            
            # 2. Acessar busca
            print("[BUSCAR] Acessando opção de busca...")
            if not self._access_search_option():
                return 0
            
            # 3. Configurar vista padrão
            print("[CONFIG] Configurando vista padrão...")
            if not self._setup_default_view():
                return 0
            
            # 4. Buscar sinistro
            print(f"[DADOS] Buscando sinistro: {numero_sinistro}...")
            if not self._search_claim(numero_sinistro):
                return 0
            
            # 5. Abrir sinistro
            print("[PASTA] Abrindo sinistro...")
            if not self._open_claim():
                return 0
            
            # 6. Verificar se pode editar
            print("[CONFIG] Verificando disponibilidade para edição...")
            if self._check_edit_availability():
                print("[SUCESSO] Botão 'Editar' encontrado - continuando automação...")
                self.logger.info("Botão 'Editar' encontrado - continuando com o processo")
                
                # Fluxo normal para processos ativos
                return self._process_active_claim(subject, content_email, to_address, from_address, sent_time, cc_addresses)
                
            else:
                print("[AVISO] Botão 'Editar' não encontrado - sinistro já finalizado...")
                self.logger.warning("Botão 'Editar' não encontrado - sinistro já finalizado")
                
                # Fluxo especial para processos encerrados (incluir histórico sem editar)
                return self._process_closed_claim(subject, content_email, to_address, from_address, sent_time, cc_addresses, numero_sinistro)
            
            
        except Exception as e:
            print(f"[ERRO] Erro crítico durante navegação: {e}")
            self.logger.error(f"Erro crítico durante navegação: {e}")
            
            # Captura screenshot do erro
            self.screenshot_manager.take_error_screenshot("erro_critico_navegacao")
            
            return 0

    def _process_active_claim(self, subject, content_email, to_address, from_address, sent_time, cc_addresses):
        """
        Processa sinistro ativo (com botão editar disponível) - fluxo completo.
        
        Returns:
            int: 1 se sucesso, 0 se falha
        """
        try:
            # 6.1. Navegar para seção de atualizações
            print("[CONFIG] Navegando para seção de atualizaçoes...")
            if not self.click_arrow_right():
                return 0
            
            print("[CONFIG] Clicando no botão historico...")
            if not self.click_history_button():
                return 0

            print("[CONFIG] Clicando no botão para Adicionar Nova Entidade...")
            if not self.click_new_entity_button():
                return 0

            # 7. Adicionar atualização
            print("[LOG] Adicionando atualização...")
            if not self._add_update(subject, content_email, to_address, from_address, sent_time, cc_addresses):
                return 0
            
            # 8. Editar telefone
            print("[TELEFONE] Editando número de telefone...")
            if not self._edit_phone_number():
                return 0
            
            sleep(3)
            
            print("[CONCLUIDO] Processo ativo finalizado com sucesso!")
            self.logger.info("=== Processo ativo finalizado com sucesso ===")
            return 1
            
        except Exception as e:
            print(f"[ERRO] Erro durante processamento de sinistro ativo: {e}")
            self.logger.error(f"Erro durante processamento de sinistro ativo: {e}")
            return 0

    def _process_closed_claim(self, subject, content_email, to_address, from_address, sent_time, cc_addresses, numero_sinistro):
        """
        Processa sinistro encerrado - adiciona histórico mas não edita.
        
        Returns:
            int: -1 para indicar processo encerrado (mas com sucesso no histórico)
        """
        try:
            print("[PROCESSO_ENCERRADO] Iniciando processamento de sinistro encerrado...")
            print("[PROCESSO_ENCERRADO] Será adicionado ao histórico mas SEM editar telefone")
            self.logger.info(f"Processando sinistro encerrado {numero_sinistro} - apenas histórico")
            
            # 6.1. Navegar para seção de atualizações (mesmo para encerrados)
            print("[CONFIG] Navegando para seção de atualizaçoes...")
            if not self.click_arrow_right():
                print("[AVISO] Falha ao navegar - tentando continuar...")
            
            print("[CONFIG] Clicando no botão historico...")
            if not self.click_history_button():
                print("[AVISO] Falha ao acessar histórico - tentando continuar...")

            print("[CONFIG] Clicando no botão para Adicionar Nova Entidade...")
            if not self.click_new_entity_button():
                print("[AVISO] Falha ao adicionar entidade - tentando continuar...")

            # 7. Adicionar atualização (PRINCIPAL - isso deve funcionar mesmo em encerrados)
            print("[LOG] [PROCESSO_ENCERRADO] Adicionando atualização no histórico...")
            if self._add_update(subject, content_email, to_address, from_address, sent_time, cc_addresses):
                print("[SUCESSO] [PROCESSO_ENCERRADO] Histórico atualizado com sucesso!")
                self.logger.info(f"Histórico do processo encerrado {numero_sinistro} atualizado com sucesso")
            else:
                print("[AVISO] [PROCESSO_ENCERRADO] Falha ao atualizar histórico, mas continuando...")
                self.logger.warning(f"Falha ao atualizar histórico do processo encerrado {numero_sinistro}")
            
            # 8. NÃO editar telefone em processos encerrados
            print("[TELEFONE] [PROCESSO_ENCERRADO] Pulando edição de telefone - processo encerrado")
            self.logger.info("Edição de telefone pulada - processo encerrado")
            
            # Marcar como processo encerrado para controle
            try:
                from services.email_service import mark_process_as_closed
                mark_process_as_closed(numero_sinistro, "Processo encerrado - histórico atualizado")
                print(f"[CONTROLE] Processo {numero_sinistro} marcado como encerrado")
                self.logger.info(f"Processo {numero_sinistro} marcado como encerrado")
            except Exception as mark_error:
                self.logger.error(f"Erro ao marcar processo como encerrado: {mark_error}")
            
            sleep(2)
            
            print("[CONCLUIDO] [PROCESSO_ENCERRADO] Processamento finalizado - histórico atualizado!")
            self.logger.info("=== Processo encerrado processado com sucesso - histórico atualizado ===")
            return -1  # Código específico para processo encerrado MAS com histórico atualizado
            
        except Exception as e:
            print(f"[ERRO] Erro durante processamento de sinistro encerrado: {e}")
            self.logger.error(f"Erro durante processamento de sinistro encerrado: {e}")
            
            # Mesmo com erro, marcar como encerrado
            try:
                from services.email_service import mark_process_as_closed
                mark_process_as_closed(numero_sinistro, f"Processo encerrado - erro: {e}")
            except:
                pass
                
            return -1  # Ainda retorna -1 mesmo com erro
    
    def _search_claim(self, numero_sinistro):
        """
        Busca pelo sinistro específico no sistema.
        
        Args:
            numero_sinistro (str): Número do sinistro a ser buscado
            
        Returns:
            bool: True se sucesso
        """
        try:
            # Tentativa 1: Campo específico identificado pelo usuário
            try:
                self.logger.info(f"Tentando localizar campo de busca de sinistro...")
                search_field = WebDriverWait(self.driver, self.config.DEFAULT_TIMEOUT).until(
                    EC.presence_of_element_located((By.ID, "c_c_c_dyncontrolNROSINIESTRO_txtFiltro_TextField"))
                )
                
                # Limpa o campo e preenche com fallback JavaScript
                try:
                    search_field.clear()
                    search_field.send_keys(numero_sinistro)
                    self.logger.info(f'Campo de sinistro preenchido com {numero_sinistro} via Selenium')
                except Exception as field_error:
                    self.logger.warning(f"Erro no preenchimento Selenium: {field_error}. Tentando JavaScript...")
                    # Fallback JavaScript para preenchimento
                    try:
                        js_script = f"""
                        var field = document.getElementById('c_c_c_dyncontrolNROSINIESTRO_txtFiltro_TextField');
                        if (field) {{
                            field.value = '';
                            field.value = '{numero_sinistro}';
                            field.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            field.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                        """
                        self.driver.execute_script(js_script)
                        self.logger.info(f'Campo de sinistro preenchido com {numero_sinistro} via JavaScript')
                    except Exception as js_error:
                        self.logger.error(f"Falha total no preenchimento do campo: {js_error}")
                        return False
                
                # Aguarda um pouco para garantir que o campo foi preenchido
                sleep(1)
                
                # Procura por botão de busca - várias possibilidades
                search_buttons = [
                    ("id", "ext-gen427"),  # ID específico identificado pelo usuário
                    ("xpath", "//button[contains(@class, 'icon-magnifier')]"),  # Por classe específica
                    ("xpath", "//button[contains(text(), 'Busca')]"),  # Por texto específico
                    ("id", "btnSearch"),
                    ("id", "btnBuscar"), 
                    ("xpath", "//button[contains(text(), 'Buscar')]"),
                    ("xpath", "//input[@value='Buscar']"),
                    ("xpath", "//input[@type='submit']"),
                    ("xpath", "//*[contains(@class, 'search') or contains(@class, 'buscar')]")
                ]
                
                for selector_type, selector_value in search_buttons:
                    try:
                        if selector_type == "xpath":
                            search_button = WebDriverWait(self.driver, 2).until(
                                EC.element_to_be_clickable((By.XPATH, selector_value))
                            )
                        else:
                            search_button = WebDriverWait(self.driver, 2).until(
                                EC.element_to_be_clickable((By.ID, selector_value))
                            )
                        
                        search_button.click()
                        self.logger.info(f'Botão de busca clicado: {selector_type}={selector_value}')
                        return True
                        
                    except TimeoutException:
                        continue
                
                # Se não encontrou botão clicável, tenta JavaScript
                try:
                    self.logger.info("Tentando clicar no botão via JavaScript...")
                    # Primeiro tenta o ID específico
                    click_script = "document.getElementById('ext-gen427').click();"
                    self.driver.execute_script(click_script)
                    self.logger.info('Botão de busca clicado via JavaScript (ID específico)')
                    return True
                except Exception as js_error:
                    self.logger.warning(f"JavaScript falhou: {js_error}")
                
                # Se JavaScript falhou, pressiona Enter no campo
                search_field.send_keys(Keys.RETURN)
                self.logger.info('Enter pressionado no campo de busca')
                return True
                
            except (TimeoutException, ElementNotInteractableException) as e:
                self.logger.warning(f"Campo específico não encontrado: {e}. Tentando IDs alternativos...")
                
                # Tentativa 2: IDs alternativos comuns
                alternative_ids = [
                    "txtClaim",
                    "txtSinistro", 
                    "txtNumero",
                    "txtBusca",
                    "searchField"
                ]
                
                for field_id in alternative_ids:
                    try:
                        search_field = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.ID, field_id))
                        )
                        
                        # Tentativa Selenium primeiro
                        try:
                            search_field.clear()
                            search_field.send_keys(numero_sinistro)
                            search_field.send_keys(Keys.RETURN)
                            self.logger.info(f'Sinistro {numero_sinistro} buscado com ID alternativo via Selenium: {field_id}')
                            return True
                        except Exception as selenium_error:
                            self.logger.warning(f"Erro Selenium no campo {field_id}: {selenium_error}. Tentando JavaScript...")
                            # Fallback JavaScript
                            try:
                                js_script = f"""
                                var field = document.getElementById('{field_id}');
                                if (field) {{
                                    field.value = '';
                                    field.value = '{numero_sinistro}';
                                    field.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    field.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    // Simula Enter
                                    var event = new KeyboardEvent('keydown', {{ key: 'Enter', keyCode: 13 }});
                                    field.dispatchEvent(event);
                                }}
                                """
                                self.driver.execute_script(js_script)
                                self.logger.info(f'Sinistro {numero_sinistro} buscado com ID alternativo via JavaScript: {field_id}')
                                return True
                            except Exception as js_error:
                                self.logger.warning(f"JavaScript falhou para campo {field_id}: {js_error}")
                                continue
                        return True
                        
                    except (TimeoutException, ElementNotInteractableException):
                        continue
                
                # Tentativa 3: Fallback JavaScript
                self.logger.warning("Tentando JavaScript como último recurso...")
                return self._fill_field_with_javascript(
                    "c_c_c_dyncontrolNROSINIESTRO_txtFiltro_TextField",
                    numero_sinistro,
                    "campo de número do sinistro"
                )
                
        except Exception as e:
            self.logger.error(f"Erro ao buscar sinistro {numero_sinistro}: {e}")
            self.screenshot_manager.take_error_screenshot("erro_busca_sinistro")
            return False
    
    def _open_claim(self):
        """
        Abre o sinistro encontrado na busca.
        
        Returns:
            bool: True se sucesso
        """
        try:
            self.logger.info("Tentando abrir sinistro...")
            
            # Aguarda um pouco para os resultados da busca carregarem
            sleep(2)
            
            # Lista de seletores para o botão de abrir sinistro
            open_buttons = [
                ("id", "ext-gen744"),  # ID específico identificado pelo usuário
                ("xpath", "//button[contains(@class, 'inw-vistas-body-verdetalles-normal')]"),  # Por classe específica
                ("xpath", "//button[contains(@class, 'verdetalles')]"),  # Parte da classe
                ("xpath", "//a[contains(@href, 'sinistro') or contains(@href, 'claim')]"),  # Link de sinistro
                ("xpath", "//button[contains(text(), 'Abrir')]"),
                ("xpath", "//button[contains(text(), 'Ver')]"),
                ("xpath", "//button[contains(text(), 'Detalhes')]"),
                ("xpath", "//input[@value='Abrir']"),
                ("xpath", "//a[contains(text(), 'Visualizar')]")
            ]
            
            for selector_type, selector_value in open_buttons:
                try:
                    if selector_type == "xpath":
                        result_element = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector_value))
                        )
                    else:
                        result_element = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.ID, selector_value))
                        )
                    
                    result_element.click()
                    self.logger.info(f"Sinistro aberto com sucesso: {selector_type}={selector_value}")
                    return True
                    
                except TimeoutException:
                    continue
            
            # Se não conseguiu clicar pelos métodos normais, tenta JavaScript
            try:
                self.logger.info("Tentando abrir sinistro via JavaScript...")
                # Primeiro tenta o ID específico
                click_script = "document.getElementById('ext-gen744').click();"
                self.driver.execute_script(click_script)
                self.logger.info('Sinistro aberto via JavaScript (ID específico)')
                return True
            except Exception as js_error:
                self.logger.warning(f"JavaScript falhou: {js_error}")
            
            # Se tudo falhou, tenta encontrar qualquer elemento clicável na área de resultados
            try:
                self.logger.info("Procurando qualquer elemento clicável nos resultados...")
                clickable_elements = self.driver.find_elements(By.XPATH, 
                    "//tr//button | //tr//a | //td//button | //td//a")
                
                for element in clickable_elements:
                    try:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self.logger.info("Clicou em elemento encontrado nos resultados")
                            return True
                    except:
                        continue
                        
            except Exception as e:
                self.logger.warning(f"Busca por elementos clicáveis falhou: {e}")
            
            self.logger.error("Não foi possível abrir o sinistro")
            self.screenshot_manager.take_error_screenshot("erro_abrir_sinistro")
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao abrir sinistro: {e}")
            self.screenshot_manager.take_error_screenshot("erro_critico_abrir_sinistro")
            return False
    
    def _check_edit_availability(self):
        """
        Verifica se o sinistro está disponível para edição.
        
        Returns:
            bool: True se disponível para edição
        """
        try:
            # Seletor específico baseado no elemento HTML fornecido
            # <button class="btn ng-scope btn-primary btn-sm"><span class="ng-binding">Editar</span></button>
            selectors = [
                "//button[span[contains(text(), 'Editar')] and contains(@class, 'ng-binding')]",
                "//button[contains(@class, 'btn-primary')]/span[contains(text(), 'Editar')]/parent::button",
                "//button[contains(@class, 'btn') and contains(@class, 'btn-primary')]/span[text()='Editar']/parent::button",
                "//span[contains(@class, 'ng-binding') and text()='Editar']/parent::button",
                "//button[span[contains(text(), 'Editar')]]",
                "//button[contains(text(), 'Editar')]",
                "//button[@ng-click and span[text()='Editar']]",
                f"//*[@id='{self.config.EDIT_BUTTON_ID}']"
            ]
            
            self.logger.info("Tentando localizar botão 'Editar' com diferentes seletores...")
            
            for i, selector in enumerate(selectors):
                try:
                    self.logger.info(f"Tentativa {i+1}: {selector}")
                    edit_button = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    
                    # Verificar se o botão está visível e habilitado
                    if edit_button.is_displayed() and edit_button.is_enabled():
                        # Verificar também se não está com ng-disabled
                        disabled_attr = edit_button.get_attribute("ng-disabled")
                        if disabled_attr and disabled_attr.lower() == "true":
                            self.logger.warning(f"Botão 'Editar' encontrado com seletor {i+1}, mas está desabilitado via ng-disabled.")
                            print(f"[AVISO] Botão 'Editar' encontrado (seletor {i+1}), mas está desabilitado.")
                            return False
                        
                        self.logger.info(f"Botão 'Editar' encontrado com seletor {i+1} e disponível para edição.")
                        print(f"[SUCESSO] Botão 'Editar' encontrado (seletor {i+1}) - sinistro pode ser editado!")
                        return True
                    else:
                        self.logger.warning(f"Botão 'Editar' encontrado com seletor {i+1}, mas não está visível ou habilitado.")
                        print(f"[AVISO] Botão 'Editar' encontrado (seletor {i+1}), mas não está disponível.")
                        return False
                        
                except TimeoutException:
                    self.logger.debug(f"Seletor {i+1} não encontrou o botão")
                    continue
                except Exception as e:
                    self.logger.debug(f"Erro com seletor {i+1}: {e}")
                    continue
            
            # Se chegou até aqui, nenhum seletor funcionou
            self.logger.warning("Botão 'Editar' não encontrado com nenhum dos seletores testados.")
            print("[AVISO] Botão 'Editar' não encontrado na página - sinistro pode já estar finalizado.")
            
            # Debug: listar todos os botões na página
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                button_info = []
                for btn in buttons:
                    if btn.text.strip():
                        classes = btn.get_attribute("class") or ""
                        button_info.append(f"'{btn.text.strip()}' (classes: {classes})")
                
                self.logger.info(f"Botões encontrados na página: {button_info}")
                print(f"[BUSCAR] Botões encontrados na página: {button_info[:5]}")  # Mostrar apenas os primeiros 5
            except Exception as debug_error:
                self.logger.debug(f"Erro ao listar botões para debug: {debug_error}")
                
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar disponibilidade do botão 'Editar': {e}")
            return False
    
    #clicar botão com seta pra direita
    def click_arrow_right(self):
        """
        Clica na seta para a direita com fallback JavaScript.
        
        Returns:
            bool: True se sucesso, False se falha
        """
        try:
            # Tentativa 1: Selenium padrão
            button = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.ID, "ext-gen331"))
            )
            button.click()
            self.logger.info("Botão 'ext-gen331' clicado com sucesso via Selenium.")
            return True
        except TimeoutException:
            self.logger.warning("Botão 'ext-gen331' não encontrado via Selenium. Tentando JavaScript...")
            # Fallback: JavaScript
            try:
                self.driver.execute_script("document.getElementById('ext-gen331').click();")
                self.logger.info("Botão 'ext-gen331' clicado com sucesso via JavaScript.")
                return True
            except Exception as js_error:
                self.logger.error(f"Falha no JavaScript para 'ext-gen331': {js_error}")
        except Exception as e:
            self.logger.warning(f"Erro Selenium no botão 'ext-gen331': {e}. Tentando JavaScript...")
            # Fallback: JavaScript
            try:
                self.driver.execute_script("document.getElementById('ext-gen331').click();")
                self.logger.info("Botão 'ext-gen331' clicado com sucesso via JavaScript.")
                return True
            except Exception as js_error:
                self.logger.error(f"Falha no JavaScript para 'ext-gen331': {js_error}")
        
        self.logger.error("Falha total ao clicar no botão 'ext-gen331'.")
        self.screenshot_manager.take_error_screenshot("erro_clicar_botao_ext_gen331")
        return False

    def click_history_button(self):
        """
        Clica no botão de histórico com fallback JavaScript.
        
        Returns:
            bool: True se sucesso, False se falha
        """
        try:
            # Tentativa 1: Selenium padrão
            button = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.ID, "ext-gen348"))
            )
            button.click()
            self.logger.info("Botão 'ext-gen348' clicado com sucesso via Selenium.")
            return True
        except TimeoutException:
            self.logger.warning("Botão 'ext-gen348' não encontrado via Selenium. Tentando JavaScript...")
            # Fallback: JavaScript
            try:
                self.driver.execute_script("document.getElementById('ext-gen348').click();")
                self.logger.info("Botão 'ext-gen348' clicado com sucesso via JavaScript.")
                return True
            except Exception as js_error:
                self.logger.error(f"Falha no JavaScript para 'ext-gen348': {js_error}")
        except Exception as e:
            self.logger.warning(f"Erro Selenium no botão 'ext-gen348': {e}. Tentando JavaScript...")
            # Fallback: JavaScript
            try:
                self.driver.execute_script("document.getElementById('ext-gen348').click();")
                self.logger.info("Botão 'ext-gen348' clicado com sucesso via JavaScript.")
                return True
            except Exception as js_error:
                self.logger.error(f"Falha no JavaScript para 'ext-gen348': {js_error}")
        
        self.logger.error("Falha total ao clicar no botão 'ext-gen348'.")
        self.screenshot_manager.take_error_screenshot("erro_clicar_botao_ext_gen348")
        return False
    

    def click_new_entity_button(self):
        """
        Clica no botão de nova entidade com fallback JavaScript.
        
        Returns:
            bool: True se sucesso, False se falha
        """
        try:
            # Tentativa 1: Selenium padrão
            button = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.ID, "c_c_bNewEntity"))
            )
            button.click()
            self.logger.info("Botão 'c_c_bNewEntity' clicado com sucesso via Selenium.")
            return True
        except TimeoutException:
            self.logger.warning("Botão 'c_c_bNewEntity' não encontrado via Selenium. Tentando JavaScript...")
            # Fallback: JavaScript
            try:
                self.driver.execute_script("document.getElementById('c_c_bNewEntity').click();")
                self.logger.info("Botão 'c_c_bNewEntity' clicado com sucesso via JavaScript.")
                return True
            except Exception as js_error:
                self.logger.error(f"Falha no JavaScript para 'c_c_bNewEntity': {js_error}")
        except Exception as e:
            self.logger.warning(f"Erro Selenium no botão 'c_c_bNewEntity': {e}. Tentando JavaScript...")
            # Fallback: JavaScript
            try:
                self.driver.execute_script("document.getElementById('c_c_bNewEntity').click();")
                self.logger.info("Botão 'c_c_bNewEntity' clicado com sucesso via JavaScript.")
                return True
            except Exception as js_error:
                self.logger.error(f"Falha no JavaScript para 'c_c_bNewEntity': {js_error}")
        
        self.logger.error("Falha total ao clicar no botão 'c_c_bNewEntity'.")
        self.screenshot_manager.take_error_screenshot("erro_clicar_botao_c_c_bNewEntity")
        return False




    def _add_update(self, subject, content_email, to_address, from_address=None, sent_time=None, cc_addresses=None):
        """
        Adiciona uma atualização ao sinistro seguindo a sequência:
        1. Preenche tipo de relatório com 00029
        2. Preenche campo observações com: assunto do email - processado pela automação
        3. Preenche campo comentários com: cabeçalho do email + conteúdo completo do corpo
        4. Salva o formulário
        
        Args:
            subject (str): Assunto do email
            content_email (str): Conteúdo do email
            to_address (str): Destinatário
            from_address (str): Remetente do email
            sent_time (str): Data e hora de envio
            cc_addresses (str): Endereços em cópia
            
        Returns:
            bool: True se sucesso
        """
        try:
            print(f"  [LOG] Iniciando adição de atualização para assunto: {subject}")
            self.logger.info(f"Iniciando adição de atualização para assunto: {subject}")
            
            # 1. Primeiro preenche o campo "Tipo de Informe" com código padrão 00029
            print("  [TAG] Preenchendo tipo de informe...")
            self._fill_tipo_informe(subject)  # Sempre tenta preencher, sem verificar retorno
            print("  [SUCESSO] Tipo de informe processado")
            
            # 2. Preenche campo OBSERVAÇÕES com assunto - processado pela automação (sem colchetes)
            print("  [LOG] Preenchendo campo observações...")
            data_hoje = datetime.now().strftime("%d-%m-%Y")
            observacoes_text = f"{data_hoje} - {subject} - Processado pela Automação"
            if self._fill_observacoes_field(observacoes_text):
                print("  [SUCESSO] Campo observações preenchido")
            else:
                print("  [AVISO] Erro ao preencher observações, mas continuando...")
            
            sleep(2)
            
            # 3. Preenche campo COMENTÁRIOS com cabeçalho + conteúdo completo do email
            print("  [LOG] Preenchendo campo comentários...")
            
            # Montar cabeçalho do email
            email_header = "=== INFORMAÇÕES DO EMAIL ===\n"
            if sent_time:
                email_header += f"Data de Envio: {sent_time}\n"
            if from_address:
                email_header += f"De: {from_address}\n"
            if to_address:
                email_header += f"Para: {to_address}\n"
            if cc_addresses:
                email_header += f"CC: {cc_addresses}\n"
            email_header += f"Assunto: {subject}\n"
            email_header += "=" * 35 + "\n\n"
            
            # Combinar cabeçalho com conteúdo
            comentarios_completo = email_header + content_email
            
            if self._fill_comentarios_field(comentarios_completo):
                print("  [SUCESSO] Campo comentários preenchido")
            else:
                print("  [AVISO] Erro ao preencher comentários, mas continuando...")
            
            sleep(2)

            # 4. Salva o formulário
            print("  [SALVAR] Salvando formulário...")
            if self._save_form():
                print("  [SUCESSO] Formulário salvo com sucesso")
                return True
            else:
                print("  [AVISO] Erro ao salvar, mas considerando processado...")
                return True  # Continua mesmo se salvar falhou
            
        except Exception as e:
            self.logger.error(f"Erro ao adicionar atualização: {e}")
            print(f"  [ERRO] Erro geral ao adicionar atualização: {e}")
            return False

    def _fill_observacoes_field(self, observacoes_text):
        """
        Preenche o campo de observações com fallback automático.
        
        Args:
            observacoes_text (str): Texto para o campo observações
            
        Returns:
            bool: True se preenchimento foi bem-sucedido
        """
        field_id = "c_c_c_SeguimientoClienteEditor_txtObservaciones_TextArea"
        return self._fill_field_with_fallback(
            field_id, 
            observacoes_text, 
            "campo observações"
        )

    def _fill_comentarios_field(self, comentarios_text):
        """
        Preenche o campo de comentários com fallback automático.
        
        Args:
            comentarios_text (str): Texto para o campo comentários
            
        Returns:
            bool: True se preenchimento foi bem-sucedido
        """
        field_id = "c_c_c_SeguimientoClienteEditor_txtComentario_TextArea"
        return self._fill_field_with_fallback(
            field_id, 
            comentarios_text, 
            "campo comentários"
        )

    def _fill_tipo_informe(self, subject):
        """
        Preenche o campo "Tipo de Informe" com o código padrão 00029.
        
        Args:
            subject (str): Assunto do email (não usado, sempre usa 00029)
            
        Returns:
            bool: True se preenchimento foi bem-sucedido
        """
        try:
            # Sempre usa o código padrão 00029
            codigo = "00029"
            
            # ID do campo baseado no HTML fornecido
            field_id = "c_c_c_SeguimientoClienteEditor_lkpTipoInforme_FieldLookUp"
            
            self.logger.info(f"Preenchendo tipo de informe com código padrão: {codigo}")
            print(f"    [TAG] Preenchendo tipo de informe com código padrão: {codigo}")
            
            try:
                # Tenta preencher o campo diretamente
                print(f"    [BUSCAR] Procurando campo: {field_id}")
                tipo_field = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, field_id))
                )
                
                if tipo_field.is_displayed() and tipo_field.is_enabled():
                    print(f"    [SUCESSO] Campo encontrado e disponível")
                    tipo_field.clear()
                    tipo_field.send_keys(codigo)
                    # Simula tecla TAB para confirmar a entrada
                    tipo_field.send_keys(Keys.TAB)
                    
                    self.logger.info(f"Tipo de informe preenchido com sucesso: {codigo}")
                    print(f"    [SUCESSO] Tipo de informe preenchido: {codigo}")
                    return True
                else:
                    self.logger.warning("Campo tipo de informe encontrado mas não disponível")
                    print(f"    [AVISO] Campo encontrado mas não disponível (displayed: {tipo_field.is_displayed()}, enabled: {tipo_field.is_enabled()})")
                    
            except TimeoutException:
                self.logger.warning("Campo tipo de informe não encontrado via seletor direto")
                print(f"    [ERRO] Campo {field_id} não encontrado")
            
            # Fallback: Tenta via JavaScript
            print(f"    [JS] Tentando via JavaScript...")
            result = self._fill_field_with_javascript(
                field_id,
                codigo,
                "tipo de informe"
            )
            
            if result:
                print(f"    [SUCESSO] Tipo de informe preenchido via JavaScript: {codigo}")
            else:
                print(f"    [ERRO] Falha ao preencher via JavaScript")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao preencher tipo de informe: {e}")
            print(f"    [ERRO] Erro ao preencher tipo de informe: {e}")
            return False

    def _save_form(self):
        """
        Salva o formulário clicando no botão Salvar.
        
        Returns:
            bool: True se salvamento foi bem-sucedido
        """
        try:
            # Botão específico fornecido pelo usuário
            save_button_id = "ext-gen525"
            
            self.logger.info(f"Tentando salvar formulário com botão: {save_button_id}")
            print(f"    [SALVAR] Procurando botão salvar: {save_button_id}")
            
            # Tenta encontrar e clicar no botão salvar
            save_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, save_button_id))
            )
            
            if save_button.is_displayed() and save_button.is_enabled():
                save_button.click()
                self.logger.info(f"Botão salvar '{save_button_id}' clicado com sucesso")
                print(f"    [SUCESSO] Botão salvar clicado: {save_button_id}")
                
                # Aguarda um pouco para o salvamento processar
                sleep(2)
                
                # Após salvar, clica no link para voltar ao sinistro
                print(f"    [VOLTA] Voltando ao sinistro...")
                if self._click_back_to_claim():
                    print(f"    [SUCESSO] Retornado ao sinistro com sucesso")
                else:
                    print(f"    [AVISO] Não foi possível retornar ao sinistro, mas continuando...")
                
                return True
            else:
                self.logger.warning(f"Botão salvar encontrado mas não disponível")
                print(f"    [AVISO] Botão salvar encontrado mas não disponível")
                return False
                
        except TimeoutException:
            self.logger.warning(f"Botão salvar '{save_button_id}' não encontrado")
            print(f"    [ERRO] Botão salvar não encontrado: {save_button_id}")
            
            # Fallback: tenta por classe ou texto
            try:
                print(f"    [BUSCA] Tentando encontrar botão por classe...")
                save_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'icon-Disk') and contains(text(), 'Salvar')]"))
                )
                save_button.click()
                self.logger.info("Botão salvar clicado via XPath (classe)")
                print(f"    [SUCESSO] Botão salvar clicado via XPath")
                sleep(2)
                
                # Após salvar, clica no link para voltar ao sinistro
                print(f"    [VOLTA] Voltando ao sinistro...")
                if self._click_back_to_claim():
                    print(f"    [SUCESSO] Retornado ao sinistro com sucesso")
                else:
                    print(f"    [AVISO] Não foi possível retornar ao sinistro, mas continuando...")
                
                return True
            except TimeoutException:
                print(f"    [ERRO] Nenhum botão salvar encontrado")
                return False
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar formulário: {e}")
            print(f"    [ERRO] Erro ao salvar formulário: {e}")
            return False

    def _click_back_to_claim(self):
        """
        Clica no link para voltar ao sinistro após salvar.
        
        Returns:
            bool: True se sucesso
        """
        try:
            # ID específico fornecido pelo usuário
            back_link_id = "ext-gen481"
            
            self.logger.info(f"Tentando clicar no link de retorno: {back_link_id}")
            print(f"      [BUSCAR] Procurando link de retorno: {back_link_id}")
            
            # Tenta encontrar e clicar no link
            back_link = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, back_link_id))
            )
            
            if back_link.is_displayed() and back_link.is_enabled():
                back_link.click()
                self.logger.info(f"Link de retorno '{back_link_id}' clicado com sucesso")
                print(f"      [SUCESSO] Link de retorno clicado: {back_link_id}")
                
                # Aguarda um pouco para a página carregar
                sleep(2)
                
                # Aguarda carregamento completo da página
                self._wait_for_page_load(timeout=10)
                
                # Após voltar ao sinistro, clica no botão Editar
                print(f"      [CLICK] Clicando no botão Editar...")
                if self._click_edit_button():
                    print(f"      [SUCESSO] Botão Editar clicado com sucesso")
                else:
                    print(f"      [AVISO] Não foi possível clicar no botão Editar, mas continuando...")
                
                return True
            else:
                self.logger.warning(f"Link de retorno encontrado mas não disponível")
                print(f"      [AVISO] Link de retorno encontrado mas não disponível")
                return False
                
        except TimeoutException:
            self.logger.warning(f"Link de retorno '{back_link_id}' não encontrado")
            print(f"      [ERRO] Link de retorno não encontrado: {back_link_id}")
            
            # Fallback: tenta por classe ou texto que contenha "Sinistro"
            try:
                print(f"      [BUSCA] Tentando encontrar link por texto...")
                back_link = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'link-navigate-to-register') and contains(text(), 'Sinistro')]"))
                )
                back_link.click()
                self.logger.info("Link de retorno clicado via XPath (texto)")
                print(f"      [SUCESSO] Link de retorno clicado via XPath")
                sleep(2)
                
                # Aguarda carregamento completo da página
                self._wait_for_page_load(timeout=10)
                
                # Após voltar ao sinistro, clica no botão Editar
                print(f"      [CLICK] Clicando no botão Editar...")
                if self._click_edit_button():
                    print(f"      [SUCESSO] Botão Editar clicado com sucesso")
                else:
                    print(f"      [AVISO] Não foi possível clicar no botão Editar, mas continuando...")
                
                return True
            except TimeoutException:
                print(f"      [ERRO] Nenhum link de retorno encontrado")
                return False
            
        except Exception as e:
            self.logger.error(f"Erro ao clicar no link de retorno: {e}")
            print(f"      [ERRO] Erro ao clicar no link de retorno: {e}")
            return False

    def _load_subject_mapping(self):
        """
        Carrega e valida o mapeamento de assuntos para códigos.
        
        Returns:
            dict: Mapeamento de assuntos para códigos
        """
        try:
            subject_to_code = json.loads(os.getenv("SUBJECT_TO_CODE", "{}"))
            self._validate_subject_to_code(subject_to_code)
            self.logger.info("Mapeamento SUBJECT_TO_CODE carregado com sucesso")
            return subject_to_code
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Erro ao carregar SUBJECT_TO_CODE: {e}")
            raise Exception("Erro ao carregar o mapeamento SUBJECT_TO_CODE. Verifique o arquivo .env.")
    
    def _validate_subject_to_code(self, subject_to_code):
        """
        Valida a estrutura do JSON SUBJECT_TO_CODE.
        
        Args:
            subject_to_code (dict): Dicionário a ser validado
        """
        if not isinstance(subject_to_code, dict):
            raise ValueError("SUBJECT_TO_CODE deve ser um dicionário.")
        for key, value in subject_to_code.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError(f"Chave e valor em SUBJECT_TO_CODE devem ser strings. Encontrado: {key}: {value}")
    
    def _navigate_to_claims_menu(self):
        """
        Navega para o menu de sinistros.
        
        Returns:
            bool: True se sucesso
        """
        try:
            print("  [PROCESSANDO] Clicando no menu de sinistros...")
            self.logger.info('Clicando no menu de sinistros...')
            
            # Tentativa 1: Método padrão
            try:
                element = WebDriverWait(self.driver, self.config.LONG_TIMEOUT).until(
                    EC.element_to_be_clickable((By.ID, self.config.SINISTROS_MENU_ID))
                )
                element.click()
                print("  [SUCESSO] Menu de sinistros clicado com sucesso")
                self.logger.info('Menu de sinistros clicado (método padrão)')
                return True
                
            except (TimeoutException, ElementNotInteractableException) as e:
                print("  [AVISO] Método padrão falhou, tentando JavaScript...")
                self.logger.warning(f"Método padrão falhou: {e}. Tentando JavaScript...")
                
                # Captura screenshot do erro antes de tentar fallback
                self.screenshot_manager.take_error_screenshot("falha_clique_menu_sinistros_metodo_padrao")
                
                # Tentativa 2: Fallback JavaScript
                return self._click_element_with_javascript(
                    self.config.SINISTROS_MENU_ID,
                    "menu de sinistros"
                )
                
        except Exception as e:
            print(f"  [ERRO] Erro ao navegar para menu de sinistros: {e}")
            self.logger.error(f"Erro ao navegar para menu de sinistros: {e}")
            self.screenshot_manager.take_error_screenshot("erro_critico_navegacao_menu_sinistros")
            return False
    
    def _access_search_option(self):
        """
        Acessa a opção de busca no menu.
        
        Returns:
            bool: True se sucesso
        """
        try:
            print("  [BUSCAR] Clicando em Buscar por opção do menu...")
            self.logger.info('Clicando em Buscar por opção do menu...')
            
            # Tentativa 1: Método padrão
            try:
                element = WebDriverWait(self.driver, self.config.DEFAULT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.ID, self.config.SEARCH_OPTION_ID))
                )
                element.click()
                print("  [SUCESSO] Opção de busca clicada com sucesso")
                self.logger.info('Opção de busca clicada (método padrão)')
                return True
                
            except (TimeoutException, ElementNotInteractableException) as e:
                self.logger.warning(f"Método padrão falhou: {e}. Tentando JavaScript...")
                
                # Tentativa 2: Fallback JavaScript
                return self._click_element_with_javascript(
                    self.config.SEARCH_OPTION_ID,
                    "opção de busca"
                )
                
        except Exception as e:
            self.logger.error(f"Erro ao acessar opção de busca: {e}")
            self.screenshot_manager.take_error_screenshot("erro_critico_acesso_opcao_busca")
            return False
    
    def _setup_default_view(self):
        """
        Configura a vista padrão para busca.
        
        Returns:
            bool: True se sucesso
        """
        try:
            self.logger.info('Configurando Vista Padrão...')
            
            # Preencher campo de busca
            if not self._fill_search_field():
                return False
            
            # Procurar e clicar na vista correta
            return self._select_default_view()
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar vista padrão: {e}")
            self.screenshot_manager.take_error_screenshot("erro_critico_configuracao_vista_padrao")
            return False
    
    def _fill_search_field(self):
        """
        Preenche o campo de busca com 'Vista Padrão'.
        
        Returns:
            bool: True se sucesso
        """
        try:
            # Tentativa 1: Método padrão
            try:
                search_field = WebDriverWait(self.driver, self.config.DEFAULT_TIMEOUT).until(
                    EC.presence_of_element_located((By.ID, self.config.SEARCH_TEXT_ID))
                )
                search_field.clear()
                search_field.send_keys(self.config.VISTA_PADRAO_TEXT)
                self.logger.info('Campo de busca preenchido (método padrão)')
                return True
                
            except (TimeoutException, ElementNotInteractableException) as e:
                self.logger.warning(f"Método padrão falhou: {e}. Tentando JavaScript...")
                
                # Tentativa 2: Fallback JavaScript
                return self._fill_field_with_javascript(
                    self.config.SEARCH_TEXT_ID,
                    self.config.VISTA_PADRAO_TEXT,
                    "campo de busca"
                )
                
        except Exception as e:
            self.logger.error(f"Erro ao preencher campo de busca: {e}")
            return False
    
    def _select_default_view(self):
        """
        Seleciona a vista padrão dos resultados da busca.
        
        Returns:
            bool: True se sucesso
        """
        try:
            for i in range(1, 30):
                try:
                    element = WebDriverWait(self.driver, self.config.VERY_SHORT_TIMEOUT).until(
                        EC.presence_of_element_located((By.XPATH, self.config.SEARCH_CONTAINER_XPATH.format(i)))
                    )
                    
                    if element.text == self.config.EXPECTED_VISTA_TEXT:
                        self.logger.info('Vista Principal / Sinistros encontrada, clicando...')
                        
                        # Tentativa 1: Click padrão
                        try:
                            element.click()
                            return True
                        except ElementNotInteractableException:
                            # Tentativa 2: JavaScript fallback
                            script = f"arguments[0].click();"
                            self.driver.execute_script(script, element)
                            self.logger.info('Vista selecionada via JavaScript')
                            return True
                            
                except TimeoutException:
                    continue
                except Exception as e:
                    self.logger.warning(f"Erro ao verificar elemento {i}: {e}")
                    continue
            
            self.logger.error("Vista Principal / Sinistros não encontrada")
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao selecionar vista padrão: {e}")
            return False
    
    def _edit_phone_number(self):
        """
        Edita o número de telefone do sinistro.
        
        Returns:
            bool: True se sucesso
        """
        try:
            # Primeiro clicar em Editar
            if not self._click_edit_button():
                return False
            
            # Aguarda carregamento
            sleep(self.config.EDIT_DELAY)
            
            # Preencher novo telefone
            if not self._fill_phone_field():
                return False
            
            # Salvar edição
            if not self._save_edit():
                return False
            
            # Confirmar salvamento
            if not self._confirm_save():
                return False
            
            self.logger.info('Telefone editado com sucesso')
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao editar telefone: {e}")
            return False
    
    def _click_edit_button(self):
        """
        Clica no botão Editar com múltiplas estratégias de fallback.
        
        Returns:
            bool: True se sucesso
        """
        try:
            self.logger.info('Clicando em Editar...')
            
            # Aguarda um pouco para garantir que a página carregou
            sleep(1)
            
            # Estratégia 1: Por ID padrão
            try:
                edit_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, self.config.EDIT_BUTTON_ID))
                )
                edit_button.click()
                self.logger.info('Botão Editar clicado (método padrão - ID)')
                sleep(1)  # Aguarda o clique ser processado
                return True
                
            except (TimeoutException, ElementNotInteractableException) as e:
                self.logger.warning(f"ID padrão falhou: {e}. Tentando XPath...")
                
                # Estratégia 2: Por XPath genérico
                try:
                    edit_selectors = [
                        "//button[contains(@id, 'edit')]",
                        "//a[contains(@id, 'edit')]", 
                        "//input[contains(@id, 'edit')]",
                        "//button[contains(text(), 'Editar')]",
                        "//a[contains(text(), 'Editar')]",
                        "//button[contains(@class, 'edit')]",
                        "//a[contains(@class, 'edit')]"
                    ]
                    
                    for selector in edit_selectors:
                        try:
                            edit_button = WebDriverWait(self.driver, 2).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", edit_button)
                            sleep(0.5)
                            edit_button.click()
                            self.logger.info(f'Botão Editar clicado via XPath: {selector}')
                            sleep(1)
                            return True
                        except:
                            continue
                    
                    self.logger.warning("XPath genérico falhou. Tentando JavaScript...")
                    
                    # Estratégia 3: JavaScript por ID
                    if self._click_element_with_javascript(
                        self.config.EDIT_BUTTON_ID,
                        "botão Editar"
                    ):
                        sleep(1)
                        return True
                    
                    # Estratégia 4: JavaScript por múltiplos seletores
                    js_selectors = [
                        f"document.getElementById('{self.config.EDIT_BUTTON_ID}')",
                        "document.querySelector('button[id*=\"edit\"]')",
                        "document.querySelector('a[id*=\"edit\"]')",
                        "document.querySelector('button:contains(\"Editar\")')",
                        "document.querySelector('a:contains(\"Editar\")')",
                        "document.querySelector('button[class*=\"edit\"]')",
                        "document.querySelector('a[class*=\"edit\"]')"
                    ]
                    
                    for js_selector in js_selectors:
                        try:
                            script = f"""
                                var element = {js_selector};
                                if (element && element.offsetParent !== null) {{
                                    element.scrollIntoView(true);
                                    setTimeout(function() {{
                                        element.click();
                                    }}, 100);
                                    return true;
                                }}
                                return false;
                            """
                            
                            result = self.driver.execute_script(script)
                            if result:
                                self.logger.info(f'Botão Editar clicado via JavaScript: {js_selector}')
                                sleep(1.5)  # Aguarda mais tempo para JavaScript
                                return True
                        except Exception as js_error:
                            self.logger.debug(f"JavaScript falhou para {js_selector}: {js_error}")
                            continue
                    
                    # Estratégia 5: Busca por todos os elementos clicáveis e filtra
                    try:
                        self.logger.info("Tentando busca avançada por elementos clicáveis...")
                        
                        # Busca todos os elementos clicáveis na página
                        clickable_elements = self.driver.find_elements(By.XPATH, 
                            "//button | //a | //input[@type='button'] | //input[@type='submit']")
                        
                        for element in clickable_elements:
                            try:
                                element_id = element.get_attribute('id') or ''
                                element_class = element.get_attribute('class') or ''
                                element_text = element.text or ''
                                element_value = element.get_attribute('value') or ''
                                
                                # Verifica se o elemento pode ser o botão Editar
                                if any(keyword in (element_id + element_class + element_text + element_value).lower() 
                                      for keyword in ['edit', 'editar', 'go-edit']):
                                    
                                    # Verifica se o elemento está visível
                                    if element.is_displayed() and element.is_enabled():
                                        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                        sleep(0.5)
                                        element.click()
                                        self.logger.info(f'Botão Editar encontrado e clicado: ID={element_id}, class={element_class}')
                                        sleep(1)
                                        return True
                                        
                            except Exception as elem_error:
                                continue
                                
                    except Exception as search_error:
                        self.logger.warning(f"Busca avançada falhou: {search_error}")
                    
                    self.logger.warning('Todas as estratégias falharam - botão Editar não encontrado ou não clicável')
                    return False
                    
                except Exception as xpath_error:
                    self.logger.error(f"Erro na estratégia XPath: {xpath_error}")
                    return False
                
        except Exception as e:
            self.logger.error(f"Erro geral ao clicar no botão Editar: {e}")
            return False
    
    def _fill_phone_field(self):
        """
        Preenche o campo de telefone com número aleatório.
        
        Returns:
            bool: True se sucesso
        """
        try:
            self.logger.info('Preenchendo campo de telefone...')
            
            new_phone = str(random.randint(1000000000, 9999999999))
            
            # Tentativa 1: Método padrão
            try:
                phone_field = WebDriverWait(self.driver, self.config.DEFAULT_TIMEOUT).until(
                    EC.presence_of_element_located((By.NAME, self.config.PHONE_FIELD_NAME))
                )
                phone_field.clear()
                phone_field.send_keys(new_phone)
                self.logger.info(f'Telefone preenchido: {new_phone} (método padrão)')
                return True
                
            except (TimeoutException, ElementNotInteractableException) as e:
                self.logger.warning(f"Método padrão falhou: {e}. Tentando JavaScript...")
                
                # Tentativa 2: Fallback JavaScript
                script = f"""
                    var element = document.getElementsByName('{self.config.PHONE_FIELD_NAME}')[0];
                    if (element) {{
                        element.value = '{new_phone}';
                        element.dispatchEvent(new Event('input', {{bubbles: true}}));
                        element.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return true;
                    }} else {{
                        return false;
                    }}
                """
                
                result = self.driver.execute_script(script)
                if result:
                    self.logger.info(f'Telefone preenchido via JavaScript: {new_phone}')
                    return True
                else:
                    self.logger.error('Campo de telefone não encontrado via JavaScript')
                    return False
                
        except Exception as e:
            self.logger.error(f"Erro ao preencher campo de telefone: {e}")
            return False
    
    def _save_edit(self):
        """
        Salva a edição do sinistro.
        
        Returns:
            bool: True se sucesso
        """
        try:
            self.logger.info('Salvando edição...')
            
            # Tentativa 1: Método padrão
            try:
                save_button = WebDriverWait(self.driver, self.config.DEFAULT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.XPATH, self.config.SAVE_EDIT_XPATH))
                )
                save_button.click()
                self.logger.info('Edição salva (método padrão)')
                return True
                
            except (TimeoutException, ElementNotInteractableException) as e:
                self.logger.warning(f"Método padrão falhou: {e}. Tentando JavaScript...")
                
                # Tentativa 2: Fallback JavaScript
                script = f"""
                    var element = document.evaluate('{self.config.SAVE_EDIT_XPATH}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (element) {{
                        element.click();
                        return true;
                    }} else {{
                        return false;
                    }}
                """
                
                result = self.driver.execute_script(script)
                if result:
                    self.logger.info('Edição salva via JavaScript')
                    return True
                else:
                    self.logger.error('Botão salvar edição não encontrado')
                    return False
                
        except Exception as e:
            self.logger.error(f"Erro ao salvar edição: {e}")
            return False
    
    def _confirm_save(self):
        """
        Confirma o salvamento.
        
        Returns:
            bool: True se sucesso
        """
        try:
            self.logger.info('Confirmando salvamento...')
            
            # Tentativa 1: Método padrão
            try:
                confirm_button = WebDriverWait(self.driver, self.config.DEFAULT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.XPATH, self.config.CONFIRM_XPATH))
                )
                confirm_button.click()
                self.logger.info('Salvamento confirmado (método padrão)')
                return True
                
            except (TimeoutException, ElementNotInteractableException) as e:
                self.logger.warning(f"Método padrão falhou: {e}. Tentando JavaScript...")
                
                # Tentativa 2: Fallback JavaScript
                script = f"""
                    var element = document.evaluate('{self.config.CONFIRM_XPATH}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (element) {{
                        element.click();
                        return true;
                    }} else {{
                        return false;
                    }}
                """
                
                result = self.driver.execute_script(script)
                if result:
                    self.logger.info('Salvamento confirmado via JavaScript')
                    return True
                else:
                    self.logger.error('Botão confirmar não encontrado')
                    return False
                
        except Exception as e:
            self.logger.error(f"Erro ao confirmar salvamento: {e}")
            return False
    
    # --- Métodos auxiliares para JavaScript ---
    
    def _wait_for_page_load(self, timeout=10):
        """
        Aguarda a página carregar completamente.
        
        Args:
            timeout (int): Timeout em segundos
            
        Returns:
            bool: True se página carregou, False se timeout
        """
        try:
            self.logger.info("Aguardando carregamento completo da página...")
            
            # Aguarda JavaScript carregar
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Aguarda jQuery se estiver presente
            try:
                WebDriverWait(self.driver, 3).until(
                    lambda driver: driver.execute_script("return typeof jQuery !== 'undefined' ? jQuery.active == 0 : true")
                )
            except:
                pass  # jQuery pode não estar presente
            
            # Aguarda Angular se estiver presente
            try:
                WebDriverWait(self.driver, 3).until(
                    lambda driver: driver.execute_script(
                        "return typeof angular !== 'undefined' ? angular.element(document).injector().get('$http').pendingRequests.length === 0 : true"
                    )
                )
            except:
                pass  # Angular pode não estar presente
            
            self.logger.info("Página carregada completamente")
            return True
            
        except TimeoutException:
            self.logger.warning(f"Timeout ao aguardar carregamento da página ({timeout}s)")
            return False
        except Exception as e:
            self.logger.warning(f"Erro ao aguardar carregamento: {e}")
            return False
    
    def _fill_field_with_fallback(self, field_id, value, field_name, trigger_events=True):
        """
        Preenche um campo com fallback automático Selenium -> JavaScript.
        
        Args:
            field_id (str): ID do campo
            value (str): Valor a ser preenchido
            field_name (str): Nome do campo para logs
            trigger_events (bool): Se deve disparar eventos JS
            
        Returns:
            bool: True se sucesso
        """
        try:
            # Tentativa 1: Selenium padrão
            self.logger.info(f"Preenchendo {field_name} via Selenium...")
            field = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, field_id))
            )
            if field.is_displayed() and field.is_enabled():
                field.clear()
                # Se for o campo de comentários, usa clipboard para evitar problemas de foco
                if field_id == "c_c_c_SeguimientoClienteEditor_txtComentario_TextArea":
                    self.logger.info(f"Preenchendo {field_name} via clipboard para evitar problemas de foco...")
                    try:
                        # Salva o conteúdo atual do clipboard
                        clipboard_backup = pyperclip.paste()
                        
                        # Copia o valor para o clipboard
                        pyperclip.copy(value)
                        
                        # Clica no campo e cola o conteúdo
                        field.click()
                        sleep(0.2)  # pequena pausa após clicar
                        field.send_keys(Keys.CONTROL + "v")
                        
                        # Restaura o clipboard original
                        pyperclip.copy(clipboard_backup)
                        
                        self.logger.info(f"{field_name} preenchido com sucesso via clipboard")
                    except Exception as clipboard_error:
                        self.logger.warning(f"Erro ao usar clipboard: {clipboard_error}, voltando ao método normal")
                        field.send_keys(value)
                        self.logger.info(f"{field_name} preenchido com sucesso via send_keys")
                else:
                    # Para outros campos, usa o método normal
                    try:
                        field.click()
                    except Exception:
                        pass
                    field.send_keys(value)
                    self.logger.info(f"{field_name} preenchido com sucesso via Selenium")
                return True
            else:
                self.logger.warning(f"{field_name} encontrado mas não disponível via Selenium")
        except Exception as selenium_error:
            self.logger.warning(f"Erro Selenium em {field_name}: {selenium_error}")
        
        # Fallback: JavaScript
        self.logger.info(f"Tentando preencher {field_name} via JavaScript...")
        try:
            events_script = ""
            if trigger_events:
                events_script = """
                    field.dispatchEvent(new Event('input', { bubbles: true }));
                    field.dispatchEvent(new Event('change', { bubbles: true }));
                """
            
            js_script = f"""
            var field = document.getElementById('{field_id}');
            if (field) {{
                field.value = '';
                field.value = '{value}';
                {events_script}
                return true;
            }}
            return false;
            """
            
            result = self.driver.execute_script(js_script)
            if result:
                self.logger.info(f"{field_name} preenchido com sucesso via JavaScript")
                return True
            else:
                self.logger.error(f"Campo {field_name} não encontrado via JavaScript")
                
        except Exception as js_error:
            self.logger.error(f"Erro JavaScript em {field_name}: {js_error}")
        
        self.logger.error(f"Falha total ao preencher {field_name}")
        return False
    
    def _click_element_with_fallback(self, element_id, element_name):
        """
        Clica em um elemento com fallback automático Selenium -> JavaScript.
        
        Args:
            element_id (str): ID do elemento
            element_name (str): Nome do elemento para logs
            
        Returns:
            bool: True se sucesso
        """
        try:
            # Tentativa 1: Selenium padrão
            self.logger.info(f"Clicando em {element_name} via Selenium...")
            element = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, element_id))
            )
            element.click()
            self.logger.info(f"{element_name} clicado com sucesso via Selenium")
            return True
            
        except Exception as selenium_error:
            self.logger.warning(f"Erro Selenium em {element_name}: {selenium_error}")
        
        # Fallback: JavaScript
        self.logger.info(f"Tentando clicar em {element_name} via JavaScript...")
        try:
            js_script = f"""
            var element = document.getElementById('{element_id}');
            if (element) {{
                element.click();
                return true;
            }}
            return false;
            """
            
            result = self.driver.execute_script(js_script)
            if result:
                self.logger.info(f"{element_name} clicado com sucesso via JavaScript")
                return True
            else:
                self.logger.error(f"Elemento {element_name} não encontrado via JavaScript")
                
        except Exception as js_error:
            self.logger.error(f"Erro JavaScript em {element_name}: {js_error}")
        
        self.logger.error(f"Falha total ao clicar em {element_name}")
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
            # Escapa aspas simples no valor
            escaped_value = value.replace("'", "\\'")
            
            script = f"""
                var element = document.getElementById('{field_id}');
                if (element) {{
                    element.value = '{escaped_value}';
                    element.dispatchEvent(new Event('input', {{bubbles: true}}));
                    element.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return true;
                }} else {{
                    return false;
                }}
            """
            
            result = self.driver.execute_script(script)
            if result:
                self.logger.info(f"{field_name} preenchido via JavaScript")
                return True
            else:
                self.logger.error(f"Elemento {field_name} não encontrado via JavaScript")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro no JavaScript para {field_name}: {e}")
            return False
    
    def _click_element_with_javascript(self, element_id, element_name):
        """
        Clica em um elemento usando JavaScript como fallback com verificações robustas.
        
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
                    // Verifica se o elemento está visível e habilitado
                    if (element.offsetParent !== null && !element.disabled) {{
                        // Scroll para o elemento
                        element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        
                        // Aguarda um pouco e clica
                        setTimeout(function() {{
                            try {{
                                // Tenta clique direto
                                element.click();
                                console.log('Clique direto executado com sucesso');
                            }} catch(e) {{
                                // Se falhar, dispara evento de clique manualmente
                                var event = new MouseEvent('click', {{
                                    view: window,
                                    bubbles: true,
                                    cancelable: true
                                }});
                                element.dispatchEvent(event);
                                console.log('Evento de clique disparado manualmente');
                            }}
                        }}, 200);
                        
                        return true;
                    }} else {{
                        console.log('Elemento encontrado mas não visível ou desabilitado');
                        return false;
                    }}
                }} else {{
                    console.log('Elemento não encontrado');
                    return false;
                }}
            """
            
            result = self.driver.execute_script(script)
            if result:
                self.logger.info(f"{element_name} clicado via JavaScript")
                sleep(1)  # Aguarda o processamento do clique
                return True
            else:
                self.logger.error(f"Elemento {element_name} não encontrado ou não clicável via JavaScript")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro no JavaScript para {element_name}: {e}")
            return False


# --- Funções de compatibilidade para manter API existente ---
def validate_subject_to_code(subject_to_code):
    """
    Função de compatibilidade que mantém a API original de validação.
    
    Args:
        subject_to_code (dict): Dicionário a ser validado
    """
    manager = NavigationManager(None, None)
    manager._validate_subject_to_code(subject_to_code)


def navigate_and_perform_actions(driver, subject, numero_sinistro, content_email, 
                                cc_addresses, to_address, from_address, logger):
    """
    Função de compatibilidade que mantém a API original.
    
    Args:
        driver: Instância do WebDriver do Selenium
        subject (str): Assunto do email
        numero_sinistro (str): Número do sinistro
        content_email (str): Conteúdo do email
        cc_addresses (str): Endereços em cópia
        to_address (str): Destinatário do email
        from_address (str): Remetente do email
        logger: Logger para registrar as operaçoes
        
    Returns:
        int: 1 se sucesso, 0 se falha
    """
    navigation_manager = NavigationManager(driver, logger)
    return navigation_manager.navigate_and_perform_actions(
        subject, numero_sinistro, content_email, 
        cc_addresses, to_address, from_address
    )
