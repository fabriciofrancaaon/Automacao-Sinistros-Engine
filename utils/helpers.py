# -*- coding: utf-8 -*-
"""
Helper Utilities Module

Este módulo fornece funções utilitárias de suporte para o sistema de
automação de sinistros, incluindo gerenciamento de logs, timestamps
e dados processados.

Funcionalidades principais:
- Geração de timestamps semanais
- Gerenciamento de sinistros processados
- Configuração de logging
- Redação de dados sensíveis
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Set, Optional


# Constantes
DEFAULT_PROCESSED_DIR = "processados"
DEFAULT_LOGS_DIR = "logs"
DEFAULT_FILENAME_PREFIX = "sinistros_concluidos"
DEFAULT_LOG_PREFIX = "logfile_sinistros"
SENSITIVE_MASK = "******"


def get_week_timestamp() -> str:
    """
    Retorna um timestamp representando a semana atual no formato DD-MM-YYYY_to_DD-MM-YYYY.
    
    Returns:
        str: Timestamp da semana atual
        
    Example:
        "01-01-2024_to_07-01-2024"
    """
    current_date = datetime.now()
    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    return f"{start_of_week.strftime('%d-%m-%Y')}_to_{end_of_week.strftime('%d-%m-%Y')}"


def save_successful_claim(numero_sinistro: str, subject: str) -> bool:
    """
    Salva o número do sinistro processado com sucesso em arquivo de texto semanal.
    
    Args:
        numero_sinistro (str): Número do sinistro processado
        subject (str): Assunto/tipo do sinistro
        
    Returns:
        bool: True se salvamento foi bem-sucedido, False caso contrário
    """
    try:
        timestamp = get_week_timestamp()
        directory = _get_processed_claims_directory()
        
        # Cria diretório se não existir
        os.makedirs(directory, exist_ok=True)
        
        # Define nome do arquivo
        filename_prefix = os.getenv("PROCESSED_CLAIMS_FILENAME_PREFIX", DEFAULT_FILENAME_PREFIX)
        file_path = os.path.join(directory, f"{filename_prefix}_{timestamp}.txt")
        
        # Salva dados no arquivo
        with open(file_path, "a", encoding="utf-8") as file:
            file.write(f"{subject} - {numero_sinistro}\n")
        
        logging.info(f"Sinistro salvo com sucesso: {numero_sinistro}")
        return True
        
    except Exception as e:
        logging.error(f"Erro ao salvar sinistro {numero_sinistro}: {e}")
        return False


def load_processed_claims() -> Set[str]:
    """
    Carrega os números de sinistros processados da semana atual e anterior.
    
    Returns:
        Set[str]: Conjunto de sinistros já processados
    """
    try:
        processed_claims = set()
        
        # Carrega arquivos da semana atual e anterior
        for offset_weeks in [0, 1]:
            file_path = _get_file_path_for_week(offset_weeks)
            claims_from_file = _load_claims_from_file(file_path)
            processed_claims.update(claims_from_file)
        
        logging.info(f"Carregados {len(processed_claims)} sinistros processados")
        return processed_claims
        
    except Exception as e:
        logging.error(f"Erro ao carregar sinistros processados: {e}")
        return set()


def _get_processed_claims_directory() -> str:
    """
    Retorna o diretório para arquivos de sinistros processados.
    
    Returns:
        str: Caminho do diretório
    """
    env_dir = os.getenv("PROCESSED_CLAIMS_DIR")
    if env_dir:
        return env_dir
    
    # Diretório padrão relativo ao módulo atual
    return os.path.join(os.path.dirname(__file__), '..', DEFAULT_PROCESSED_DIR)


def _get_file_path_for_week(offset_weeks: int = 0) -> str:
    """
    Retorna o caminho do arquivo para uma semana específica.
    
    Args:
        offset_weeks (int): Número de semanas para retroceder (0 = semana atual)
        
    Returns:
        str: Caminho completo do arquivo
    """
    # Calcula a data da semana alvo
    target_date = datetime.now() - timedelta(weeks=offset_weeks)
    start_of_week = target_date - timedelta(days=target_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Gera timestamp
    timestamp = f"{start_of_week.strftime('%d-%m-%Y')}_to_{end_of_week.strftime('%d-%m-%Y')}"
    
    # Monta caminho do arquivo
    directory = _get_processed_claims_directory()
    filename_prefix = os.getenv("PROCESSED_CLAIMS_FILENAME_PREFIX", DEFAULT_FILENAME_PREFIX)
    
    return os.path.join(directory, f"{filename_prefix}_{timestamp}.txt")


def _load_claims_from_file(file_path: str) -> Set[str]:
    """
    Carrega sinistros de um arquivo específico.
    
    Args:
        file_path (str): Caminho do arquivo
        
    Returns:
        Set[str]: Conjunto de sinistros do arquivo
    """
    if not os.path.exists(file_path):
        return set()
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return {line.strip() for line in file.readlines() if line.strip()}
    except Exception as e:
        logging.warning(f"Erro ao ler arquivo {file_path}: {e}")
        return set()


def redact_sensitive_data(message: str) -> str:
    """
    Remove dados sensíveis como senhas de mensagens de log.
    
    Args:
        message (str): Mensagem original
        
    Returns:
        str: Mensagem com dados sensíveis mascarados
    """
    if not message:
        return message
    
    # Lista de variáveis de ambiente sensíveis
    sensitive_env_vars = [
        "AON_PASSWORD",
        "EMAIL_PASSWORD", 
        "DB_PASSWORD",
        "API_KEY",
        "SECRET_KEY"
    ]
    
    redacted_message = message
    
    for env_var in sensitive_env_vars:
        sensitive_value = os.getenv(env_var)
        if sensitive_value and sensitive_value in redacted_message:
            redacted_message = redacted_message.replace(sensitive_value, SENSITIVE_MASK)
    
    return redacted_message


def log_and_print(message: str, logger: logging.Logger, level: str = "info") -> None:
    """
    Registra mensagem no log e imprime no console, removendo dados sensíveis.
    
    Args:
        message (str): Mensagem a ser registrada
        logger (logging.Logger): Instância do logger
        level (str): Nível do log ("info", "error", "warning", "debug")
    """
    safe_message = redact_sensitive_data(message)
    
    # Mapeia níveis de log
    log_methods = {
        "info": logger.info,
        "error": logger.error,
        "warning": logger.warning,
        "debug": logger.debug
    }
    
    # Registra no log
    log_method = log_methods.get(level.lower(), logger.info)
    log_method(safe_message)
    
    # Imprime no console
    print(safe_message)


def setup_logger() -> logging.Logger:
    """
    Configura e retorna um logger para o sistema.
    
    Returns:
        logging.Logger: Logger configurado
    """
    try:
        # Cria diretório de logs
        log_dir = _get_logs_directory()
        os.makedirs(log_dir, exist_ok=True)
        
        # Define nome do arquivo de log
        log_prefix = os.getenv("LOG_FILENAME_PREFIX", DEFAULT_LOG_PREFIX)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = os.path.join(log_dir, f"{log_prefix}_{timestamp}.log")
        
        # Configura formato do log
        log_format = "%(asctime)s - %(levelname)s - %(message)s"
        
        # Configura logging básico
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            filename=log_filename,
            encoding="utf-8"
        )
        
        logger = logging.getLogger()
        logger.info("Logger configurado com sucesso")
        
        return logger
        
    except Exception as e:
        # Fallback para logger básico se configuração falhar
        print(f"Erro ao configurar logger: {e}")
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        return logging.getLogger()


def _get_logs_directory() -> str:
    """
    Retorna o diretório para arquivos de log.
    
    Returns:
        str: Caminho do diretório de logs
    """
    env_dir = os.getenv("LOGS_DIR")
    if env_dir:
        return env_dir
    
    # Diretório padrão relativo ao módulo atual
    return os.path.join(os.path.dirname(__file__), '..', DEFAULT_LOGS_DIR)


def create_timestamp() -> str:
    """
    Cria um timestamp no formato YYYYMMDD_HHMMSS.
    
    Returns:
        str: Timestamp formatado
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def is_within_business_hours(start_hour: int = 8, end_hour: int = 18) -> bool:
    """
    Verifica se o horário atual está dentro do horário comercial.
    
    Args:
        start_hour (int): Hora de início (padrão: 8)
        end_hour (int): Hora de fim (padrão: 18)
        
    Returns:
        bool: True se dentro do horário comercial, False caso contrário
    """
    current_hour = datetime.now().hour
    return start_hour <= current_hour < end_hour


def format_duration(start_time: datetime, end_time: datetime) -> str:
    """
    Formata a duração entre dois momentos.
    
    Args:
        start_time (datetime): Horário de início
        end_time (datetime): Horário de fim
        
    Returns:
        str: Duração formatada (ex: "2m 30s")
    """
    duration = end_time - start_time
    total_seconds = int(duration.total_seconds())
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"
