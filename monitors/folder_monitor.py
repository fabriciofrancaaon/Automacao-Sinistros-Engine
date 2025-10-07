# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Monitor de Pasta de Rede
========================

Script para monitorar mudanças em uma pasta de rede específica.
Monitora adições, modificações e remoções de arquivos e pastas.

Autor: Sistema de Monitoramento
Data: 2025-08-06
"""

import os
import time
import logging
import json
import re
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("ERRO: Biblioteca 'watchdog' não encontrada!")
    print("Execute: pip install watchdog --user")
    exit(1)

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    import subprocess
    # Importa as funções de navegação personalizadas
    from ..services.navigation_service import navigate_and_perform_actions
    from ..services.login_service import login
    from ..utils.helpers import load_processed_claims, save_successful_claim
    from ..services.email_service import get_outlook_email_info, extract_numero_sinistro
except ImportError as e:
    print(f"AVISO: Biblioteca não encontrada: {e}")
    print("Execute: pip install selenium --user")
    print("Automação web será desabilitada.")
    selenium_available = False
else:
    selenium_available = True

# Configuração de logging
# Garantir que a pasta de logs existe
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
log_dir = os.path.join(project_root, 'data', 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, 'monitor_rede.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class MonitorEventHandler(FileSystemEventHandler):
    """Handler para eventos do sistema de arquivos"""
    
    def __init__(self, config):
        self.config = config
        # Usar caminho completo para arquivo de eventos na pasta data
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        data_dir = os.path.join(project_root, 'data', 'logs')
        os.makedirs(data_dir, exist_ok=True)
        
        log_filename = config.get('log_file', 'eventos_monitoramento.json')
        self.log_file = os.path.join(data_dir, log_filename)
        self.automacao_enabled = config.get('automacao_selenium', True) and selenium_available
        
    def extract_file_info(self, file_path):
        """Extrai informaç[EMOJI]es do arquivo para processamento"""
        try:
            file_name = os.path.basename(file_path)
            
            # Tenta extrair informaç[EMOJI]es do nome do arquivo
            info = {
                'file_path': file_path,
                'file_name': file_name,
                'numero_sinistro': None,
                'subject': None
            }
            
            # Se o arquivo contém 'AON', tenta extrair o número do sinistro
            if 'AON' in file_name.upper():
                try:
                    # Usa regex para extrair números após AON
                    import re
                    match = re.search(r'AON(\d+)', file_name.upper())
                    if match:
                        numero_sinistro = match.group(1)
                        info['numero_sinistro'] = numero_sinistro
                        info['subject'] = file_name
                        logger.info(f"Sinistro extraído: AON{numero_sinistro} do arquivo {file_name}")
                    else:
                        # Fallback para a função original
                        numero_sinistro = extract_numero_sinistro(file_name)
                        if numero_sinistro:
                            info['numero_sinistro'] = numero_sinistro
                            info['subject'] = file_name
                except Exception as e:
                    logger.warning(f"Erro ao extrair número do sinistro: {e}")
            
            return info
        except Exception as e:
            logger.error(f"Erro ao extrair informaç[EMOJI]es do arquivo {file_path}: {e}")
            return {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'numero_sinistro': None,
                'subject': None
            }
        
    def trigger_selenium_automation(self, file_path):
        """Executa automação via main.py quando arquivo é criado"""
        if not self.automacao_enabled:
            logger.warning("Automação desabilitada na configuração")
            return
            
        try:
            logger.info(f"Iniciando automação para arquivo: {file_path}")
            
            # Extrai informaç[EMOJI]es do arquivo
            file_info = self.extract_file_info(file_path)
            
            # Sempre executa via main.py (orquestrador) quando arquivo é criado
            logger.info("Executando automação via main.py (orquestrador)")
            
            # Chama o main.py passando o caminho do arquivo
            import subprocess
            import sys
            
            # Executa como módulo Python para resolver imports relativos
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            
            # Executa main.py via módulo com o arquivo como parâmetro
            result = subprocess.run([
                sys.executable, '-m', 'automacao_sinistros.core.main', file_path
            ], capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=project_root)
            
            if result.returncode == 0:
                logger.info("Automação via main.py executada com sucesso")
                
                # Salva como processado se tiver informaç[EMOJI]es do sinistro
                if file_info.get('numero_sinistro') and file_info.get('subject'):
                    save_successful_claim(file_info['numero_sinistro'], file_info['subject'])
                    logger.info(f"Sinistro {file_info['numero_sinistro']} salvo como processado")
                
                self.log_event("AUTOMACAO_MAIN_SUCESSO", file_path, {
                    'numero_sinistro': file_info.get('numero_sinistro'),
                    'subject': file_info.get('subject'),
                    'status': 'sucesso_completo',
                    'stdout': result.stdout[:500] if result.stdout else '',
                    'orquestrador': 'main.py'
                })
            else:
                logger.error(f"Erro na automação via main.py: {result.stderr}")
                self.log_event("AUTOMACAO_MAIN_ERRO", file_path, {
                    'numero_sinistro': file_info.get('numero_sinistro'),
                    'subject': file_info.get('subject'),
                    'status': 'falha',
                    'stderr': result.stderr[:500] if result.stderr else '',
                    'returncode': result.returncode
                })
            
            logger.info("Automação concluída")
            
        except Exception as e:
            logger.error(f"Erro na automação: {e}")
            self.log_event("AUTOMACAO_ERRO", file_path, {
                'erro': str(e),
                'status': 'falha'
            })
        
    def log_event(self, event_type, file_path, details=None):
        """Registra evento em arquivo de log JSON"""
        event_data = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'file_path': str(file_path),
            'details': details or {}
        }
        
        # Adiciona ao arquivo de log JSON
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    events = json.load(f)
            else:
                events = []
                
            events.append(event_data)
            
            # Mantém apenas os últimos 1000 eventos
            if len(events) > 1000:
                events = events[-1000:]
                
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Erro ao salvar evento no log JSON: {e}")
        
        # Log no console/arquivo
        logger.info(f"{event_type}: {file_path}")
    
    def get_file_info(self, file_path):
        """Obtém informaç[EMOJI]es do arquivo"""
        try:
            stat = os.stat(file_path)
            return {
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except Exception:
            return {}
    
    def on_created(self, event):
        """Arquivo ou pasta criado"""
        if not event.is_directory:
            logger.info(f"ARQUIVO DETECTADO - Arquivo criado: {event.src_path}")
            details = self.get_file_info(event.src_path)
            self.log_event("ARQUIVO_CRIADO", event.src_path, details)
            
            # SEMPRE executa automação Selenium quando arquivo é criado
            logger.info(f"ATIVANDO AUTOMAÇÃO - Iniciando main.py para: {event.src_path}")
            self.trigger_selenium_automation(event.src_path)
        else:
            logger.info(f"PASTA DETECTADA - Pasta criada: {event.src_path}")
            self.log_event("PASTA_CRIADA", event.src_path)
    
    def on_deleted(self, event):
        """Arquivo ou pasta deletado"""
        if not event.is_directory:
            self.log_event("ARQUIVO_DELETADO", event.src_path)
        else:
            self.log_event("PASTA_DELETADA", event.src_path)
    
    def on_modified(self, event):
        """Arquivo ou pasta modificado"""
        if not event.is_directory:
            details = self.get_file_info(event.src_path)
            self.log_event("ARQUIVO_MODIFICADO", event.src_path, details)
    
    def on_moved(self, event):
        """Arquivo ou pasta movido/renomeado"""
        details = {
            'origem': event.src_path,
            'destino': event.dest_path
        }
        if not event.is_directory:
            self.log_event("ARQUIVO_MOVIDO", event.dest_path, details)
        else:
            self.log_event("PASTA_MOVIDA", event.dest_path, details)

class NetworkFolderMonitor:
    """Monitor principal para pasta de rede"""
    
    def __init__(self, config_file=None):
        if config_file is None:
            # Usar arquivo de configuração da pasta config
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            config_file = os.path.join(project_root, 'config', 'monitor.json')
        self.config = self.load_config(config_file)
        self.observer = Observer()
        self.event_handler = MonitorEventHandler(self.config)
        
    def load_config(self, config_file):
        """Carrega configuração do arquivo JSON"""
        default_config = {
            'pasta_monitorada': r'\\aonnet.aon.net\SAFS\Brazil\Sao_Paulo\Chatbot',
            'intervalo_verificacao': 30,
            'recursive': True,
            'log_file': 'eventos_monitoramento.json',
            'automacao_selenium': True,
            'selenium_headless': True,
            'navegacao_completa': True,
            'timeout_navegacao': 60,
            'usar_main_orquestrador': True
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Merge com configuração padrão
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                # Cria arquivo de configuração padrão
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                logger.info(f"Arquivo de configuração criado: {config_file}")
                return default_config
                
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            return default_config
    
    def check_network_access(self):
        """Verifica se a pasta de rede está acessível"""
        pasta = self.config['pasta_monitorada']
        try:
            return os.path.exists(pasta) and os.path.isdir(pasta)
        except Exception:
            return False
    
    def start_monitoring(self):
        """Inicia o monitoramento"""
        if not self.check_network_access():
            logger.error("Não foi possível acessar a pasta de rede. Verifique a conectividade.")
            return False
        
        pasta = self.config['pasta_monitorada']
        recursive = self.config.get('recursive', True)
        
        try:
            self.observer.schedule(
                self.event_handler,
                pasta,
                recursive=recursive
            )
            
            self.observer.start()
            logger.info(f"Monitoramento iniciado para: {pasta}")
            logger.info(f"Modo recursivo: {recursive}")
            
            # Gera relatório inicial
            self.generate_initial_report()
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao iniciar monitoramento: {e}")
            return False
    
    def generate_initial_report(self):
        """Gera relatório inicial do conteúdo da pasta"""
        pasta = self.config['pasta_monitorada']
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'pasta_monitorada': pasta,
                'total_arquivos': 0,
                'total_pastas': 0
            }
            
            for root, dirs, files in os.walk(pasta):
                report['total_pastas'] += len(dirs)
                report['total_arquivos'] += len(files)
            
            # Salva relatório na pasta data
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            data_dir = os.path.join(project_root, 'data', 'reports')
            os.makedirs(data_dir, exist_ok=True)
            
            report_file = os.path.join(data_dir, 'relatorio_inicial.json')
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Relatório inicial: {report['total_arquivos']} arquivos, {report['total_pastas']} pastas")
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório inicial: {e}")
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        try:
            self.observer.stop()
            self.observer.join()
            logger.info("Monitoramento interrompido")
        except Exception as e:
            logger.error(f"Erro ao parar monitoramento: {e}")
    
    def run(self):
        """Executa o monitor em loop contínuo"""
        if not self.start_monitoring():
            return
        
        try:
            while True:
                time.sleep(self.config.get('intervalo_verificacao', 10))
                
                # Verifica se ainda tem acesso à rede
                if not self.check_network_access():
                    logger.warning("Perda de acesso à pasta de rede detectada")
                    time.sleep(30)  # Aguarda antes de tentar novamente
                    
        except KeyboardInterrupt:
            logger.info("Interrupção pelo usuário detectada")
        finally:
            self.stop_monitoring()

def main():
    """Função principal"""
    print("=" * 60)
    print("MONITOR DE PASTA DE REDE - AON")
    print("=" * 60)
    print("Pasta monitorada: \\\\aonnet.aon.net\\SAFS\\Brazil\\Sao_Paulo\\Chatbot")
    print("Pressione Ctrl+C para parar o monitoramento")
    print("=" * 60)
    
    monitor = NetworkFolderMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
