# -*- coding: utf-8 -*-
"""
Screenshot Manager Module

Este módulo fornece funcionalidades para captura, organização e
gerenciamento de screenshots durante a execução da automação,
com categorização automática e limpeza de arquivos antigos.

Funcionalidades principais:
- Captura de screenshots organizados por categoria
- Estrutura de pastas automática
- Migração de screenshots antigos
- Limpeza automática de arquivos
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union
import logging


class ScreenshotConfig:
    """Configurações para gerenciamento de screenshots."""
    
    # Estrutura de diretórios
    SCREENSHOTS_DIR = "screenshots"
    ERRORS_DIR = "errors"
    GENERAL_DIR = "general"
    
    # Formatos e nomeação
    TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
    FILENAME_FORMAT = "{category}_{description}_{timestamp}.png"
    
    # Configurações de arquivo
    DEFAULT_FORMAT = "PNG"
    JPEG_QUALITY = 95
    
    # Limpeza automática
    CLEANUP_DAYS = 30  # Dias para manter screenshots


class ScreenshotManagerError(Exception):
    """Exceção customizada para erros do gerenciador de screenshots."""
    pass


class ScreenshotManager:
    """
    Gerenciador de screenshots para o sistema de automação.
    
    Esta classe encapsula toda a lógica de captura, nomeação e organização
    de screenshots durante a execução da automação, com categorização
    automática e limpeza de arquivos antigos.
    """
    
    def __init__(self, driver, logger: logging.Logger, base_path: Optional[str] = None):
        """
        Inicializa o gerenciador de screenshots.
        
        Args:
            driver: Instância do WebDriver do Selenium
            logger (logging.Logger): Logger para registrar operações
            base_path (Optional[str]): Caminho base para salvar screenshots
        """
        self.driver = driver
        self.logger = logger
        self.config = ScreenshotConfig()
        
        # Define caminho base (raiz do projeto por padrão)
        if base_path is None:
            self.base_path = Path(__file__).parent.parent
        else:
            self.base_path = Path(base_path)
        
        # Inicializa estrutura
        self._initialize_structure()
    
    def _initialize_structure(self) -> None:
        """
        Inicializa a estrutura completa de diretórios e migração.
        """
        try:
            self._create_directory_structure()
            self._migrate_existing_screenshots()
            self._cleanup_old_screenshots()
            self.logger.info("Estrutura de screenshots inicializada com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao inicializar estrutura de screenshots: {e}")
    
    def _create_directory_structure(self) -> None:
        """
        Cria a estrutura de diretórios para organização dos screenshots.
        """
        # Pasta principal
        self.screenshots_path = self.base_path / self.config.SCREENSHOTS_DIR
        self.screenshots_path.mkdir(exist_ok=True)
        
        # Subpastas por categoria
        categories = [self.config.ERRORS_DIR, self.config.GENERAL_DIR]
        
        for category in categories:
            category_path = self.screenshots_path / category
            category_path.mkdir(exist_ok=True)
        
        self.logger.info(f"Estrutura de screenshots criada: {self.screenshots_path}")
    
    def _migrate_existing_screenshots(self) -> None:
        """
        Migra screenshots existentes na raiz do projeto para estrutura organizada.
        """
        try:
            moved_count = 0
            
            # Procura por arquivos .png na raiz do projeto
            for file_path in self.base_path.glob("*.png"):
                if file_path.is_file():
                    dest_path = self.screenshots_path / self.config.GENERAL_DIR / file_path.name
                    shutil.move(str(file_path), str(dest_path))
                    moved_count += 1
            
            if moved_count > 0:
                self.logger.info(f"Migrados {moved_count} screenshots existentes")
                
        except Exception as e:
            self.logger.warning(f"Erro ao migrar screenshots existentes: {e}")
    
    def _cleanup_old_screenshots(self) -> None:
        """
        Remove screenshots antigos baseado na configuração de dias.
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.CLEANUP_DAYS)
            removed_count = 0
            
            for category in [self.config.ERRORS_DIR, self.config.GENERAL_DIR]:
                category_path = self.screenshots_path / category
                
                for file_path in category_path.glob("*.png"):
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_date:
                        file_path.unlink()
                        removed_count += 1
            
            if removed_count > 0:
                self.logger.info(f"Removidos {removed_count} screenshots antigos")
                
        except Exception as e:
            self.logger.warning(f"Erro durante limpeza de screenshots: {e}")
    
    def take_screenshot(self, category: str = "errors", description: str = "screenshot", 
                       custom_name: Optional[str] = None) -> Optional[str]:
        """
        Captura um screenshot e salva na categoria apropriada.
        
        Args:
            category (str): Categoria do screenshot (errors, general)
            description (str): Descrição breve do screenshot
            custom_name (Optional[str]): Nome customizado para o arquivo
            
        Returns:
            Optional[str]: Caminho completo do arquivo salvo, ou None se falhou
        """
        try:
            # Valida e normaliza categoria
            category = self._validate_category(category)
            
            # Gera nome do arquivo
            filename = self._generate_filename(category, description, custom_name)
            
            # Define caminho completo
            file_path = self.screenshots_path / category / filename
            
            # Captura e salva screenshot
            success = self._capture_and_save(file_path)
            
            if success:
                self.logger.info(f"Screenshot capturado: {filename}")
                return str(file_path)
            else:
                self.logger.error(f"Falha ao capturar screenshot: {filename}")
                return None
                
        except Exception as e:
            self.logger.error(f"Erro ao capturar screenshot: {e}")
            return None
    
    def take_error_screenshot(self, description: str = "error") -> Optional[str]:
        """
        Captura um screenshot de erro de forma simplificada.
        
        Args:
            description (str): Descrição do erro
            
        Returns:
            Optional[str]: Caminho do arquivo salvo ou None se falhou
        """
        return self.take_screenshot(
            category=self.config.ERRORS_DIR,
            description=description
        )
    
    def take_general_screenshot(self, description: str = "general") -> Optional[str]:
        """
        Captura um screenshot geral de forma simplificada.
        
        Args:
            description (str): Descrição do screenshot
            
        Returns:
            Optional[str]: Caminho do arquivo salvo ou None se falhou
        """
        return self.take_screenshot(
            category=self.config.GENERAL_DIR,
            description=description
        )
    
    def _validate_category(self, category: str) -> str:
        """
        Valida e retorna categoria válida.
        
        Args:
            category (str): Categoria solicitada
            
        Returns:
            str: Categoria válida
        """
        valid_categories = [self.config.ERRORS_DIR, self.config.GENERAL_DIR]
        
        if category not in valid_categories:
            self.logger.warning(f"Categoria inválida '{category}', usando 'errors'")
            return self.config.ERRORS_DIR
        
        return category
    
    def _generate_filename(self, category: str, description: str, 
                          custom_name: Optional[str]) -> str:
        """
        Gera nome do arquivo baseado nos parâmetros.
        
        Args:
            category (str): Categoria do screenshot
            description (str): Descrição
            custom_name (Optional[str]): Nome customizado
            
        Returns:
            str: Nome do arquivo gerado
        """
        timestamp = datetime.now().strftime(self.config.TIMESTAMP_FORMAT)
        
        if custom_name:
            return f"{custom_name}_{timestamp}.png"
        else:
            return self.config.FILENAME_FORMAT.format(
                category=category,
                description=description,
                timestamp=timestamp
            )
    
    def _capture_and_save(self, file_path: Path) -> bool:
        """
        Captura screenshot e salva no caminho especificado.
        
        Args:
            file_path (Path): Caminho onde salvar o arquivo
            
        Returns:
            bool: True se sucesso, False se falhou
        """
        try:
            # Verifica se driver está disponível
            if not self.driver:
                self.logger.error("Driver não disponível para captura de screenshot")
                return False
            
            # Captura screenshot
            screenshot_data = self.driver.get_screenshot_as_png()
            
            # Salva arquivo
            with open(file_path, 'wb') as file:
                file.write(screenshot_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar screenshot em {file_path}: {e}")
            return False
    
    def get_screenshots_info(self) -> dict:
        """
        Retorna informações sobre os screenshots armazenados.
        
        Returns:
            dict: Informações sobre screenshots por categoria
        """
        try:
            info = {"categories": {}}
            
            for category in [self.config.ERRORS_DIR, self.config.GENERAL_DIR]:
                category_path = self.screenshots_path / category
                
                if category_path.exists():
                    files = list(category_path.glob("*.png"))
                    info["categories"][category] = {
                        "count": len(files),
                        "total_size_mb": sum(f.stat().st_size for f in files) / (1024 * 1024),
                        "latest": max(files, key=lambda f: f.stat().st_mtime).name if files else None
                    }
                else:
                    info["categories"][category] = {"count": 0, "total_size_mb": 0, "latest": None}
            
            return info
            
        except Exception as e:
            self.logger.error(f"Erro ao obter informações de screenshots: {e}")
            return {}
    
    def cleanup_category(self, category: str, days: Optional[int] = None) -> int:
        """
        Limpa screenshots de uma categoria específica.
        
        Args:
            category (str): Categoria a ser limpa
            days (Optional[int]): Número de dias para manter (usa padrão se None)
            
        Returns:
            int: Número de arquivos removidos
        """
        try:
            category = self._validate_category(category)
            days = days or self.config.CLEANUP_DAYS
            
            cutoff_date = datetime.now() - timedelta(days=days)
            category_path = self.screenshots_path / category
            removed_count = 0
            
            for file_path in category_path.glob("*.png"):
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    file_path.unlink()
                    removed_count += 1
            
            self.logger.info(f"Removidos {removed_count} screenshots da categoria {category}")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar categoria {category}: {e}")
            return 0
    
    def get_screenshot_path(self, category: str = "errors") -> str:
        """
        Retorna o caminho do diretório de uma categoria.
        
        Args:
            category (str): Categoria desejada
            
        Returns:
            str: Caminho do diretório
        """
        category = self._validate_category(category)
        return str(self.screenshots_path / category)


# Função de compatibilidade para manter API existente
def create_screenshot_manager(driver, logger, base_path: Optional[str] = None) -> ScreenshotManager:
    """
    Função de compatibilidade para criar instância do ScreenshotManager.
    
    Args:
        driver: WebDriver instance
        logger: Logger instance
        base_path (Optional[str]): Base path for screenshots
        
    Returns:
        ScreenshotManager: Configured instance
    """
    return ScreenshotManager(driver, logger, base_path)
