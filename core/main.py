# -*- coding: utf-8 -*-
"""
Modulo principal do sistema de automacao de sinistros AON.

Este modulo coordena a execucao completa do sistema, incluindo:
- Processamento de emails do Outlook
- Autenticacao no sistema AON
- Navegacao e preenchimento de formulários
- Geracao de relatorios e logs
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Adiciona o diretorio pai ao path para permitir execucao direta
if __name__ == "__main__":
    # Adiciona o diretorio raiz do projeto ao Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    sys.path.insert(0, project_root)

# Importacoes condicionais para suportar execucao direta e como modulo
try:
    from ..utils.webdriver_setup import setup_webdriver
    from ..services.login_service import AonLoginManager
    from ..services.navigation_service import NavigationManager
    from ..services.email_service import (
        get_emails_24h_new_only,
        mark_email_as_processed, 
        clean_old_processed_emails,
        send_claim_email, 
        send_processing_email, 
        send_summary_email
    )
    from ..utils.helpers import (
        log_and_print, 
        setup_logger
    )
except ImportError:
    # Fallback para execucao direta
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from utils.webdriver_setup import setup_webdriver
        from services.login_service import AonLoginManager
        from services.navigation_service import NavigationManager
        from services.email_service import (
            get_emails_24h_new_only,
            mark_email_as_processed, 
            clean_old_processed_emails,
            send_claim_email, 
            send_processing_email, 
            send_summary_email
        )
        from utils.helpers import (
            log_and_print, 
            setup_logger
        )
    except ImportError as e:
        print(f"[ERRO] Erro de import: {e}")
        print("[INFO] Execute o script a partir do diretorio raiz do projeto")
        sys.exit(1)

# Constantes de configuracao
DEFAULT_MAX_RETRIES = 3
DEFAULT_LOGIN_ERROR_MESSAGE = "Login ou senha incorretos."


def main():
    """
    Funcao principal que coordena a execucao do sistema de automacao.
    
    Fluxo de execucao:
    1. Carrega configuracoes e credenciais
    2. Recupera emails do Outlook
    3. Processa cada email nao processado
    4. Realiza login e navegacao no sistema AON
    5. Gera relatorios e envia confirmacoes
    """
    # LOG DETALHADO: Inicio do sistema
    print("=" * 100)
    print(" " * 20 + "[*] SISTEMA DE AUTOMACAO DE SINISTROS [*]")
    print("=" * 100)
    print(f"[SISTEMA] Iniciando execucao em: {datetime.now().strftime('%d/%m/%Y as %H:%M:%S')}")
    print("[SISTEMA] Versao: Automacao AON v2.0")
    print("[SISTEMA] Modo: Processamento automatico de emails")
    print("=" * 100)
    
    # Marcar inicio da execucao
    execution_start_time = datetime.now()
    
    # FASE 1: Inicializacao do sistema
    print("\n[FASE 1] [CONFIG] INICIALIZAÇÃO DO SISTEMA")
    print("-" * 50)
    
    # Sub-fase 1.1: Configuracao do ambiente
    print("[FASE 1.1] Carregando variáveis de ambiente...")
    load_dotenv(override=True)  # Override=True para usar credenciais da interface
    print("[FASE 1.1] [OK] Variáveis de ambiente carregadas")

    # Sub-fase 1.2: Configuracao do logger
    print("[FASE 1.2] Configurando sistema de logs...")
    logger = setup_logger()
    print("[FASE 1.2] [OK] Sistema de logs configurado")
    logger.info("Sistema iniciado - Inicio da execucao principal")

    # Sub-fase 1.3: Configuracoes do sistema
    print("[FASE 1.3] Carregando configuracoes do sistema...")
    max_retries = int(os.getenv('MAX_RETRIES', DEFAULT_MAX_RETRIES))
    login_error_message = os.getenv('LOGIN_ERROR_MESSAGE', DEFAULT_LOGIN_ERROR_MESSAGE)
    print(f"[FASE 1.3] Máximo de tentativas por email: {max_retries}")
    print(f"[FASE 1.3] [OK] Configuracoes carregadas")

    # Sub-fase 1.4: Inicializacao das listas de controle
    print("[FASE 1.4] Inicializando estruturas de controle...")
    processed_list = []
    non_processed_list = []
    print("[FASE 1.4] [OK] Listas de controle inicializadas")
    
    print("[FASE 1] [OK] INICIALIZAÇÃO CONCLUÍDA")
    logger.info("Fase 1 (Inicializacao) concluida com sucesso")

    try:
        # FASE 2: Limpeza e preparacao
        print("\n[FASE 2] [CLEAN] LIMPEZA E PREPARAÇÃO")
        print("-" * 50)
        
        # Sub-fase 2.1: Limpeza de emails antigos
        print("[FASE 2.1] Removendo emails processados antigos (> 7 dias)...")
        logger.info("Iniciando limpeza de emails processados antigos")
        clean_old_processed_emails(days_to_keep=7)
        print("[FASE 2.1] [OK] Limpeza de emails antigos concluida")
        
        # Sub-fase 2.2: Limpeza de processos encerrados antigos
        print("[FASE 2.2] Removendo processos encerrados antigos (> 30 dias)...")
        try:
            from services.email_service import clean_old_closed_processes, count_closed_processes
            processos_antes = count_closed_processes()
            print(f"[FASE 2.2] Processos encerrados atualmente: {processos_antes}")
            clean_old_closed_processes(days_to_keep=30)
            processos_depois = count_closed_processes()
            removidos = processos_antes - processos_depois
            print(f"[FASE 2.2] Processos apos limpeza: {processos_depois}")
            print(f"[FASE 2.2] Processos removidos: {removidos}")
            print("[FASE 2.2] [OK] Limpeza de processos encerrados concluida")
            logger.info(f"Limpeza de processos: {removidos} processos removidos, {processos_depois} mantidos")
        except Exception as e:
            print(f"[FASE 2.2] [AVISO] Erro na limpeza de processos: {e}")
            logger.warning(f"Erro na limpeza de processos encerrados: {e}")
        
        print("[FASE 2] [OK] LIMPEZA E PREPARAÇÃO CONCLUÍDA")

        # FASE 3: Recuperacao de emails
        print("\n[FASE 3] [EMAIL] RECUPERAÇÃO DE EMAILS")
        print("-" * 50)
        
        print("[FASE 3.1] Conectando ao Outlook...")
        print("[FASE 3.1] Buscando emails novos das ultimas 24 horas...")
        logger.info("Iniciando busca por emails das ultimas 24 horas")
        
        email_info_list = get_emails_24h_new_only()
        
        print(f"[FASE 3.1] [OK] Busca concluida: {len(email_info_list)} emails encontrados")
        
        if len(email_info_list) == 0:
            print("[FASE 3.1] [INFO] Nenhum email novo encontrado para processamento")
            logger.info("Nenhum email novo encontrado - finalizando execucao")
        else:
            print(f"[FASE 3.1] [INBOX] {len(email_info_list)} emails NOVOS aguardando processamento")
            
            # Exibir resumo dos emails encontrados
            print("[FASE 3.2] Resumo dos emails encontrados:")
            for i, email_data in enumerate(email_info_list[:5], 1):  # Mostrar apenas os primeiros 5
                numero_sinistro = email_data[0] or "SEM_NUMERO"
                subject = email_data[1]
                from_address = email_data[6]
                print(f"[FASE 3.2] {i}. Sinistro: {numero_sinistro} | De: {from_address}")
                print(f"[FASE 3.2]    Assunto: {subject[:60]}...")
            
            if len(email_info_list) > 5:
                print(f"[FASE 3.2] ... e mais {len(email_info_list) - 5} emails")
        
        print("[FASE 3] [OK] RECUPERAÇÃO DE EMAILS CONCLUÍDA")
        logger.info(f"Fase 3 (Recuperacao de emails) concluida: {len(email_info_list)} emails para processar")

        # Verificacao se há emails para processar
        if not email_info_list:
            print("\n[FINALIZAÇÃO] [INFO] NENHUM EMAIL PARA PROCESSAR")
            print("-" * 50)
            print("[FINALIZAÇÃO] Nenhum email novo encontrado nas ultimas 24 horas")
            print("[FINALIZAÇÃO] Sistema será finalizado sem processamento")
            print("[FINALIZAÇÃO] [OK] Execucao concluida normalmente")
            logger.info("Nenhum email novo encontrado - finalizando execucao normal")
            return

        # FASE 4: Validacao de credenciais
        print("\n[FASE 4] [AUTH] VALIDAÇÃO DE CREDENCIAIS")
        print("-" * 50)
        
        print("[FASE 4.1] Obtendo credenciais de autenticacao...")
        logger.info("Iniciando validacao de credenciais")
        credentials = _validate_credentials()
        
        if not credentials:
            print("[FASE 4.1] [ERRO] FALHA NA VALIDAÇÃO DE CREDENCIAIS")
            print("[FASE 4.1] Sistema será finalizado - credenciais inválidas")
            logger.error("Falha na validacao de credenciais - finalizando execucao")
            return
        
        print("[FASE 4.1] [OK] Credenciais validadas com sucesso")
        print(f"[FASE 4.1] URL: {credentials.get('url', 'N/A')}")
        print(f"[FASE 4.1] Usuário: {credentials.get('username', 'N/A')}")
        print("[FASE 4] [OK] VALIDAÇÃO DE CREDENCIAIS CONCLUÍDA")
        logger.info("Fase 4 (Validacao de credenciais) concluida com sucesso")

        # FASE 5: Processamento de emails
        print("\n[FASE 5] [EXEC] PROCESSAMENTO DE EMAILS")
        print("-" * 50)
        
        print(f"[FASE 5] Iniciando processamento de {len(email_info_list)} emails...")
        print(f"[FASE 5] Máximo de tentativas por email: {max_retries}")
        print(f"[FASE 5] Horário de inicio: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80)
        
        logger.info(f"Iniciando Fase 5: processamento de {len(email_info_list)} emails")
        
        _process_emails(
            email_info_list, 
            credentials, 
            max_retries, 
            login_error_message,
            logger,
            processed_list,
            non_processed_list
        )
        
        print("=" * 80)
        print("[FASE 5] [OK] PROCESSAMENTO DE EMAILS CONCLUÍDO")
        logger.info("Fase 5 (Processamento de emails) concluida")

    except Exception as e:
        print(f"\n[ERRO CRÍTICO] [ERRO] FALHA NO SISTEMA: {e}")
        print("[ERRO CRÍTICO] Execucao será interrompida")
        logger.error(f"Erro critico no sistema: {e}")
        print("-" * 50)
    
    finally:
        # FASE 6: Geracao de relatorios
        print("\n[FASE 6] [RELAT] GERAÇÃO DE RELATÓRIOS")
        print("-" * 50)
        
        execution_end_time = datetime.now()
        execution_duration = execution_end_time - execution_start_time
        
        print(f"[FASE 6] Gerando relatorio final consolidado...")
        print(f"[FASE 6] Horário de termino: {execution_end_time.strftime('%H:%M:%S')}")
        print(f"[FASE 6] Duracao total da execucao: {execution_duration}")
        print(f"[FASE 6] Emails processados com sucesso: {len(processed_list)}")
        print(f"[FASE 6] Emails com falha: {len(non_processed_list)}")
        
        logger.info(f"Iniciando Fase 6: geracao de relatorios - {len(processed_list)} sucessos, {len(non_processed_list)} falhas")
        
        _generate_final_report(processed_list, non_processed_list, logger, 
                             execution_start_time, execution_end_time)
        
        print("[FASE 6] [OK] GERAÇÃO DE RELATÓRIOS CONCLUÍDA")
        
        # Finalizacao do sistema
        print("\n" + "=" * 100)
        print(" " * 25 + "[META] EXECUÇÃO FINALIZADA [META]")
        print("=" * 100)
        print(f"[SISTEMA] Horário de termino: {execution_end_time.strftime('%d/%m/%Y as %H:%M:%S')}")
        print(f"[SISTEMA] Duracao total: {execution_duration}")
        print(f"[SISTEMA] Status: Execucao concluida com sucesso")
        print("=" * 100)
        
        logger.info(f"Sistema finalizado - Duracao: {execution_duration}, Sucessos: {len(processed_list)}, Falhas: {len(non_processed_list)}")


def _validate_credentials():
    """
    Valida e retorna as credenciais do sistema.
    
    Returns:
        dict: Dicionário com credenciais ou None se inválidas
    """
    username = os.getenv('AON_USERNAME')
    password = os.getenv('AON_PASSWORD')
    url = os.getenv('AON_URL')

    if not all([username, password, url]):
        print("[ERRO] Credenciais nao encontradas!")
        missing = []
        if not username: missing.append("AON_USERNAME")
        if not password: missing.append("AON_PASSWORD")
        if not url: missing.append("AON_URL")
        
        print(f"[ERRO] Variaveis ausentes: {', '.join(missing)}")
        return None
    
    return {'username': username, 'password': password, 'url': url}


def _process_emails(email_info_list, credentials, max_retries, 
                   login_error_message, logger, processed_list, non_processed_list):
    """
    Processa a lista de emails encontrados (já filtrados e novos).
    
    Args:
        email_info_list: Lista de emails NOVOS das ultimas 24h
        credentials: Credenciais de acesso
        max_retries: Numero máximo de tentativas
        login_error_message: Mensagem de erro de login
        logger: Logger do sistema
        processed_list: Lista para armazenar sucessos
        non_processed_list: Lista para armazenar falhas
    """
    total_emails = len(email_info_list)
    
    # LOG DETALHADO: Inicio do processamento da fila
    print("=" * 80)
    print(f"[FILA] INICIANDO PROCESSAMENTO DA FILA DE EMAILS")
    print(f"[FILA] Total de emails na fila: {total_emails}")
    print(f"[FILA] Máximo de tentativas por email: {max_retries}")
    print("=" * 80)
    logger.info(f"Iniciando processamento da fila: {total_emails} emails")
    
    for index, email_data in enumerate(email_info_list, start=1):
        numero_sinistro, subject, subject_email, content_email, to_address, cc_addresses, from_address, sent_time = email_data[:8]
        numero_sinistro = numero_sinistro or "SEM_NUMERO"
        numero_sinistro = str(numero_sinistro).strip()
        
        # LOG DETALHADO: Posicao na fila e informacoes do email
        print("\n" + "=" * 60)
        print(f"[FILA] PROCESSANDO EMAIL {index} DE {total_emails}")
        print(f"[FILA] Posicao na fila: {index}/{total_emails} ({(index/total_emails)*100:.1f}%)")
        print(f"[FILA] Sinistro: {numero_sinistro}")
        print(f"[FILA] Assunto: {subject}")
        print(f"[FILA] Remetente: {from_address}")
        print(f"[FILA] Data do email: {sent_time}")
        print("=" * 60)
        
        logger.info(f"[FILA {index}/{total_emails}] Iniciando processamento do sinistro {numero_sinistro}: {subject}")
        
        success = _process_single_email(
            email_data, index, total_emails, credentials, 
            max_retries, login_error_message, logger
        )
        
        # LOG DETALHADO: Resultado do processamento
        if success:
            print(f"[FILA] [OK] Email {index}/{total_emails} PROCESSADO COM SUCESSO")
            logger.info(f"[FILA {index}/{total_emails}] Email processado com sucesso: {numero_sinistro}")
        else:
            print(f"[FILA] [ERRO] Email {index}/{total_emails} FALHA NO PROCESSAMENTO")
            logger.warning(f"[FILA {index}/{total_emails}] Falha no processamento: {numero_sinistro}")
        
        # CONTROLE DE DUPLICATAS DESABILITADO - não marcar mais como processado
        print(f"[FILA] [INFO] Email não será marcado como processado - duplicatas permitidas")
        logger.info(f"[FILA {index}/{total_emails}] Email não marcado como processado - permite reprocessamento")
        
        # Adicionar a lista apropriada
        process_data = f"{subject} - {numero_sinistro}"
        if success:
            processed_list.append(process_data)
        else:
            non_processed_list.append(process_data)
        
        # LOG DETALHADO: Status atual da fila
        processados_ate_agora = len(processed_list)
        falharam_ate_agora = len(non_processed_list)
        restantes = total_emails - index
        
        print(f"[FILA] STATUS ATUAL:")
        print(f"[FILA] - Processados com sucesso: {processados_ate_agora}")
        print(f"[FILA] - Falharam: {falharam_ate_agora}")
        print(f"[FILA] - Restantes na fila: {restantes}")
        
        if restantes > 0:
            print(f"[FILA] Proximo: Email {index + 1}/{total_emails}")
        else:
            print(f"[FILA] [SUCESSO] TODOS OS EMAILS DA FILA FORAM PROCESSADOS!")
        
        print("=" * 60)
    
    # LOG DETALHADO: Resumo final da fila
    print("\n" + "=" * 80)
    print(f"[FILA] PROCESSAMENTO DA FILA CONCLUÍDO")
    print(f"[FILA] Total processado: {total_emails} emails")
    print(f"[FILA] Sucessos: {len(processed_list)}")
    print(f"[FILA] Falhas: {len(non_processed_list)}")
    print(f"[FILA] Taxa de sucesso: {(len(processed_list)/total_emails)*100:.1f}%")
    print("=" * 80)
    
    logger.info(f"Fila processada: {len(processed_list)} sucessos, {len(non_processed_list)} falhas de {total_emails} total")


def _process_single_email(email_data, index, total_emails, credentials, 
                         max_retries, login_error_message, logger):
    """
    Processa um unico email com retry logic.
    
    Args:
        email_data: Dados do email a ser processado
        index: Índice atual do email
        total_emails: Total de emails a processar
        credentials: Credenciais de acesso
        max_retries: Numero máximo de tentativas
        login_error_message: Mensagem de erro de login
        logger: Logger do sistema
        
    Returns:
        bool: True se processado com sucesso, False caso contrário
    """
    numero_sinistro, subject, subject_email, content_email, to_address, cc_addresses, from_address, sent_time = email_data
    start_time = datetime.now()
    
    # LOG DETALHADO: Inicio do processamento individual
    print(f"\n[EMAIL {index}/{total_emails}] [PROC] INICIANDO PROCESSAMENTO INDIVIDUAL")
    print(f"[EMAIL {index}/{total_emails}] Sinistro: {numero_sinistro}")
    print(f"[EMAIL {index}/{total_emails}] Hora de inicio: {start_time.strftime('%H:%M:%S')}")
    logger.info(f"[EMAIL {index}/{total_emails}] Iniciando processamento individual do sinistro {numero_sinistro}")
    
    # PASSO 1: Verificar se o numero do sinistro e válido (6 digitos comecando com 6)
    print(f"[EMAIL {index}/{total_emails}] PASSO 1: Validando numero do sinistro...")
    try:
        from services.email_service import _is_valid_sinistro_number
        if not numero_sinistro or not _is_valid_sinistro_number(numero_sinistro):
            print(f"[EMAIL {index}/{total_emails}] [ERRO] PASSO 1 FALHOU: Numero do sinistro inválido")
            print(f"[EMAIL {index}/{total_emails}] Numero recebido: '{numero_sinistro}'")
            print(f"[EMAIL {index}/{total_emails}] Deve ter 6 digitos e comecar com 6")
            logger.info(f"[EMAIL {index}/{total_emails}] Sinistro {numero_sinistro} filtrado: numero inválido (deve ter 6 digitos e comecar com 6)")
            return False
        else:
            print(f"[EMAIL {index}/{total_emails}] [OK] PASSO 1 CONCLUÍDO: Numero do sinistro válido")
            logger.info(f"[EMAIL {index}/{total_emails}] Validacao do numero do sinistro aprovada: {numero_sinistro}")
    except Exception as validation_error:
        print(f"[EMAIL {index}/{total_emails}] [AVISO] PASSO 1 ERRO: Falha na validacao - {validation_error}")
        logger.warning(f"[EMAIL {index}/{total_emails}] Erro ao validar numero do sinistro {numero_sinistro}: {validation_error}")
    
    # PASSO 2: Verificar se o processo já foi marcado como encerrado
    print(f"[EMAIL {index}/{total_emails}] PASSO 2: Verificando se processo está encerrado...")
    try:
        from services.email_service import is_process_closed
        if is_process_closed(numero_sinistro):
            print(f"[EMAIL {index}/{total_emails}] [STOP] PASSO 2 BLOQUEOU: Processo já marcado como encerrado")
            print(f"[EMAIL {index}/{total_emails}] Pulando todas as tentativas para evitar reprocessamento")
            logger.info(f"[EMAIL {index}/{total_emails}] Sinistro {numero_sinistro} já marcado como encerrado - evitando reprocessamento desnecessário")
            return False
        else:
            print(f"[EMAIL {index}/{total_emails}] [OK] PASSO 2 CONCLUÍDO: Processo nao está encerrado, pode prosseguir")
            logger.info(f"[EMAIL {index}/{total_emails}] Processo {numero_sinistro} liberado para processamento")
    except Exception as check_error:
        print(f"[EMAIL {index}/{total_emails}] [AVISO] PASSO 2 ERRO: Falha na verificacao - {check_error}")
        logger.warning(f"[EMAIL {index}/{total_emails}] Erro ao verificar se processo {numero_sinistro} está encerrado: {check_error}")
    
    # PASSO 3: Loop de tentativas
    print(f"[EMAIL {index}/{total_emails}] PASSO 3: Iniciando loop de tentativas (máximo: {max_retries})")
    
    for attempt in range(1, max_retries + 1):
        driver = None
        navigation_result = None
        
        try:
            # LOG DETALHADO: Inicio da tentativa
            print(f"\n[EMAIL {index}/{total_emails}] TENTATIVA {attempt}/{max_retries}")
            print(f"[EMAIL {index}/{total_emails}] Sinistro: {numero_sinistro}")
            
            # SUB-PASSO 3.1: Configurar navegador
            print(f"[EMAIL {index}/{total_emails}] SUB-PASSO 3.{attempt}.1: Configurando navegador...")
            logger.info(f"[EMAIL {index}/{total_emails}] Tentativa {attempt}: Configurando WebDriver")
            driver = setup_webdriver()
            print(f"[EMAIL {index}/{total_emails}] [OK] SUB-PASSO 3.{attempt}.1 CONCLUÍDO: Navegador configurado")
            
            # LOG de inicio do processamento
            log_and_print(
                f"-----------Inicio Processamento {subject} do sinistro {numero_sinistro} "
                f"({index}/{total_emails}) - Tentativa {attempt}...---------------", 
                logger
            )
            
            # SUB-PASSO 3.2: Realizar login
            print(f"[EMAIL {index}/{total_emails}] SUB-PASSO 3.{attempt}.2: Realizando login no sistema...")
            print(f"[EMAIL {index}/{total_emails}] URL: {credentials['url']}")
            print(f"[EMAIL {index}/{total_emails}] Usuário: {credentials['username']}")
            logger.info(f"[EMAIL {index}/{total_emails}] Tentativa {attempt}: Realizando login")
            
            login_manager = AonLoginManager(driver, logger)
            if not login_manager.login(credentials['url'], credentials['username'], credentials['password']):
                raise Exception("Falha no login - credenciais ou conectividade")
            
            print(f"[EMAIL {index}/{total_emails}] [OK] SUB-PASSO 3.{attempt}.2 CONCLUÍDO: Login realizado com sucesso")
            logger.info(f"[EMAIL {index}/{total_emails}] Tentativa {attempt}: Login bem-sucedido")

            # SUB-PASSO 3.3: Navegar e processar
            print(f"[EMAIL {index}/{total_emails}] SUB-PASSO 3.{attempt}.3: Executando navegacao e acoes...")
            print(f"[EMAIL {index}/{total_emails}] Preparando dados para navegacao:")
            print(f"[EMAIL {index}/{total_emails}] - Sinistro: {numero_sinistro}")
            print(f"[EMAIL {index}/{total_emails}] - Destinatário: {to_address}")
            print(f"[EMAIL {index}/{total_emails}] - CC: {cc_addresses}")
            logger.info(f"[EMAIL {index}/{total_emails}] Tentativa {attempt}: Iniciando navegacao e processamento")
            
            navigation_manager = NavigationManager(driver, logger)
            
            navigation_result = navigation_manager.navigate_and_perform_actions(
                subject, numero_sinistro, content_email, 
                to_address, cc_addresses, from_address, sent_time
            )
            
            # LOG DETALHADO: Resultado da navegacao
            if navigation_result == 1:  # Sucesso
                print(f"[EMAIL {index}/{total_emails}] [OK] SUB-PASSO 3.{attempt}.3 CONCLUÍDO: Navegacao bem-sucedida")
                logger.info(f"[EMAIL {index}/{total_emails}] Tentativa {attempt}: Navegacao bem-sucedida")
                
                # SUB-PASSO 3.4: Finalizacao com sucesso
                end_time = datetime.now()
                duration = end_time - start_time
                
                print(f"[EMAIL {index}/{total_emails}] SUB-PASSO 3.{attempt}.4: Enviando email de confirmacao...")
                
                # Enviar email de confirmacao
                send_claim_email(
                    numero_sinistro=numero_sinistro,
                    solicitacao=subject,
                    start_time=start_time,
                    end_time=end_time,
                    duration=str(timedelta(seconds=duration.total_seconds())).split('.')[0],
                    status="Sucesso"
                )
                
                print(f"[EMAIL {index}/{total_emails}] [OK] PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
                print(f"[EMAIL {index}/{total_emails}] Tempo total: {duration}")
                logger.info(f"[EMAIL {index}/{total_emails}] Processamento concluido com sucesso em {duration}")
                return True
                
            elif navigation_result == -1:  # Processo encerrado MAS com histórico atualizado
                print(f"[EMAIL {index}/{total_emails}] [SUCCESS_CLOSED] SUB-PASSO 3.{attempt}.3: Processo encerrado mas histórico atualizado")
                print(f"[EMAIL {index}/{total_emails}] SUCESSO: Email registrado no histórico do processo encerrado")
                logger.info(f"[EMAIL {index}/{total_emails}] Processo {numero_sinistro} encerrado - histórico atualizado com sucesso")
                
                # SUB-PASSO 3.4: Finalizacao com sucesso (processo encerrado)
                end_time = datetime.now()
                duration = end_time - start_time
                
                print(f"[EMAIL {index}/{total_emails}] SUB-PASSO 3.{attempt}.4: Enviando email de confirmacao (processo encerrado)...")
                
                # Enviar email de confirmacao específico para processo encerrado
                send_claim_email(
                    numero_sinistro=numero_sinistro,
                    solicitacao=subject,
                    start_time=start_time,
                    end_time=end_time,
                    duration=str(timedelta(seconds=duration.total_seconds())).split('.')[0],
                    status="Sucesso - Processo Encerrado (Histórico Atualizado)"
                )
                
                print(f"[EMAIL {index}/{total_emails}] [OK] PROCESSAMENTO CONCLUÍDO - PROCESSO ENCERRADO!")
                print(f"[EMAIL {index}/{total_emails}] Histórico atualizado com sucesso, telefone não editado")
                print(f"[EMAIL {index}/{total_emails}] Tempo total: {duration}")
                logger.info(f"[EMAIL {index}/{total_emails}] Processo encerrado processado com sucesso em {duration}")
                return True  # Retorna True porque o histórico foi atualizado com sucesso
                return False
                
            else:  # Falha generica (navigation_result == 0)
                print(f"[EMAIL {index}/{total_emails}] [ERRO] SUB-PASSO 3.{attempt}.3: Falha na navegacao")
                raise Exception("Falha na navegacao - tentativa nao bem-sucedida")
                
        except Exception as e:
            error_message = str(e)
            
            print(f"[EMAIL {index}/{total_emails}] [ERRO] TENTATIVA {attempt}/{max_retries} FALHOU: {error_message}")
            log_and_print(
                f"[EMAIL {index}/{total_emails}] Erro ao processar o sinistro {numero_sinistro}: {error_message}. "
                f"Tentativa {attempt} de {max_retries}.", 
                logger, 
                level="error"
            )
            
            if attempt == max_retries:
                print(f"[EMAIL {index}/{total_emails}] [ERRO] TODAS AS TENTATIVAS ESGOTADAS")
                print(f"[EMAIL {index}/{total_emails}] SUB-PASSO FINAL: Enviando email de erro...")
                
                # Última tentativa falhou
                end_time = datetime.now()
                duration = end_time - start_time
                
                # Enviar email de erro
                send_claim_email(
                    numero_sinistro=numero_sinistro,
                    solicitacao=subject,
                    start_time=start_time,
                    end_time=end_time,
                    duration=str(timedelta(seconds=duration.total_seconds())).split('.')[0],
                    status="Erro"
                )
                
                print(f"[EMAIL {index}/{total_emails}] [ERRO] PROCESSAMENTO CONCLUÍDO COM FALHA")
                print(f"[EMAIL {index}/{total_emails}] Tempo total: {duration}")
                logger.error(f"[EMAIL {index}/{total_emails}] Sinistro {numero_sinistro} nao pôde ser processado apos {max_retries} tentativas em {duration}")
            else:
                print(f"[EMAIL {index}/{total_emails}] [PROC] Preparando proxima tentativa ({attempt + 1}/{max_retries})...")
        
        finally:
            if driver:
                try:
                    print(f"[EMAIL {index}/{total_emails}] [CONFIG] Fechando navegador da tentativa {attempt}...")
                    driver.quit()
                    print(f"[EMAIL {index}/{total_emails}] [OK] Navegador fechado com sucesso")
                except Exception as close_error:
                    print(f"[EMAIL {index}/{total_emails}] [AVISO] Erro ao fechar navegador: {close_error}")

    print(f"[EMAIL {index}/{total_emails}] [ERRO] PROCESSAMENTO INDIVIDUAL FINALIZADO SEM SUCESSO")
    logger.warning(f"[EMAIL {index}/{total_emails}] Processamento do sinistro {numero_sinistro} finalizado sem sucesso")
    return False


def _generate_final_report(processed_list, non_processed_list, logger, 
                          execution_start_time, execution_end_time):
    """
    Gera e envia o relatorio final consolidado do processamento.
    
    Args:
        processed_list: Lista de sinistros processados com sucesso
        non_processed_list: Lista de sinistros com falha
        logger: Logger do sistema
        execution_start_time: Horário de inicio da execucao
        execution_end_time: Horário de fim da execucao
    """
    # LOG DETALHADO: Inicio da geracao de relatorios
    print("[RELATÓRIOS] [RELAT] INICIANDO GERAÇÃO DE RELATÓRIOS CONSOLIDADOS")
    print("-" * 60)
    
    # Calcular estatisticas de execucao
    total_emails = len(processed_list) + len(non_processed_list)
    duration = execution_end_time - execution_start_time
    duration_str = str(duration).split('.')[0]
    success_rate = (len(processed_list) / total_emails * 100) if total_emails > 0 else 0
    
    print(f"[RELATÓRIOS] Total de emails processados: {total_emails}")
    print(f"[RELATÓRIOS] Sucessos: {len(processed_list)}")
    print(f"[RELATÓRIOS] Falhas: {len(non_processed_list)}")
    print(f"[RELATÓRIOS] Taxa de sucesso: {success_rate:.1f}%")
    print(f"[RELATÓRIOS] Duracao da execucao: {duration_str}")
    
    try:
        # Importar funcoes do novo sistema de relatorio
        from services.email_service import (
            send_consolidated_final_report, 
            save_execution_report,
            count_closed_processes
        )
        
        # PASSO 1: Enviar relatorio consolidado por email
        print("[RELATÓRIOS] PASSO 1: Enviando relatorio consolidado por email...")
        logger.info("Iniciando envio de relatorio consolidado por email")
        
        email_success = send_consolidated_final_report(
            processed_list, non_processed_list, 
            execution_start_time, execution_end_time
        )
        
        if email_success:
            print("[RELATÓRIOS] [OK] PASSO 1 CONCLUÍDO: Relatorio enviado por email")
            logger.info("Relatorio consolidado enviado por email com sucesso")
        else:
            print("[RELATÓRIOS] [AVISO] PASSO 1 FALHA: Erro no envio do relatorio por email")
            logger.warning("Falha no envio do relatorio consolidado por email")
        
        # PASSO 2: Salvar relatorio em arquivo JSON
        print("[RELATÓRIOS] PASSO 2: Salvando relatorio em arquivo JSON...")
        logger.info("Salvando relatorio em arquivo JSON")
        
        report_file = save_execution_report(
            {}, processed_list, non_processed_list
        )
        
        if report_file:
            print(f"[RELATÓRIOS] [OK] PASSO 2 CONCLUÍDO: Arquivo salvo em {report_file}")
            logger.info(f"Relatorio JSON salvo: {report_file}")
        else:
            print("[RELATÓRIOS] [AVISO] PASSO 2 FALHA: Erro ao salvar arquivo JSON")
            logger.warning("Falha ao salvar relatorio JSON")
        
        # PASSO 3: Obter estatisticas de processos encerrados
        print("[RELATÓRIOS] PASSO 3: Obtendo estatisticas de processos encerrados...")
        try:
            total_encerrados = count_closed_processes()
            print(f"[RELATÓRIOS] [OK] PASSO 3 CONCLUÍDO: {total_encerrados} processos marcados como encerrados")
            logger.info(f"Estatisticas: {total_encerrados} processos marcados como encerrados")
        except Exception as e:
            print(f"[RELATÓRIOS] [AVISO] PASSO 3 ERRO: {e}")
            logger.warning(f"Erro ao obter estatisticas de processos encerrados: {e}")
        
        # PASSO 4: Enviar relatorio simples (compatibilidade)
        print("[RELATÓRIOS] PASSO 4: Enviando resumo adicional (compatibilidade)...")
        logger.info("Enviando relatorio simples adicional")
        
        send_summary_email(processed_list, non_processed_list)
        print("[RELATÓRIOS] [OK] PASSO 4 CONCLUÍDO: Resumo adicional enviado")
        logger.info("Relatorio simples adicional enviado")
        
    except Exception as e:
        print(f"[RELATÓRIOS] [ERRO] ERRO NA GERAÇÃO DE RELATÓRIOS: {e}")
        logger.error(f"Erro ao gerar relatorio consolidado: {e}")
        
        # FALLBACK: Relatorio simples
        print("[RELATÓRIOS] FALLBACK: Tentando enviar relatorio simples...")
        try:
            send_summary_email(processed_list, non_processed_list)
            print("[RELATÓRIOS] [OK] FALLBACK CONCLUÍDO: Relatorio simples enviado")
            logger.info("Relatorio simples enviado como fallback")
        except Exception as fallback_error:
            print(f"[RELATÓRIOS] [ERRO] FALLBACK FALHOU: {fallback_error}")
            logger.error(f"Erro no fallback do relatorio: {fallback_error}")
    
    # RESUMO FINAL NO CONSOLE
    print("\n" + "=" * 80)
    print(" " * 25 + "[RELAT] RESUMO FINAL DA EXECUÇÃO [RELAT]")
    print("=" * 80)
    print(f"[RESUMO] Horário de inicio: {execution_start_time.strftime('%d/%m/%Y as %H:%M:%S')}")
    print(f"[RESUMO] Horário de termino: {execution_end_time.strftime('%d/%m/%Y as %H:%M:%S')}")
    print(f"[RESUMO] Duracao total: {duration_str}")
    print(f"[RESUMO] Total de emails: {total_emails}")
    print(f"[RESUMO] [OK] Processados com sucesso: {len(processed_list)}")
    print(f"[RESUMO] [ERRO] Falharam no processamento: {len(non_processed_list)}")
    print(f"[RESUMO] [TAXA] Taxa de sucesso: {success_rate:.1f}%")
    print("=" * 80)
    
    # Listar sucessos (limitado a 10)
    if processed_list:
        print("[RESUMO] [META] SUCESSOS:")
        for i, item in enumerate(processed_list[:10], 1):
            print(f"[RESUMO] {i}. {item}")
        if len(processed_list) > 10:
            print(f"[RESUMO] ... e mais {len(processed_list) - 10} sucessos")
    
    # Listar falhas (limitado a 10)
    if non_processed_list:
        print("\n[RESUMO] [AVISO] FALHAS:")
        for i, item in enumerate(non_processed_list[:10], 1):
            print(f"[RESUMO] {i}. {item}")
        if len(non_processed_list) > 10:
            print(f"[RESUMO] ... e mais {len(non_processed_list) - 10} falhas")
    
    print("=" * 80)
    print("[RESUMO] [SUCESSO] RELATÓRIOS FINALIZADOS COM SUCESSO!")
    print("=" * 80)
    
    logger.info(f"Relatorios finalizados - Sucessos: {len(processed_list)}, Falhas: {len(non_processed_list)}, Duracao: {duration_str}, Taxa de sucesso: {success_rate:.1f}%")


if __name__ == "__main__":
    main()
