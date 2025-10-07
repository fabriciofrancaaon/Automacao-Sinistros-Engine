# -*- coding: utf-8 -*-
"""
Email Service Module

Este módulo fornece funcionalidades para envio e gerenciamento de emails
através do Outlook, incluindo processamento de sinistros e relatórios.

Funcionalidades principais:
- Envio de emails genéricos
- Processamento de emails de sinistros
- Busca emails das últimas 24h sem repetição
- Controle anti-duplicação com persistência
- Recuperação de informações de emails
- Formatação de relatórios tabulares
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Set

import win32com.client
import pythoncom
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Constantes
DEFAULT_EMAIL_RECIPIENT = "fabricio.franca@aon.com"
OUTLOOK_INBOX_FOLDER = 6
OUTLOOK_SENT_ITEMS_FOLDER = 5
SORT_BY_RECEIVED_TIME = "[ReceivedTime]"
SORT_BY_SENT_TIME = "[SentOn]"
DAYS_LOOKBACK = 7

# Arquivo para controle de emails processados
PROCESSED_EMAILS_FILE = "data/processed/emails_processados.json"

# Arquivo para controle de processos encerrados
CLOSED_PROCESSES_FILE = "data/processed/processos_encerrados.json"


class EmailServiceError(Exception):
    """Exceção customizada para erros do serviço de email."""
    pass


def _ensure_com_initialized():
    """Garante que o COM está inicializado para uso do Outlook"""
    try:
        pythoncom.CoInitialize()
    except:
        # Se já estiver inicializado, ignora o erro
        pass


def _get_real_sender_email(message):
    """
    Tenta extrair o nome e email real do remetente, evitando códigos Exchange.
    
    Args:
        message: Objeto de email do Outlook
        
    Returns:
        str: Nome e email do remetente no formato "Nome <email@domain.com>" ou fallback
    """
    try:
        # Coletar informações disponíveis
        sender_email = getattr(message, 'SenderEmailAddress', '')
        sender_name = None
        real_email = None
        
        # Tentar obter nome do remetente
        try:
            if hasattr(message, 'SenderName') and message.SenderName:
                sender_name = message.SenderName.strip()
            elif hasattr(message, 'Sender') and message.Sender and hasattr(message.Sender, 'Name'):
                sender_name = message.Sender.Name.strip()
        except:
            pass
        
        # Primeira tentativa: SenderEmailAddress direto
        if '@' in sender_email and not sender_email.startswith('/'):
            real_email = sender_email
        
        # Segunda tentativa: através do objeto Sender
        if not real_email and hasattr(message, 'Sender') and message.Sender:
            sender = message.Sender
            if hasattr(sender, 'Address') and sender.Address:
                sender_address = sender.Address
                if '@' in sender_address and not sender_address.startswith('/'):
                    real_email = sender_address
        
        # Terceira tentativa: SenderName (se contém email)
        if not real_email and sender_name and '@' in sender_name:
            real_email = sender_name
            sender_name = None  # Reset para não duplicar
        
        # Quarta tentativa: através do objeto Author
        if not real_email and hasattr(message, 'Author') and message.Author:
            author = message.Author
            if '@' in author:
                real_email = author
        
        # Quinta tentativa: através de Recipients
        if not real_email:
            try:
                if hasattr(message, 'Recipients') and message.Recipients:
                    for recipient in message.Recipients:
                        if hasattr(recipient, 'Type') and recipient.Type == 1:  # olOriginator
                            if hasattr(recipient, 'Address') and recipient.Address:
                                if '@' in recipient.Address and not recipient.Address.startswith('/'):
                                    real_email = recipient.Address
                                    break
            except:
                pass
        
        # Sexta tentativa: ReplyRecipients
        if not real_email:
            try:
                if hasattr(message, 'ReplyRecipients') and message.ReplyRecipients:
                    for reply_recipient in message.ReplyRecipients:
                        if hasattr(reply_recipient, 'Address') and reply_recipient.Address:
                            if '@' in reply_recipient.Address and not reply_recipient.Address.startswith('/'):
                                real_email = reply_recipient.Address
                                break
            except:
                pass
        
        # Sétima tentativa: propriedades MAPI
        if not real_email:
            try:
                # PR_SENDER_EMAIL_ADDRESS
                sender_mapi = message.PropertyAccessor.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x0C1F001E")
                if sender_mapi and '@' in sender_mapi and not sender_mapi.startswith('/'):
                    real_email = sender_mapi
            except:
                pass
        
        # Oitava tentativa: PR_SENT_REPRESENTING_EMAIL_ADDRESS
        if not real_email:
            try:
                repr_email = message.PropertyAccessor.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x0065001E")
                if repr_email and '@' in repr_email and not repr_email.startswith('/'):
                    real_email = repr_email
            except:
                pass
        
        # Tentar extrair email de domínios conhecidos através do nome
        if not real_email and sender_name:
            # Tentar construir email baseado no nome para domínios AON
            name_lower = sender_name.lower().replace(' ', '.')
            potential_emails = [
                f"{name_lower}@aon.com",
                f"{name_lower}@aon.com.br"
            ]
            
            # Para fins de log, usar o primeiro potencial
            real_email = potential_emails[0]
        
        # Construir resultado final
        if real_email and sender_name:
            # Limpar nome (remover caracteres especiais se necessário)
            clean_name = sender_name.replace('"', '').replace("'", "").strip()
            return f"{clean_name} <{real_email}>"
        
        elif real_email:
            # Só temos email
            return real_email
        
        elif sender_name and sender_name.strip() and not sender_name.startswith('/'):
            # Só temos nome - tentar construir email AON
            clean_name = sender_name.replace('"', '').replace("'", "").strip()
            name_parts = clean_name.lower().split()
            if len(name_parts) >= 2:
                email_guess = f"{name_parts[0]}.{name_parts[-1]}@aon.com"
                return f"{clean_name} <{email_guess}>"
            else:
                return f"{clean_name} [SEM_EMAIL]"
        
        # Último fallback: código com identificação 
        if sender_email and sender_email.startswith('/'):
            return f"[CÓDIGO_EXCHANGE] {sender_email[:50]}..."
        
        return sender_email or 'Remetente Desconhecido'
        
    except Exception as e:
        logging.debug(f"Erro ao extrair email do remetente: {e}")
        return getattr(message, 'SenderEmailAddress', 'Remetente Desconhecido')


def send_generic_email(to: str, subject: str, body: str, is_html: bool = False) -> bool:
    """
    Envia um email genérico usando o Outlook.
    
    Args:
        to (str): Endereço de email do destinatário
        subject (str): Assunto do email
        body (str): Corpo do email
        is_html (bool): Se True, envia como HTML, senão como texto simples
        
    Returns:
        bool: True se o email foi enviado com sucesso, False caso contrário
        
    Raises:
        EmailServiceError: Se os parâmetros obrigatórios não forem fornecidos
    """
    try:
        logging.info("Iniciando envio de email genérico...")
        
        # Validação de parâmetros
        if not all([to, subject, body]):
            raise EmailServiceError("Destinatário, assunto ou corpo do email não foram fornecidos.")

        # Inicializar COM e configurar Outlook
        _ensure_com_initialized()
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        mail.To = to
        mail.Subject = subject
        
        if is_html:
            mail.HTMLBody = body
        else:
            mail.Body = body

        logging.info(f"Enviando email para: {to}, Assunto: {subject}")
        mail.Send()
        logging.info("Email enviado para a caixa de saída.")

        # Tentativa de envio imediato
        _force_immediate_send(outlook)
        
        print("Email enviado com sucesso.")
        return True
        
    except Exception as e:
        logging.error(f"Erro ao enviar email: {e}")
        print(f"Erro ao enviar email: {e}")
        return False


def _force_immediate_send(outlook) -> None:
    """
    Força o envio imediato de emails na caixa de saída.
    
    Args:
        outlook: Instância do Outlook Application
    """
    try:
        logging.info("Forçando envio imediato com SendAndReceive...")
        session = outlook.GetNamespace("MAPI")
        session.SendAndReceive(True)
        logging.info("Envio forçado concluído.")
    except Exception as e:
        logging.warning(f"Falha ao forçar envio imediato: {e}")


def delete_sent_email(subject: str, body_identifier: str) -> bool:
    """
    Exclui um email enviado da pasta de enviados baseado no assunto e identificador.
    
    Args:
        subject (str): Assunto do email a ser excluído
        body_identifier (str): Identificador único no corpo do email
        
    Returns:
        bool: True se o email foi encontrado e excluído, False caso contrário
    """
    try:
        logging.info("Tentando excluir email enviado...")
        
        _ensure_com_initialized()
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        sent_items = outlook.GetDefaultFolder(OUTLOOK_SENT_ITEMS_FOLDER)
        
        for item in sent_items.Items:
            if item.Subject == subject and body_identifier in item.Body:
                logging.info(f"Email encontrado para exclusão: {item.Subject}")
                item.Delete()
                logging.info(f"Email excluído da pasta de enviados: {subject}")
                print(f"Email excluído da pasta de enviados: {subject}")
                return True
                
        logging.warning(f"Nenhum email encontrado para exclusão com o assunto: {subject}")
        print(f"Nenhum email encontrado para exclusão com o assunto: {subject}")
        return False
        
    except Exception as e:
        logging.error(f"Falha ao excluir email da pasta de enviados: {e}")
        print(f"Falha ao excluir email da pasta de enviados: {e}")
        return False


def send_claim_email(numero_sinistro: str, solicitacao: str, start_time: str, 
                    end_time: str, duration: str, status: str) -> bool:
    """
    Envia um email com os detalhes de processamento de um sinistro.
    
    Args:
        numero_sinistro (str): Número do sinistro processado
        solicitacao (str): Tipo de solicitação
        start_time (str): Horário de início do processamento
        end_time (str): Horário de fim do processamento
        duration (str): Duração total do processamento
        status (str): Status final do processamento
        
    Returns:
        bool: True se o email foi enviado com sucesso, False caso contrário
        
    Raises:
        EmailServiceError: Se as configurações de email não estiverem definidas
    """
    try:
        logging.info("Iniciando envio de email para sinistro...")
        
        # Recupera configurações do ambiente
        subject = os.getenv("EMAIL_SUBJECT_PROCESSED")
        if not subject:
            raise EmailServiceError("O assunto do email não foi configurado na variável EMAIL_SUBJECT_PROCESSED.")
        
        recipient = os.getenv("EMAIL_TO_PROCESSED")
        if not recipient:
            raise EmailServiceError("O destinatário não foi configurado na variável EMAIL_TO_PROCESSED.")
        
        # Cria o corpo do email e envia
        body = _create_claim_email_body(numero_sinistro, solicitacao, start_time, 
                                       end_time, duration, status)
        
        success = send_generic_email(recipient, subject, body)
        
        if success:
            logging.info("Envio de email para sinistro concluído.")
        
        return success
        
    except Exception as e:
        logging.error(f"Erro ao enviar email para sinistro: {e}")
        print(f"Erro ao enviar email para sinistro: {e}")
        return False


def _create_claim_email_body(numero_sinistro: str, solicitacao: str, start_time: str, 
                            end_time: str, duration: str, status: str) -> str:
    """
    Cria o corpo do email com os detalhes da execução do sinistro.
    
    Args:
        numero_sinistro (str): Número do sinistro
        solicitacao (str): Tipo de solicitação
        start_time (str): Horário de início
        end_time (str): Horário de fim
        duration (str): Duração
        status (str): Status final
        
    Returns:
        str: Corpo formatado do email
    """
    return (
        f"Data: {numero_sinistro} - {solicitacao} - {start_time} - "
        f"{end_time} - {duration} - {status}"
    )


def send_summary_email(processed_list: List[str], non_processed_list: List[str]) -> bool:
    """
    Envia um email com resumo dos sinistros processados e não processados.
    
    Args:
        processed_list (List[str]): Lista de sinistros processados
        non_processed_list (List[str]): Lista de sinistros não processados
        
    Returns:
        bool: True se o email foi enviado com sucesso, False caso contrário
    """
    try:
        logging.info("Preparando resumo do processamento de sinistros...")
        
        subject = "Resumo do Processamento de Sinistros"
        
        # Prepara dados para tabelas
        processed_data = [item.split(" - ") for item in processed_list]
        non_processed_data = [item.split(" - ") for item in non_processed_list]
        
        # Cria tabelas formatadas
        headers = ["Número do Sinistro", "Assunto"]
        processed_table = _format_table(processed_data, headers)
        non_processed_table = _format_table(non_processed_data, headers)
        
        # Monta corpo do email
        body = _create_summary_email_body(processed_table, non_processed_table)
        
        # Envia email
        recipient = os.getenv("EMAIL_TO_PROCESSED", DEFAULT_EMAIL_RECIPIENT)
        success = send_generic_email(recipient, subject, body)
        
        if success:
            logging.info("Resumo enviado com sucesso.")
            
        return success
        
    except Exception as e:
        logging.error(f"Erro ao enviar email de resumo: {e}")
        return False


def _create_summary_email_body(processed_table: str, non_processed_table: str) -> str:
    """
    Cria o corpo do email de resumo.
    
    Args:
        processed_table (str): Tabela formatada de sinistros processados
        non_processed_table (str): Tabela formatada de sinistros não processados
        
    Returns:
        str: Corpo formatado do email de resumo
    """
    return (
        "Resumo do processamento de sinistros:\n\n"
        "Sinistros Processados:\n"
        f"{processed_table}\n\n"
        "Sinistros Não Processados:\n"
        f"{non_processed_table}"
    )


def _format_table(data: List[List[str]], headers: List[str]) -> str:
    """
    Formata uma tabela manualmente com alinhamento.
    
    Args:
        data (List[List[str]]): Dados da tabela
        headers (List[str]): Cabeçalhos da tabela
        
    Returns:
        str: Tabela formatada como string
    """
    if not data:
        return "Nenhum dado disponível"
    
    # Determina o tamanho máximo de cada coluna
    column_widths = [max(len(str(item)) for item in col) 
                    for col in zip(headers, *data)]
    
    # Cria o cabeçalho
    header = " | ".join(f"{header:<{column_widths[i]}}" 
                       for i, header in enumerate(headers))
    separator = "-+-".join("-" * width for width in column_widths)
    
    # Cria as linhas da tabela
    rows = "\n".join(" | ".join(f"{str(item):<{column_widths[i]}}" 
                                for i, item in enumerate(row)) 
                    for row in data)
    
    return f"{header}\n{separator}\n{rows}"


def get_outlook_email_info() -> List[Tuple]:
    """
    Recupera informações dos emails do Outlook dos últimos 7 dias da caixa de enviados.
    
    Filtra emails baseado nos assuntos configurados na variável de ambiente
    EMAIL_SUBJECT_LIST e retorna informações detalhadas de cada email.
    
    Returns:
        List[Tuple]: Lista de tuplas contendo informações dos emails:
                    (numero_sinistro, subject, full_subject, body, to, cc, sender)
    """
    try:
        logging.info("Recuperando informações de emails do Outlook da caixa de enviados...")
        
        # Inicializar COM e configurar conexão com Outlook
        _ensure_com_initialized()
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        sent_items = outlook.GetDefaultFolder(OUTLOOK_SENT_ITEMS_FOLDER)
        
        # Para caixa de enviados, usa a pasta principal ao invés de subpasta
        # folder_name = os.getenv("EMAIL_FOLDER", "ALARME AUTOMATICO")  # Comentado para caixa enviados
        # target_folder = sent_items.Folders[folder_name]  # Comentado para caixa enviados
        messages = sent_items.Items
        messages.Sort(SORT_BY_SENT_TIME, True)  # Ordena por data de envio
        
        # Define período de busca
        cutoff_date = _get_cutoff_date()
        
        # Recupera lista de assuntos a filtrar
        email_subject_list = _get_email_subject_list()
        if not email_subject_list:
            logging.warning("Lista de assuntos de email está vazia.")
            return []
        
        # Processa emails
        email_info_list = []
        for message in messages:
            if _is_message_too_old_sent(message, cutoff_date):
                break
                
            matching_subject = _find_matching_subject(message.Subject, email_subject_list)
            if matching_subject:
                email_info = _extract_email_info_sent(message, matching_subject)
                email_info_list.append(email_info)
        
        logging.info(f"Encontrados {len(email_info_list)} emails relevantes na caixa de enviados.")
        return email_info_list
        
    except Exception as e:
        logging.error(f"Erro ao recuperar informações de emails: {e}")
        return []


def _get_cutoff_date() -> datetime:
    """
    Calcula a data limite para busca de emails (últimos 7 dias).
    
    Returns:
        datetime: Data limite com fuso horário local
    """
    local_timezone = datetime.now().astimezone().tzinfo
    cutoff_date = (datetime.now() - timedelta(days=DAYS_LOOKBACK))
    return cutoff_date.replace(tzinfo=local_timezone)


def _get_email_subject_list() -> List[str]:
    """
    Recupera a lista de assuntos de email da variável de ambiente.
    
    Returns:
        List[str]: Lista de assuntos para filtrar emails
    """
    subject_list = os.getenv("EMAIL_SUBJECT_LIST", "").split(",")
    return [subject.strip() for subject in subject_list if subject.strip()]


def _is_message_too_old(message, cutoff_date: datetime) -> bool:
    """
    Verifica se a mensagem é anterior à data limite.
    
    Args:
        message: Objeto de mensagem do Outlook
        cutoff_date (datetime): Data limite para busca
        
    Returns:
        bool: True se a mensagem é muito antiga, False caso contrário
    """
    received_time = message.ReceivedTime
    
    # Garante que received_time seja offset-aware
    if received_time.tzinfo is None:
        local_timezone = datetime.now().astimezone().tzinfo
        received_time = received_time.replace(tzinfo=local_timezone)
    
    return received_time < cutoff_date


def _is_message_too_old_sent(message, cutoff_date: datetime) -> bool:
    """
    Verifica se a mensagem enviada é anterior à data limite.
    
    Args:
        message: Objeto de mensagem do Outlook
        cutoff_date (datetime): Data limite para busca
        
    Returns:
        bool: True se a mensagem é muito antiga, False caso contrário
    """
    sent_time = getattr(message, 'SentOn', None)
    
    if sent_time is None:
        return True  # Se não tem data de envio, considera como antiga
    
    # Garante que sent_time seja offset-aware
    if sent_time.tzinfo is None:
        local_timezone = datetime.now().astimezone().tzinfo
        sent_time = sent_time.replace(tzinfo=local_timezone)
    
    return sent_time < cutoff_date


def _find_matching_subject(message_subject: str, subject_list: List[str]) -> Optional[str]:
    """
    Encontra o primeiro assunto da lista que está contido no assunto da mensagem.
    
    Args:
        message_subject (str): Assunto da mensagem
        subject_list (List[str]): Lista de assuntos para verificar
        
    Returns:
        Optional[str]: Assunto correspondente ou None se não encontrado
    """
    for subject in subject_list:
        if subject in message_subject:
            return subject
    return None


def _extract_email_info(message, matching_subject: str) -> Tuple:
    """
    Extrai informações relevantes de uma mensagem de email.
    
    Args:
        message: Objeto de mensagem do Outlook
        matching_subject (str): Assunto que fez match com os filtros
        
    Returns:
        Tuple: Informações extraídas da mensagem
    """
    numero_sinistro = extract_numero_sinistro(message.Subject)
    
    return (
        numero_sinistro,
        matching_subject,
        message.Subject,
        message.Body,
        message.To,
        message.CC,
        message.SenderEmailAddress,
    )


def _extract_email_info_sent(message, matching_subject: str) -> Tuple:
    """
    Extrai informações relevantes de uma mensagem de email enviado.
    
    Args:
        message: Objeto de mensagem do Outlook (da caixa de enviados)
        matching_subject (str): Assunto que fez match com os filtros
        
    Returns:
        Tuple: Informações extraídas da mensagem
    """
    numero_sinistro = extract_numero_sinistro(message.Subject)
    
    return (
        numero_sinistro,
        matching_subject,
        message.Subject,
        message.Body,
        getattr(message, 'To', ''),
        getattr(message, 'CC', ''),
        getattr(message, 'SenderEmailAddress', ''),
    )


def extract_numero_sinistro(subject: str) -> Optional[str]:
    """
    Extrai o número do sinistro do assunto do email seguindo regras específicas.
    
    REGRAS DE VALIDAÇÃO:
    - Deve ter EXATAMENTE 6 dígitos
    - Deve começar com 6 (primeiro dígito)
    - Exemplos válidos: 612345, 654321, 689012
    - Exemplos inválidos: 12345 (5 dígitos), 1234567 (7 dígitos), 123456 (começa com 1), 543210 (começa com 5)
    
    Padrões de busca no assunto:
    - 6XXXXX (sequência de exatamente 6 dígitos começando com 6)
    - AON 6XXXXX, Sinistro: 6XXXXX, SINI 6XXXXX
    - Qualquer contexto com 6 dígitos consecutivos válidos
    
    Args:
        subject (str): Assunto do email
        
    Returns:
        Optional[str]: Número do sinistro válido ou None se não encontrado
    """
    import re
    
    try:
        subject = subject.upper()
        logging.debug(f"🔍 Buscando número de sinistro em: {subject}")
        
        # Padrão: Exatamente 6 dígitos consecutivos com word boundaries
        six_digit_matches = re.findall(r'\b(\d{6})\b', subject)
        
        # Validar cada número de 6 dígitos encontrado
        for numero in six_digit_matches:
            if _is_valid_sinistro_number(numero):
                logging.info(f"Número de sinistro VÁLIDO encontrado: {numero} no assunto: {subject}")
                return numero
            else:
                logging.debug(f"Número {numero} inválido (deve ter 6 dígitos e começar com 6)")
        
        # Se não encontrou números válidos de 6 dígitos isolados, 
        # procura por 6 dígitos válidos em sequências maiores
        all_numbers = re.findall(r'\d+', subject)
        for number in all_numbers:
            if len(number) >= 6:
                # Tenta extrair 6 dígitos válidos da sequência
                for i in range(len(number) - 5):
                    potential_number = number[i:i+6]
                    if _is_valid_sinistro_number(potential_number):
                        logging.info(f"Número de sinistro VÁLIDO extraído: {potential_number} de {number} no assunto: {subject}")
                        return potential_number
        
        logging.debug(f"Nenhum número de sinistro válido (6 dígitos começando com 6) encontrado no assunto: {subject}")
        return None
        
    except Exception as e:
        logging.warning(f"Erro ao extrair número do sinistro do assunto '{subject}': {e}")
        return None


def _is_valid_sinistro_number(numero: str) -> bool:
    """
    Valida se um número de sinistro segue as regras de negócio.
    
    REGRAS:
    - Exatamente 6 dígitos
    - Primeiro dígito deve ser 6
    
    Args:
        numero (str): Número a ser validado
        
    Returns:
        bool: True se válido, False caso contrário
    """
    try:
        # Verificar se tem exatamente 6 dígitos
        if not numero.isdigit() or len(numero) != 6:
            return False
        
        # Verificar se o primeiro dígito é 6
        primeiro_digito = numero[0]
        if primeiro_digito != '6':
            return False
            
        return True
        
    except Exception:
        return False


def validate_sinistro_examples():
    """
    Função de teste para mostrar exemplos de números válidos e inválidos.
    Útil para debug e documentação.
    """
    exemplos_validos = [
        "612345", "654321", "689012", "600000", "699999", "666666"
    ]
    
    exemplos_invalidos = [
        "123456",  # começa com 1
        "234567",  # começa com 2  
        "412345",  # começa com 4
        "543210",  # começa com 5
        "712345",  # começa com 7
        "812345",  # começa com 8
        "12345",   # apenas 5 dígitos
        "1234567", # 7 dígitos
        "abcdef",  # não é número
        ""         # vazio
    ]
    
    print("\n📋 EXEMPLOS DE NÚMEROS DE SINISTRO:")
    print("VÁLIDOS (6 dígitos começando com 6):")
    for num in exemplos_validos:
        print(f"   {num} -> {_is_valid_sinistro_number(num)}")
    
    print("INVÁLIDOS:")
    for num in exemplos_invalidos:
        print(f"   {num} -> {_is_valid_sinistro_number(num)}")
    
    return exemplos_validos, exemplos_invalidos


def get_inbox_emails_info(days_back: int = DAYS_LOOKBACK) -> List[Tuple]:
    """
    Recupera informações dos emails da caixa de entrada (Inbox) do Outlook.
    
    Args:
        days_back (int): Número de dias anteriores para buscar emails (padrão: 7)
        
    Returns:
        List[Tuple]: Lista de tuplas contendo informações dos emails:
                    (numero_sinistro, subject, full_subject, body, to, cc, sender, received_time)
    """
    try:
        logging.info("Recuperando informações de emails da caixa de entrada...")
        
        # Inicializar COM e configurar conexão com Outlook
        _ensure_com_initialized()
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        inbox = outlook.GetDefaultFolder(6)  # Caixa de entrada (olFolderInbox = 6)
        
        messages = inbox.Items
        messages.Sort(SORT_BY_RECEIVED_TIME, True)  # Ordena por data de recebimento
        
        # Define período de busca com timezone consistente
        local_timezone = datetime.now().astimezone().tzinfo
        cutoff_date = datetime.now().replace(tzinfo=local_timezone) - timedelta(days=days_back)
        
        # Processa emails
        email_info_list = []
        for message in messages:
            # Verifica se a mensagem é muito antiga
            received_time = getattr(message, 'ReceivedTime', None)
            if received_time is None:
                continue
            
            # Normaliza timezone para comparação
            try:
                # Se received_time não tem timezone, assume local
                if received_time.tzinfo is None:
                    received_time = received_time.replace(tzinfo=local_timezone)
                # Se tem timezone diferente, converte para local
                elif received_time.tzinfo != local_timezone:
                    received_time = received_time.astimezone(local_timezone)
                
                if received_time < cutoff_date:
                    break  # Para de processar mensagens antigas
                    
            except Exception as tz_error:
                # Em caso de erro de timezone, usa comparação naive
                try:
                    cutoff_naive = cutoff_date.replace(tzinfo=None)
                    received_naive = received_time.replace(tzinfo=None) if received_time.tzinfo else received_time
                    if received_naive < cutoff_naive:
                        break
                except Exception:
                    # Se ainda falhar, pula esta verificação de data
                    pass
            
            try:
                # Extrai informações básicas
                subject = str(message.Subject)
                body = str(message.Body)
                sender = _get_real_sender_email(message)  # Usa função melhorada para extrair email
                to_addresses = str(message.To) if hasattr(message, 'To') else ""
                cc_addresses = str(message.CC) if hasattr(message, 'CC') else ""
                
                # Extrai número do sinistro do assunto
                numero_sinistro = extract_numero_sinistro(subject)
                
                # Formatar data para string
                received_time_str = received_time.strftime('%d/%m/%Y %H:%M:%S')
                
                # Adiciona à lista
                email_info = (
                    numero_sinistro,
                    subject,
                    subject,  # full_subject igual ao subject
                    body,
                    to_addresses,
                    cc_addresses,
                    sender,
                    received_time_str
                )
                
                email_info_list.append(email_info)
                logging.debug(f"Email da caixa de entrada processado: {subject}")
                
            except Exception as e:
                logging.warning(f"Erro ao processar email individual da caixa de entrada: {e}")
                continue
        
        logging.info(f"Total de emails recuperados da caixa de entrada: {len(email_info_list)}")
        return email_info_list
        
    except Exception as e:
        logging.error(f"Erro ao recuperar informações de emails da caixa de entrada: {e}")
        return []


def get_sent_emails_info(days_back: int = DAYS_LOOKBACK) -> List[Tuple]:
    """
    Recupera informações dos emails da caixa de enviados (Sent Items) do Outlook.
    
    Args:
        days_back (int): Número de dias anteriores para buscar emails (padrão: 7)
        
    Returns:
        List[Tuple]: Lista de tuplas contendo informações dos emails:
                    (numero_sinistro, subject, full_subject, body, to, cc, sender, sent_time)
    """
    try:
        logging.info("Recuperando informações de emails da caixa de enviados...")
        
        # Inicializar COM e configurar conexão com Outlook
        _ensure_com_initialized()
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        sent_items = outlook.GetDefaultFolder(OUTLOOK_SENT_ITEMS_FOLDER)  # Caixa de enviados
        
        messages = sent_items.Items
        messages.Sort(SORT_BY_SENT_TIME, True)  # Ordena por data de envio (mais recentes primeiro)
        
        # Define período de busca com timezone consistente
        local_timezone = datetime.now().astimezone().tzinfo
        cutoff_date = datetime.now().replace(tzinfo=local_timezone) - timedelta(days=days_back)
        
        # Processa emails
        email_info_list = []
        for message in messages:
            # Verifica se a mensagem é muito antiga
            sent_time = getattr(message, 'SentOn', None)
            if sent_time is None:
                continue
            
            # Normaliza timezone para comparação
            try:
                # Se sent_time não tem timezone, assume local
                if sent_time.tzinfo is None:
                    sent_time = sent_time.replace(tzinfo=local_timezone)
                # Se tem timezone diferente, converte para local
                elif sent_time.tzinfo != local_timezone:
                    sent_time = sent_time.astimezone(local_timezone)
                
                if sent_time < cutoff_date:
                    break
                    
            except Exception as tz_error:
                # Em caso de erro de timezone, usa comparação naive
                try:
                    cutoff_naive = cutoff_date.replace(tzinfo=None)
                    sent_naive = sent_time.replace(tzinfo=None) if sent_time.tzinfo else sent_time
                    if sent_naive < cutoff_naive:
                        break
                except Exception:
                    # Se ainda falhar, pula esta verificação de data
                    pass
            
            # Extrai informações do email
            numero_sinistro = extract_numero_sinistro(message.Subject)
            
            # Aplicar filtro opcional de números válidos na coleta base
            # (por padrão incluir todos para manter compatibilidade)
            should_include = True
            if numero_sinistro is None:
                logging.debug(f"Email sem número de sinistro: {message.Subject}")
            elif not _is_valid_sinistro_number(numero_sinistro):
                logging.debug(f"Email com número inválido {numero_sinistro}: {message.Subject}")
                
            email_info = (
                numero_sinistro,
                message.Subject,
                message.Subject,  # full_subject (mesmo que subject)
                message.Body,
                getattr(message, 'To', ''),
                getattr(message, 'CC', ''),
                _get_real_sender_email(message),  # Usa função melhorada para extrair email
                sent_time  # Usa SentOn ao invés de ReceivedTime
            )
            email_info_list.append(email_info)
        
        logging.info(f"Encontrados {len(email_info_list)} emails na caixa de enviados dos últimos {days_back} dias.")
        return email_info_list
        
    except Exception as e:
        logging.error(f"Erro ao recuperar informações de emails da caixa de enviados: {e}")
        return []


def get_filtered_sent_emails(subject_filters: Optional[List[str]] = None, 
                            days_back: int = DAYS_LOOKBACK) -> List[Tuple]:
    """
    Recupera emails da caixa de enviados filtrados por assuntos específicos.
    
    Args:
        subject_filters (Optional[List[str]]): Lista de strings que devem estar contidas no assunto
        days_back (int): Número de dias anteriores para buscar emails
        
    Returns:
        List[Tuple]: Lista de tuplas com emails filtrados
    """
    try:
        logging.info("Recuperando emails filtrados da caixa de enviados...")
        
        # Se não há filtros fornecidos, usa os da variável de ambiente
        if not subject_filters:
            subject_filters = _get_email_subject_list()
        
        # Busca todos os emails da caixa de enviados
        all_emails = get_sent_emails_info(days_back)
        
        # Se não há filtros, retorna todos os emails
        if not subject_filters:
            logging.info("Nenhum filtro de assunto definido, retornando todos os emails.")
            return all_emails
        
        # Se não há filtros, retorna todos os emails
        if not subject_filters:
            logging.info("Nenhum filtro de assunto definido, retornando todos os emails.")
            return all_emails
        
        # Aplica filtros de assunto
        filtered_emails = []
        for email_info in all_emails:
            subject = email_info[1]  # O assunto está no índice 1
            
            # Verifica se algum filtro está presente no assunto
            for filter_text in subject_filters:
                if filter_text.lower() in subject.lower():
                    filtered_emails.append(email_info)
                    break
        
        logging.info(f"Filtrados {len(filtered_emails)} emails dos {len(all_emails)} encontrados.")
        return filtered_emails
        
    except Exception as e:
        logging.error(f"Erro ao recuperar emails filtrados da caixa de enviados: {e}")
        return []


def get_emails_24h_new_only() -> List[Tuple]:
    """
    FUNÇÃO PRINCIPAL: Busca emails das últimas 24h que não foram processados de ambas as caixas (enviados e recebidos).
    Aplica filtro para processar apenas emails com números de sinistro válidos (6 dígitos começando com 6).
    
    Returns:
        List[Tuple]: Lista de emails novos para processar das últimas 24h com números válidos
    """
    try:
        logging.info("🔍 Buscando emails novos das últimas 24h da caixa de enviados E caixa de entrada...")
        
        # Busca emails das últimas 24h da caixa de enviados
        print("[FASE 3.1] Buscando emails da caixa de ENVIADOS...")
        sent_emails = get_sent_emails_info(days_back=1)
        sent_emails_24h = _filter_last_24h_exact(sent_emails)
        
        # Busca emails das últimas 24h da caixa de entrada
        print("[FASE 3.1] Buscando emails da caixa de ENTRADA...")
        inbox_emails = get_inbox_emails_info(days_back=1)
        inbox_emails_24h = _filter_last_24h_exact(inbox_emails)
        
        # Combinar ambas as listas
        all_emails_24h = sent_emails_24h + inbox_emails_24h
        
        print(f"[FASE 3.1] Emails encontrados - Enviados: {len(sent_emails_24h)}, Recebidos: {len(inbox_emails_24h)}")
        print(f"[FASE 3.1] Total de emails das últimas 24h: {len(all_emails_24h)}")
        
        # CONTROLE DE DUPLICATAS DESABILITADO - Permite reprocessar mesmo número de sinistro
        print("[FASE 3.1] [INFO] Controle de duplicatas DESABILITADO - permite reprocessar sinistros")
        
        # Aplicar apenas filtro de número válido (sem verificar se já foi processado)
        new_emails = []
        filtered_out_count = 0
        
        for email in all_emails_24h:
            # Aplicar apenas filtro de número válido
            numero_sinistro = email[0] if len(email) > 0 else None
            
            if numero_sinistro and _is_valid_sinistro_number(numero_sinistro):
                new_emails.append(email)
                subject = email[1] if len(email) > 1 else "Assunto não disponível"
                logging.info(f"✅ Email VÁLIDO encontrado - Sinistro: {numero_sinistro} no assunto: {subject}")
            else:
                filtered_out_count += 1
                # Log de emails inválidos apenas em debug para não poluir a saída
                subject = email[1] if len(email) > 1 else "Assunto não disponível"
                logging.debug(f"🚫 Email filtrado - Número inválido: {numero_sinistro} no assunto: {subject}")
        
        total_found = len(all_emails_24h)
        logging.info(f"Resultados da filtragem:")
        logging.info(f"   Total de emails encontrados: {total_found}")
        logging.info(f"   Emails com números válidos: {len(new_emails)}")
        logging.info(f"   🚫 Emails filtrados (números inválidos): {filtered_out_count}")
        
        print(f"[FILTRO] {len(new_emails)} emails válidos de {total_found} encontrados (filtrados: {filtered_out_count})")
        print(f"[FILTRO] Fontes: caixa de enviados + caixa de entrada")
        print(f"[FILTRO] DUPLICATAS PERMITIDAS - mesmo sinistro pode ser reprocessado")
        
        return new_emails
        
    except Exception as e:
        logging.error(f"Erro ao buscar emails das últimas 24h: {e}")
        return []


def mark_email_as_processed(email: Tuple) -> bool:
    """
    FUNÇÃO PRINCIPAL: Marca um email como processado para evitar duplicação.
    
    Args:
        email: Tupla do email (resultado de get_emails_24h_new_only())
        
    Returns:
        bool: True se marcou com sucesso
    """
    try:
        processed = _load_processed_emails()
        identifier = _create_email_identifier(email)
        processed.add(identifier)
        
        return _save_processed_emails(processed)
        
    except Exception as e:
        logging.error(f"Erro ao marcar email como processado: {e}")
        return False


def count_processed_emails() -> int:
    """Retorna quantos emails já foram processados"""
    return len(_load_processed_emails())


def save_processed_sinistro_to_file(numero_sinistro: str, subject: str, status: str = "Sucesso") -> bool:
    """
    Salva sinistro processado na pasta 'processados' no formato tradicional.
    
    Args:
        numero_sinistro: Número do sinistro
        subject: Assunto do email
        status: Status do processamento (Sucesso/Erro)
        
    Returns:
        bool: True se salvou com sucesso
    """
    try:
        from datetime import datetime
        
        # Cria nome do arquivo baseado na data atual
        now = datetime.now()
        filename = f"sinistros_concluidos_{now.strftime('%d-%m-%Y')}.txt"
        filepath = os.path.join("processados", filename)
        
        # Cria diretório se não existir
        os.makedirs("processados", exist_ok=True)
        
        # Prepara linha para salvar
        timestamp = now.strftime("%d/%m/%Y %H:%M:%S")
        linha = f"{subject} - {numero_sinistro} - {timestamp} - {status}\n"
        
        # Salva no arquivo
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(linha)
        
        logging.info(f"Sinistro salvo em {filepath}: {numero_sinistro}")
        return True
        
    except Exception as e:
        logging.error(f"Erro ao salvar sinistro em arquivo: {e}")
        return False


def check_processed_sinistro_in_file(numero_sinistro: str, subject: str) -> bool:
    """
    Verifica se sinistro já foi processado consultando arquivos da pasta processados.
    
    Args:
        numero_sinistro: Número do sinistro
        subject: Assunto do email
        
    Returns:
        bool: True se já foi processado
    """
    try:
        import glob
        
        # Busca todos os arquivos de sinistros concluídos
        pattern = os.path.join("processados", "sinistros_concluidos_*.txt")
        arquivos = glob.glob(pattern)
        
        # Verifica em cada arquivo
        for arquivo in arquivos:
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                    
                    # Verifica se a combinação assunto + sinistro já existe
                    if f"{subject} - {numero_sinistro}" in conteudo:
                        logging.info(f"Sinistro {numero_sinistro} já processado em {arquivo}")
                        return True
            except Exception:
                continue
        
        return False
        
    except Exception as e:
        logging.error(f"Erro ao verificar sinistro em arquivo: {e}")
        return False


def get_processed_sinistros_count() -> int:
    """Conta quantos sinistros foram processados nos arquivos da pasta processados"""
    try:
        import glob
        
        total = 0
        pattern = os.path.join("processados", "sinistros_concluidos_*.txt")
        arquivos = glob.glob(pattern)
        
        for arquivo in arquivos:
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    linhas = f.readlines()
                    total += len([linha for linha in linhas if linha.strip()])
            except Exception:
                continue
        
        return total
        
    except Exception as e:
        logging.error(f"Erro ao contar sinistros processados: {e}")
        return 0


def clean_old_processed_emails(days_to_keep: int = 7):
    """Remove emails processados mais antigos que X dias"""
    try:
        processed = _load_processed_emails()
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        
        new_processed = set()
        for item in processed:
            try:
                parts = item.split('|')
                if len(parts) >= 2:
                    date = datetime.strptime(parts[-1], "%Y-%m-%d %H:%M:%S")
                    if date >= cutoff:
                        new_processed.add(item)
            except:
                new_processed.add(item)  # Mantém em caso de erro
        
        if len(new_processed) < len(processed):
            _save_processed_emails(new_processed)
            logging.info(f"🧹 Removidos {len(processed) - len(new_processed)} emails antigos")
            
    except Exception as e:
        logging.error(f"Erro ao limpar emails antigos: {e}")


def _filter_last_24h_exact(emails: List[Tuple]) -> List[Tuple]:
    """
    Filtra emails das últimas 24 horas exatas.
    
    Compatível com ambos os formatos:
    - Emails enviados: email[7] é datetime
    - Emails recebidos: email[7] é string no formato '%d/%m/%Y %H:%M:%S'
    """
    local_timezone = datetime.now().astimezone().tzinfo
    cutoff = datetime.now().replace(tzinfo=local_timezone) - timedelta(hours=24)
    
    emails_24h = []
    for email in emails:
        try:
            # Extrai tempo do email (índice 7)
            time_data = email[7] if len(email) > 7 else None
            if not time_data:
                continue
                
            # Converte para datetime se for string
            if isinstance(time_data, str):
                try:
                    # Formato usado na caixa de entrada: '%d/%m/%Y %H:%M:%S'
                    email_time = datetime.strptime(time_data, '%d/%m/%Y %H:%M:%S')
                    email_time = email_time.replace(tzinfo=local_timezone)
                except ValueError:
                    # Tenta outros formatos comuns
                    try:
                        email_time = datetime.strptime(time_data, '%Y-%m-%d %H:%M:%S')
                        email_time = email_time.replace(tzinfo=local_timezone)
                    except ValueError:
                        continue
            elif hasattr(time_data, 'year'):  # É um objeto datetime
                email_time = time_data
                # Normaliza timezone
                if email_time.tzinfo is None:
                    email_time = email_time.replace(tzinfo=local_timezone)
                elif email_time.tzinfo != local_timezone:
                    email_time = email_time.astimezone(local_timezone)
            else:
                continue  # Formato não reconhecido
                
            # Verifica se está nas últimas 24h
            if email_time >= cutoff:
                emails_24h.append(email)
                
        except Exception as e:
            # Em caso de erro, assume que é um email válido para não perder dados
            continue
    
    return emails_24h


def _is_email_processed(email: Tuple, processed: Set[str]) -> bool:
    """Verifica se email já foi processado"""
    try:
        identifier = _create_email_identifier(email)
        return identifier in processed
    except:
        return False


def _create_email_identifier(email: Tuple) -> str:
    """Cria identificador único do email"""
    try:
        subject = email[1].strip().replace('\n', ' ').replace('\r', '')
        received_time = email[7]
        time_str = received_time.strftime("%Y-%m-%d %H:%M:%S")
        return f"{subject}|{time_str}"
    except:
        return f"email_sem_id|{datetime.now().isoformat()}"


def _load_processed_emails() -> Set[str]:
    """Carrega lista de emails processados"""
    try:
        os.makedirs(os.path.dirname(PROCESSED_EMAILS_FILE), exist_ok=True)
        
        if os.path.exists(PROCESSED_EMAILS_FILE):
            with open(PROCESSED_EMAILS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('processados', []))
        
        return set()
    except:
        return set()


def _save_processed_emails(processed: Set[str]) -> bool:
    """Salva lista de emails processados"""
    try:
        os.makedirs(os.path.dirname(PROCESSED_EMAILS_FILE), exist_ok=True)
        
        data = {
            'ultima_atualizacao': datetime.now().isoformat(),
            'total_processados': len(processed),
            'processados': list(processed)
        }
        
        with open(PROCESSED_EMAILS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    except:
        return False


def send_processing_email(numero_sinistro: str, start_time: str, 
                         end_time: str, status: str) -> bool:
    """
    Envia email de notificação sobre o processamento de um sinistro.
    
    Args:
        numero_sinistro (str): Número do sinistro
        start_time (str): Horário de início
        end_time (str): Horário de fim
        status (str): Status do processamento
        
    Returns:
        bool: True se o email foi enviado com sucesso, False caso contrário
    """
    try:
        subject = f"Processamento do Sinistro {numero_sinistro}"
        body = _create_claim_email_body(numero_sinistro, "", start_time, 
                                       end_time, "", status)
        
        recipient = os.getenv("EMAIL_TO_PROCESSED", DEFAULT_EMAIL_RECIPIENT)
        success = send_generic_email(recipient, subject, body)
        
        if success:
            print(f"Email de processamento enviado para o sinistro {numero_sinistro}.")
            
        return success
        
    except Exception as e:
        logging.error(f"Erro ao enviar email de processamento: {e}")
        return False


# =================== CONTROLE DE PROCESSOS ENCERRADOS ===================

def is_process_closed(numero_sinistro: str) -> bool:
    """
    Verifica se um processo já foi marcado como encerrado.
    
    Args:
        numero_sinistro (str): Número do sinistro a verificar
        
    Returns:
        bool: True se o processo está encerrado, False caso contrário
    """
    try:
        closed_processes = _load_closed_processes()
        # Verifica se o número do sinistro está em qualquer dos registros
        for item in closed_processes:
            if _extract_numero_sinistro_from_closed(item) == numero_sinistro:
                return True
        return False
    except Exception as e:
        logging.error(f"Erro ao verificar processo encerrado: {e}")
        return False


def mark_process_as_closed(numero_sinistro: str, motivo: str = "Botão editar não encontrado") -> bool:
    """
    Marca um processo como encerrado para evitar reprocessamento.
    
    Args:
        numero_sinistro (str): Número do sinistro
        motivo (str): Motivo do encerramento
        
    Returns:
        bool: True se marcou com sucesso
    """
    try:
        closed_processes = _load_closed_processes()
        identifier = f"{numero_sinistro}|{datetime.now().isoformat()}|{motivo}"
        closed_processes.add(identifier)
        
        success = _save_closed_processes(closed_processes)
        if success:
            logging.info(f"Processo {numero_sinistro} marcado como encerrado: {motivo}")
            print(f"[CONTROLE] Processo {numero_sinistro} marcado como encerrado - não será reprocessado")
        
        return success
        
    except Exception as e:
        logging.error(f"Erro ao marcar processo como encerrado: {e}")
        return False


def clean_old_closed_processes(days_to_keep: int = 30):
    """Remove processos encerrados mais antigos que X dias"""
    try:
        closed_processes = _load_closed_processes()
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        
        new_closed = set()
        for item in closed_processes:
            try:
                parts = item.split('|')
                if len(parts) >= 2:
                    date = datetime.fromisoformat(parts[1])
                    if date >= cutoff:
                        new_closed.add(item)
            except:
                new_closed.add(item)  # Mantém em caso de erro
        
        if len(new_closed) < len(closed_processes):
            _save_closed_processes(new_closed)
            logging.info(f"🧹 Removidos {len(closed_processes) - len(new_closed)} processos encerrados antigos")
            
    except Exception as e:
        logging.error(f"Erro ao limpar processos encerrados antigos: {e}")


def count_closed_processes() -> int:
    """Retorna quantos processos estão marcados como encerrados"""
    return len(_load_closed_processes())


def _load_closed_processes() -> Set[str]:
    """Carrega lista de processos encerrados"""
    try:
        os.makedirs(os.path.dirname(CLOSED_PROCESSES_FILE), exist_ok=True)
        
        if os.path.exists(CLOSED_PROCESSES_FILE):
            # Tentar várias codificações em ordem
            encodings = ['utf-8', 'utf-16', 'utf-16le', 'latin1', 'cp1252']
            file_size = os.path.getsize(CLOSED_PROCESSES_FILE)
            
            # Se arquivo vazio ou muito pequeno, retornar conjunto vazio
            if file_size == 0:
                logging.debug(f"Arquivo {CLOSED_PROCESSES_FILE} está vazio")
                return set()
            
            # Se arquivo corrompido (muito pequeno), recriá-lo
            if file_size < 5:
                logging.warning(f"Arquivo {CLOSED_PROCESSES_FILE} parece corrompido, recriando...")
                os.remove(CLOSED_PROCESSES_FILE)
                return set()
            
            # Tentar cada codificação
            for encoding in encodings:
                try:
                    with open(CLOSED_PROCESSES_FILE, 'r', encoding=encoding) as f:
                        data = json.load(f)
                        processes = set(data.get('processos_encerrados', []))
                        logging.debug(f"Carregados {len(processes)} processos encerrados usando {encoding}")
                        return processes
                except UnicodeError:
                    continue
                except json.JSONDecodeError:
                    continue
                except Exception as specific_error:
                    logging.debug(f"Erro ao tentar ler com {encoding}: {specific_error}")
                    continue
            
            # Se nenhuma codificação funcionou, arquivo está corrompido
            logging.error("Arquivo de processos encerrados está corrompido, recriando...")
            os.remove(CLOSED_PROCESSES_FILE)
            return set()
        else:
            logging.debug(f"Arquivo {CLOSED_PROCESSES_FILE} não existe, criando novo conjunto vazio")
            return set()
    
    except Exception as e:
        logging.error(f"ERRO ao carregar processos encerrados: {e}")
        print(f"[ERRO] Falha ao carregar processos encerrados: {e}")
        return set()


def _save_closed_processes(closed_processes: Set[str]) -> bool:
    """Salva lista de processos encerrados"""
    try:
        # Garantir que o diretório existe
        os.makedirs(os.path.dirname(CLOSED_PROCESSES_FILE), exist_ok=True)
        
        # Preparar dados para salvar
        data = {
            'ultima_atualizacao': datetime.now().isoformat(),
            'total_encerrados': len(closed_processes),
            'processos_encerrados': list(sorted(closed_processes))  # Ordenar para consistência
        }
        
        # Converter para JSON com formatação consistente
        json_str = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        
        # Primeiro salvar em arquivo temporário
        temp_file = f"{CLOSED_PROCESSES_FILE}.tmp"
        try:
            with open(temp_file, 'w', encoding='utf-8', newline='\n') as f:
                f.write(json_str)
            
            # Se chegou aqui, arquivo temporário foi salvo com sucesso
            # Agora podemos fazer o replace atômico
            if os.path.exists(CLOSED_PROCESSES_FILE):
                os.remove(CLOSED_PROCESSES_FILE)
            os.rename(temp_file, CLOSED_PROCESSES_FILE)
            
            logging.info(f"Arquivo de processos encerrados salvo com sucesso: {len(closed_processes)} processos")
            return True
            
        except Exception as save_error:
            # Se falhou, tentar remover arquivo temporário
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            raise save_error
            
    except Exception as e:
        logging.error(f"ERRO ao salvar processos encerrados em {CLOSED_PROCESSES_FILE}: {e}")
        print(f"[ERRO] Falha ao salvar processos encerrados: {e}")
        return False


def _extract_numero_sinistro_from_closed(closed_item: str) -> str:
    """Extrai número do sinistro de um item da lista de processos encerrados"""
    try:
        return closed_item.split('|')[0]
    except:
        return closed_item


# =================== RELATÓRIO CONSOLIDADO FINAL ===================

def get_current_user_email() -> str:
    """
    Obtém o endereço de email do usuário atual do Outlook.
    
    Returns:
        str: Endereço de email do usuário ou email padrão se não conseguir obter
    """
    try:
        _ensure_com_initialized()
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        
        # Método 1: Tentar obter através das contas
        try:
            for account in namespace.Accounts:
                smtp_address = getattr(account, 'SmtpAddress', None)
                if smtp_address and '@' in smtp_address:
                    logging.info(f"Email do usuário obtido via conta: {smtp_address}")
                    return smtp_address
        except Exception as e:
            logging.debug(f"Erro ao obter email via contas: {e}")
        
        # Método 2: Tentar através do CurrentUser e ExchangeUser
        try:
            current_user = namespace.CurrentUser
            if current_user:
                # Tentar obter AddressEntry
                address_entry = current_user
                if hasattr(address_entry, 'GetExchangeUser'):
                    exchange_user = address_entry.GetExchangeUser()
                    if exchange_user and hasattr(exchange_user, 'PrimarySmtpAddress'):
                        smtp_address = exchange_user.PrimarySmtpAddress
                        if smtp_address and '@' in smtp_address:
                            logging.info(f"Email do usuário obtido via ExchangeUser: {smtp_address}")
                            return smtp_address
        except Exception as e:
            logging.debug(f"Erro ao obter email via CurrentUser: {e}")
        
        # Método 3: Tentar via propriedades do usuário
        try:
            current_user = namespace.CurrentUser
            if current_user and hasattr(current_user, 'PropertyAccessor'):
                prop_accessor = current_user.PropertyAccessor
                # Propriedade para email SMTP
                smtp_prop = "http://schemas.microsoft.com/mapi/proptag/0x39FE001E"
                smtp_address = prop_accessor.GetProperty(smtp_prop)
                if smtp_address and '@' in smtp_address:
                    logging.info(f"Email do usuário obtido via PropertyAccessor: {smtp_address}")
                    return smtp_address
        except Exception as e:
            logging.debug(f"Erro ao obter email via PropertyAccessor: {e}")
        
        # Método 4: Tentar obter de emails enviados recentes
        try:
            sent_items = namespace.GetDefaultFolder(OUTLOOK_SENT_ITEMS_FOLDER)
            # Pegar o email mais recente dos itens enviados
            items = sent_items.Items
            items.Sort("[SentOn]", True)  # Ordenar por data decrescente
            
            if items.Count > 0:
                recent_item = items.Item(1)  # Primeiro item (mais recente)
                sender_address = getattr(recent_item, 'SenderEmailAddress', '')
                if sender_address and '@' in sender_address and not sender_address.startswith('/'):
                    logging.info(f"Email do usuário obtido via itens enviados: {sender_address}")
                    return sender_address
        except Exception as e:
            logging.debug(f"Erro ao obter email via itens enviados: {e}")
                
    except Exception as e:
        logging.warning(f"Não foi possível obter email do usuário: {e}")
    
    # Fallback: Usar email padrão e avisar
    logging.warning("Usando email padrão - não foi possível obter email do usuário do Outlook")
    print("[AVISO] Não foi possível obter email do usuário. Usando email padrão.")
    return DEFAULT_EMAIL_RECIPIENT


def send_consolidated_final_report(processed_list: List[str], non_processed_list: List[str], 
                                 execution_start_time: datetime, execution_end_time: datetime) -> bool:
    """
    Envia um relatório consolidado final profissional com estatísticas completas do processamento.
    
    Args:
        processed_list: Lista de sinistros processados com sucesso
        non_processed_list: Lista de sinistros não processados
        execution_start_time: Horário de início da execução
        execution_end_time: Horário de fim da execução
        
    Returns:
        bool: True se o email foi enviado com sucesso
    """
    try:
        logging.info("Preparando relatório consolidado final...")
        
        # Obter email do usuário
        user_email = get_current_user_email()
        
        # Gerar estatísticas completas
        stats = _generate_execution_statistics(processed_list, non_processed_list, 
                                             execution_start_time, execution_end_time)
        
        # Criar corpo do email em HTML profissional
        subject = f"AUTOMAÇÃO DE SINISTROS - Relatório de Execução - {execution_end_time.strftime('%d/%m/%Y %H:%M')}"
        body = _create_professional_report_body(stats, processed_list, non_processed_list)
        
        # Enviar email
        success = send_generic_email(user_email, subject, body, is_html=True)
        
        if success:
            logging.info(f"Relatório consolidado enviado para: {user_email}")
            print(f"[RELATÓRIO] Relatório final enviado para: {user_email}")
        else:
            logging.error("Falha ao enviar relatório consolidado")
            print("[RELATÓRIO] Falha ao enviar relatório final")
            
        return success
        
    except Exception as e:
        logging.error(f"Erro ao enviar relatório consolidado: {e}")
        print(f"[RELATÓRIO] Erro ao enviar relatório: {e}")
        return False


def _generate_execution_statistics(processed_list: List[str], non_processed_list: List[str],
                                 start_time: datetime, end_time: datetime) -> dict:
    """
    Gera estatísticas completas da execução.
    
    Returns:
        dict: Dicionário com todas as estatísticas
    """
    try:
        # Estatísticas básicas
        total_processed = len(processed_list)
        total_failed = len(non_processed_list)
        total_emails = total_processed + total_failed
        
        # Tempo de execução
        duration = end_time - start_time
        duration_str = str(duration).split('.')[0]  # Remove microsegundos
        
        # Taxa de sucesso
        success_rate = (total_processed / total_emails * 100) if total_emails > 0 else 0
        
        # Estatísticas de processos encerrados
        try:
            total_closed = count_closed_processes()
            closed_processes = _load_closed_processes()
            
            # Processos encerrados hoje
            today = datetime.now().date()
            closed_today = 0
            for item in closed_processes:
                try:
                    parts = item.split('|')
                    if len(parts) >= 2:
                        date = datetime.fromisoformat(parts[1]).date()
                        if date == today:
                            closed_today += 1
                except:
                    continue
                    
        except Exception:
            total_closed = 0
            closed_today = 0
        
        # Estatísticas de emails processados
        try:
            emails_processados_count = count_processed_emails()
        except Exception:
            emails_processados_count = 0
        
        return {
            'execution': {
                'start_time': start_time.strftime('%d/%m/%Y %H:%M:%S'),
                'end_time': end_time.strftime('%d/%m/%Y %H:%M:%S'),
                'duration': duration_str,
                'total_duration_seconds': int(duration.total_seconds())
            },
            'processing': {
                'total_emails': total_emails,
                'processed': total_processed,
                'failed': total_failed,
                'success_rate': round(success_rate, 2)
            },
            'control': {
                'total_closed_processes': total_closed,
                'closed_today': closed_today,
                'total_processed_emails': emails_processados_count
            }
        }
        
    except Exception as e:
        logging.error(f"Erro ao gerar estatísticas: {e}")
        return {}


def _validate_and_repair_closed_processes_file() -> None:
    """Valida e repara o arquivo de processos encerrados se necessário"""
    try:
        if not os.path.exists(CLOSED_PROCESSES_FILE):
            return
        
        # Tentar ler o arquivo com diferentes codificações
        content = None
        encodings = ['utf-8', 'utf-16', 'utf-16le', 'latin1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(CLOSED_PROCESSES_FILE, 'r', encoding=encoding) as f:
                    content = f.read()
                    # Tentar parse do JSON
                    data = json.loads(content)
                    if isinstance(data, dict) and 'processos_encerrados' in data:
                        # Se chegou aqui, arquivo está OK mas pode estar em codificação errada
                        if encoding != 'utf-8':
                            logging.warning(f"Convertendo arquivo de {encoding} para UTF-8...")
                            _save_closed_processes(set(data['processos_encerrados']))
                        return
                    break
            except:
                continue
        
        # Se chegou aqui, arquivo está corrompido
        logging.error("Arquivo de processos encerrados está corrompido, recriando...")
        os.remove(CLOSED_PROCESSES_FILE)
        _save_closed_processes(set())
        
    except Exception as e:
        logging.error(f"Erro ao validar arquivo de processos encerrados: {e}")

def _create_professional_report_body(stats: dict, processed_list: List[str], 
                                   non_processed_list: List[str]) -> str:
    """
    Cria o corpo do email do relatório consolidado em formato HTML profissional.
    
    Returns:
        str: Corpo do email formatado profissionalmente
    """
    try:
        # Estilo CSS profissional
        css_styles = """
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }
            .container { max-width: 800px; margin: 0 auto; background-color: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }
            .header h1 { margin: 0; font-size: 28px; font-weight: 300; }
            .header p { margin: 10px 0 0 0; opacity: 0.9; font-size: 16px; }
            .content { padding: 30px; }
            .summary-card { background-color: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 5px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
            .stat-item { background: white; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            .stat-value { font-size: 36px; font-weight: bold; margin-bottom: 5px; }
            .stat-label { color: #6c757d; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }
            .success { color: #28a745; }
            .warning { color: #ffc107; }
            .danger { color: #dc3545; }
            .info { color: #17a2b8; }
            .section { margin: 30px 0; }
            .section h2 { color: #495057; border-bottom: 2px solid #e9ecef; padding-bottom: 10px; margin-bottom: 20px; }
            .table { width: 100%; border-collapse: collapse; margin: 15px 0; }
            .table th { background-color: #f8f9fa; color: #495057; padding: 15px; text-align: left; border-bottom: 2px solid #dee2e6; font-weight: 600; }
            .table td { padding: 12px 15px; border-bottom: 1px solid #dee2e6; }
            .table tr:nth-child(even) { background-color: #f8f9fa; }
            .table tr:hover { background-color: #e9ecef; }
            .footer { background-color: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; border-radius: 0 0 10px 10px; }
            .badge { display: inline-block; padding: 4px 8px; border-radius: 20px; font-size: 12px; font-weight: bold; text-transform: uppercase; }
            .badge-success { background-color: #d4edda; color: #155724; }
            .badge-danger { background-color: #f8d7da; color: #721c24; }
            .no-data { text-align: center; color: #6c757d; font-style: italic; padding: 40px; }
        </style>
        """
        
        # Início do HTML
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Relatório de Automação de Sinistros</title>
            {css_styles}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>RELATÓRIO DE AUTOMAÇÃO DE SINISTROS</h1>
                    <p>Sistema de Processamento Automatizado - AON Brasil</p>
                </div>
                
                <div class="content">
        """
        
        # Resumo executivo com estatísticas
        if stats:
            success_rate = stats['processing']['success_rate']
            rate_color = 'success' if success_rate >= 80 else 'warning' if success_rate >= 60 else 'danger'
            
            html += f"""
                    <div class="summary-card">
                        <h2 style="margin-top: 0; color: #495057;">RESUMO EXECUTIVO</h2>
                        <p><strong>Período:</strong> {stats['execution']['start_time']} até {stats['execution']['end_time']}</p>
                        <p><strong>Duração Total:</strong> {stats['execution']['duration']}</p>
                        <p><strong>Status:</strong> <span class="badge badge-{'success' if success_rate >= 80 else 'danger'}">
                            {'EXECUÇÃO CONCLUÍDA' if success_rate >= 80 else 'EXECUÇÃO COM FALHAS'}
                        </span></p>
                    </div>
                    
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-value info">{stats['processing']['total_emails']}</div>
                            <div class="stat-label">Total de Emails</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value success">{stats['processing']['processed']}</div>
                            <div class="stat-label">Processados</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value danger">{stats['processing']['failed']}</div>
                            <div class="stat-label">Falhas</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value {rate_color}">{stats['processing']['success_rate']}%</div>
                            <div class="stat-label">Taxa de Sucesso</div>
                        </div>
                    </div>
                    
                    <div class="summary-card">
                        <h3 style="margin-top: 0; color: #495057;">CONTROLE DE QUALIDADE</h3>
                        <p><strong>Processos Encerrados (Total):</strong> {stats['control']['total_closed_processes']}</p>
                        <p><strong>Processos Encerrados (Hoje):</strong> {stats['control']['closed_today']}</p>
                        <p><strong>Emails Já Processados (Sistema):</strong> {stats['control']['total_processed_emails']}</p>
                    </div>
            """
        
        # Seção de sinistros processados com sucesso
        if processed_list:
            html += f"""
                    <div class="section">
                        <h2>SINISTROS PROCESSADOS COM SUCESSO ({len(processed_list)})</h2>
                        <table class="table">
                            <thead>
                                <tr>
                                    <th width="60">Nº</th>
                                    <th width="150">Número do Sinistro</th>
                                    <th>Assunto do Email</th>
                                    <th width="80">Status</th>
                                </tr>
                            </thead>
                            <tbody>
            """
            
            for i, item in enumerate(processed_list, 1):
                parts = item.split(" - ", 1)
                numero = parts[0] if len(parts) > 0 else "N/A"
                assunto = parts[1] if len(parts) > 1 else "Assunto não identificado"
                
                html += f"""
                                <tr>
                                    <td><strong>{i:02d}</strong></td>
                                    <td><strong>{numero}</strong></td>
                                    <td>{assunto}</td>
                                    <td><span class="badge badge-success">OK</span></td>
                                </tr>
                """
            
            html += """
                            </tbody>
                        </table>
                    </div>
            """
        else:
            html += """
                    <div class="section">
                        <h2>SINISTROS PROCESSADOS COM SUCESSO (0)</h2>
                        <div class="no-data">Nenhum sinistro foi processado com sucesso nesta execução.</div>
                    </div>
            """
        
        # Seção de sinistros com falha
        if non_processed_list:
            html += f"""
                    <div class="section">
                        <h2>FALHAS NO PROCESSAMENTO ({len(non_processed_list)})</h2>
                        <table class="table">
                            <thead>
                                <tr>
                                    <th width="60">Nº</th>
                                    <th width="150">Número do Sinistro</th>
                                    <th>Assunto do Email</th>
                                    <th width="80">Status</th>
                                </tr>
                            </thead>
                            <tbody>
            """
            
            for i, item in enumerate(non_processed_list, 1):
                parts = item.split(" - ", 1)
                numero = parts[0] if len(parts) > 0 else "N/A"
                assunto = parts[1] if len(parts) > 1 else "Assunto não identificado"
                
                html += f"""
                                <tr>
                                    <td><strong>{i:02d}</strong></td>
                                    <td><strong>{numero}</strong></td>
                                    <td>{assunto}</td>
                                    <td><span class="badge badge-danger">ERRO</span></td>
                                </tr>
                """
            
            html += """
                            </tbody>
                        </table>
                        
                        <div class="summary-card" style="border-left-color: #dc3545; background-color: #f8d7da;">
                            <h3 style="margin-top: 0; color: #721c24;">AÇÕES RECOMENDADAS</h3>
                            <ul style="margin: 0; padding-left: 20px;">
                                <li>Verificar logs de erro para identificar causas das falhas</li>
                                <li>Revisar números de sinistro que não seguem padrão (6 dígitos iniciando com 6)</li>
                                <li>Confirmar se processos não estão encerrados no sistema AON</li>
                                <li>Verificar conectividade e estabilidade do sistema</li>
                            </ul>
                        </div>
                    </div>
            """
        else:
            html += """
                    <div class="section">
                        <h2>FALHAS NO PROCESSAMENTO (0)</h2>
                        <div class="no-data" style="color: #28a745;">
                            Excelente! Todos os sinistros foram processados com sucesso.
                        </div>
                    </div>
            """
        
        # Rodapé
        html += f"""
                </div>
                
                <div class="footer">
                    <p><strong>Sistema de Automação de Sinistros - AON Brasil</strong></p>
                    <p>Relatório gerado automaticamente em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
                    <p style="font-size: 12px; margin-top: 10px;">
                        Este é um relatório automático. Para dúvidas ou problemas, contate a equipe de TI.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
        
    except Exception as e:
        logging.error(f"Erro ao criar corpo do relatório profissional: {e}")
        # Fallback para formato simples sem emojis
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
        <h1>RELATÓRIO FINAL - AUTOMAÇÃO DE SINISTROS</h1>
        <h2>ERRO NA GERAÇÃO DO RELATÓRIO</h2>
        <p><strong>Processados:</strong> {len(processed_list)}</p>
        <p><strong>Falhas:</strong> {len(non_processed_list)}</p>
        <p><strong>Erro:</strong> {e}</p>
        </body>
        </html>
        """



def save_execution_report(stats: dict, processed_list: List[str], 
                         non_processed_list: List[str]) -> str:
    """
    Salva relatório de execução em arquivo JSON.
    
    Returns:
        str: Caminho do arquivo salvo
    """
    try:
        # Criar diretório se não existir
        reports_dir = "data/reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"relatorio_execucao_{timestamp}.json"
        filepath = os.path.join(reports_dir, filename)
        
        # Dados do relatório
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "statistics": stats,
            "processed": processed_list,
            "failed": non_processed_list,
            "summary": {
                "total_emails": len(processed_list) + len(non_processed_list),
                "success_count": len(processed_list),
                "failure_count": len(non_processed_list),
                "success_rate": (len(processed_list) / (len(processed_list) + len(non_processed_list)) * 100) if (len(processed_list) + len(non_processed_list)) > 0 else 0
            }
        }
        
        # Salvar arquivo
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Relatório salvo em: {filepath}")
        return filepath
        
    except Exception as e:
        logging.error(f"Erro ao salvar relatório: {e}")
        return ""
