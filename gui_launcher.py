#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface Gráfica para Sistema de Automação de Sinistros AON

Esta interface fornece uma experiência visual moderna para executar
o sistema de automação, incluindo lo        # Frame de status do sistema com padding reduzido
        status_frame = ttk.LabelFrame(
            main_frame,
            text=" Status do Sistema ",
            style="AON.TFrame",
            padding="15"
        )
        status_frame.pack(fill=tk.X, pady=(0, 15))ro e monitoramento de status.
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import threading
import subprocess
import sys
import os
from datetime import datetime
import json
import logging

# Adicionar o diretório raiz ao path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Cores da AON
AON_RED = "#EB0017"
AON_WHITE = "#FFFFFF"
AON_LIGHT_GRAY = "#F5F5F5"
AON_DARK_GRAY = "#333333"
AON_BLUE = "#0066CC"

class AONAutomationGUI:
    def __init__(self):
        self.root = tk.Tk()
        
        # Variáveis de controle do painel de progresso
        self.current_sinistro = tk.StringVar(value="Aguardando...")
        self.current_position = tk.StringVar(value="0/0")
        self.current_step = tk.StringVar(value="Sistema pronto")
        self.is_running = False
        
        # Variáveis de controle do botão
        self.pending_processes = 0
        self.credentials_valid = False
        
        self.setup_window()
        self.setup_styles()
        self.create_widgets()
        self.update_pending_count()
        
    def setup_window(self):
        """Configura a janela principal"""
        self.root.title("Sistema de Automação de Sinistros AON - V2.0")
        self.root.geometry("650x650")  # Altura aumentada para garantir que o botão apareça
        self.root.resizable(False, False)
        self.root.configure(bg=AON_WHITE)
        
        # Centralizar na tela
        self.center_window()
        
        # Ícone da janela (se disponível)
        try:
            if os.path.exists("assets/icon.ico"):
                self.root.iconbitmap("assets/icon.ico")
        except:
            pass
    
    def center_window(self):
        """Centraliza a janela na tela, otimizada para notebooks"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        # Posição horizontal: centrada
        pos_x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        
        # Posição vertical: um pouco mais para cima (30% da tela) para notebooks
        screen_height = self.root.winfo_screenheight()
        pos_y = int(screen_height * 0.15)  # 15% do topo da tela ao invés de centralizado
        
        # Garantir que a janela não saia da tela
        if pos_y + height > screen_height:
            pos_y = screen_height - height - 50  # 50px de margem inferior
        
        self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
    
    def setup_styles(self):
        """Configura os estilos da interface"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Estilo para botões
        self.style.configure(
            "AON.TButton",
            background=AON_RED,
            foreground=AON_WHITE,
            font=('Segoe UI', 12, 'bold'),
            borderwidth=0,
            focuscolor='none'
        )
        
        self.style.map(
            "AON.TButton",
            background=[('active', '#CC0015'), ('pressed', '#AA0012')]
        )
        
        # Estilo para frames
        self.style.configure("AON.TFrame", background=AON_WHITE)
        
        # Estilo para labels
        self.style.configure(
            "Title.TLabel",
            background=AON_WHITE,
            foreground=AON_DARK_GRAY,
            font=('Segoe UI', 20, 'bold')
        )
        
        self.style.configure(
            "Subtitle.TLabel",
            background=AON_WHITE,
            foreground=AON_DARK_GRAY,
            font=('Segoe UI', 12)
        )
        
        self.style.configure(
            "Status.TLabel",
            background=AON_WHITE,
            foreground=AON_BLUE,
            font=('Segoe UI', 10, 'bold')
        )
    
    def create_widgets(self):
        """Cria todos os widgets da interface em layout horizontal"""
        
        # Alterar geometria para formato mais horizontal
        self.root.geometry("1000x600")
        
        # Container principal com padding
        main_container = ttk.Frame(self.root, style="AON.TFrame", padding="15")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # =========================
        # CABEÇALHO (TOPO)
        # =========================
        header_frame = ttk.Frame(main_container, style="AON.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Logo e título lado a lado
        logo_title_frame = ttk.Frame(header_frame, style="AON.TFrame")
        logo_title_frame.pack(fill=tk.X)
        
        # Logo à esquerda
        logo_frame = ttk.Frame(logo_title_frame, style="AON.TFrame")
        logo_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        logo_text = """
  ▄▄▄▄▄▄▄ ▄▄▄▄▄▄▄ ▄▄    ▄ 
 █   ▄   █   ▄   █  █  █ █
 █  █▄█  █  █▄█  █   █▄█ █
 █       █       █       █
 █▄▄█ █▄▄█▄▄█ █▄▄█▄█  █▄▄█
        """
        
        logo_label = tk.Label(
            logo_frame,
            text=logo_text,
            font=('Courier New', 6, 'bold'),
            foreground=AON_RED,
            background=AON_WHITE,
            justify=tk.CENTER
        )
        logo_label.pack()
        
        # Títulos à direita do logo
        title_frame = ttk.Frame(logo_title_frame, style="AON.TFrame")
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        title_label = ttk.Label(
            title_frame,
            text="Sistema de Automação de Sinistros",
            style="Title.TLabel"
        )
        title_label.pack(anchor=tk.W, pady=(10, 2))
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Versão 2.0 - Interface Gráfica Desktop",
            style="Subtitle.TLabel"
        )
        subtitle_label.pack(anchor=tk.W)
        
        # =========================
        # ÁREA PRINCIPAL (HORIZONTAL)
        # =========================
        content_frame = ttk.Frame(main_container, style="AON.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # COLUNA ESQUERDA - LOGIN E AÇÕES (40% da largura)
        left_column = ttk.Frame(content_frame, style="AON.TFrame")
        left_column.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        left_column.configure(width=350)  # Largura fixa
        
        # Frame de login
        login_frame = ttk.LabelFrame(
            left_column,
            text=" Credenciais de Acesso ",
            style="AON.TFrame",
            padding="15"
        )
        login_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Campo de usuário
        ttk.Label(
            login_frame,
            text="Usuário:",
            font=('Segoe UI', 11, 'bold'),
            background=AON_WHITE,
            foreground=AON_DARK_GRAY
        ).pack(anchor=tk.W, pady=(0, 5))
        
        self.username_var = tk.StringVar()
        self.username_var.trace('w', self.validate_button_state)
        self.username_entry = ttk.Entry(
            login_frame,
            textvariable=self.username_var,
            font=('Segoe UI', 11),
            width=30
        )
        self.username_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Campo de senha
        ttk.Label(
            login_frame,
            text="Senha:",
            font=('Segoe UI', 11, 'bold'),
            background=AON_WHITE,
            foreground=AON_DARK_GRAY
        ).pack(anchor=tk.W, pady=(0, 5))
        
        self.password_var = tk.StringVar()
        self.password_var.trace('w', self.validate_button_state)
        self.password_entry = ttk.Entry(
            login_frame,
            textvariable=self.password_var,
            font=('Segoe UI', 11),
            width=30,
            show="*"
        )
        self.password_entry.pack(fill=tk.X)
        
        # Frame de ações
        action_frame = ttk.LabelFrame(
            left_column,
            text=" Controle de Execução ",
            style="AON.TFrame",
            padding="15"
        )
        action_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Botão executar
        self.execute_btn = ttk.Button(
            action_frame,
            text="🚀 EXECUTAR AUTOMAÇÃO",
            command=self.execute_automation,
            style="AON.TButton",
            state='disabled'
        )
        self.execute_btn.pack(fill=tk.X, ipady=10)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            action_frame,
            variable=self.progress_var,
            mode='indeterminate'
        )
        self.progress_bar.pack(fill=tk.X, pady=(10, 0))
        self.progress_bar.pack_forget()
        
        # Status da execução
        self.execution_status = ttk.Label(
            action_frame,
            text="",
            font=('Segoe UI', 10),
            background=AON_WHITE,
            foreground=AON_BLUE
        )
        self.execution_status.pack(pady=(8, 0))
        
        # COLUNA DIREITA - STATUS E INFORMAÇÕES (60% da largura)
        right_column = ttk.Frame(content_frame, style="AON.TFrame")
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Frame de status do sistema (parte superior)
        status_frame = ttk.LabelFrame(
            right_column,
            text=" Status do Sistema ",
            style="AON.TFrame",
            padding="15"
        )
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Layout horizontal para contador e botão
        status_content_frame = ttk.Frame(status_frame, style="AON.TFrame")
        status_content_frame.pack(fill=tk.X)
        
        # Contador à esquerda
        counter_frame = ttk.Frame(status_content_frame, style="AON.TFrame")
        counter_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.pending_label = ttk.Label(
            counter_frame,
            text="Carregando...",
            style="Status.TLabel"
        )
        self.pending_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.last_update_label = ttk.Label(
            counter_frame,
            text="",
            font=('Segoe UI', 9),
            background=AON_WHITE,
            foreground=AON_DARK_GRAY
        )
        self.last_update_label.pack(anchor=tk.W)
        
        # Botão atualizar à direita
        button_frame = ttk.Frame(status_content_frame, style="AON.TFrame")
        button_frame.pack(side=tk.RIGHT, padx=(15, 0))
        
        refresh_btn = ttk.Button(
            button_frame,
            text="🔄 Atualizar",
            command=self.update_pending_count,
            style="AON.TButton"
        )
        refresh_btn.pack()
        
        # Frame de histórico de execuções
        history_frame = ttk.LabelFrame(
            right_column,
            text=" Histórico de Execuções ",
            style="AON.TFrame",
            padding="15"
        )
        history_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Área de texto para histórico com scroll
        history_text_frame = ttk.Frame(history_frame, style="AON.TFrame")
        history_text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.history_text = tk.Text(
            history_text_frame,
            height=10,
            font=('Consolas', 9),
            bg=AON_WHITE,
            fg=AON_DARK_GRAY,
            relief=tk.SUNKEN,
            borderwidth=1,
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        
        # Scrollbar para o histórico
        history_scrollbar = ttk.Scrollbar(
            history_text_frame,
            orient="vertical",
            command=self.history_text.yview
        )
        self.history_text.configure(yscrollcommand=history_scrollbar.set)
        
        self.history_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Adicionar entrada inicial no histórico
        self.add_history_entry("📋 Sistema inicializado - Aguardando execução...")
        
        
        # Frame de progresso detalhado na coluna direita
        self.progress_detail_frame = ttk.LabelFrame(
            right_column,
            text=" Status da Execução ",
            style="AON.TFrame",
            padding="15"
        )
        self.progress_detail_frame.pack(fill=tk.X, pady=(0, 15))
        self.progress_detail_frame.pack_forget()  # Inicialmente oculto
        
        # Sinistro atual
        sinistro_frame = ttk.Frame(self.progress_detail_frame, style="AON.TFrame")
        sinistro_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            sinistro_frame,
            text="📋 Sinistro Atual:",
            font=('Segoe UI', 10, 'bold'),
            background=AON_WHITE,
            foreground=AON_DARK_GRAY
        ).pack(side=tk.LEFT)
        
        self.current_sinistro_label = ttk.Label(
            sinistro_frame,
            textvariable=self.current_sinistro,
            font=('Segoe UI', 10),
            background=AON_WHITE,
            foreground=AON_RED
        )
        self.current_sinistro_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Posição na fila
        position_frame = ttk.Frame(self.progress_detail_frame, style="AON.TFrame")
        position_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            position_frame,
            text="📊 Progresso:",
            font=('Segoe UI', 10, 'bold'),
            background=AON_WHITE,
            foreground=AON_DARK_GRAY
        ).pack(side=tk.LEFT)
        
        self.current_position_label = ttk.Label(
            position_frame,
            textvariable=self.current_position,
            font=('Segoe UI', 10),
            background=AON_WHITE,
            foreground=AON_BLUE
        )
        self.current_position_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Etapa atual
        step_frame = ttk.Frame(self.progress_detail_frame, style="AON.TFrame")
        step_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            step_frame,
            text="⚙️ Etapa:",
            font=('Segoe UI', 10, 'bold'),
            background=AON_WHITE,
            foreground=AON_DARK_GRAY
        ).pack(side=tk.LEFT)
        
        self.current_step_label = ttk.Label(
            step_frame,
            textvariable=self.current_step,
            font=('Segoe UI', 10),
            background=AON_WHITE,
            foreground=AON_DARK_GRAY
        )
        self.current_step_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Barra de progresso com porcentagem
        progress_container = ttk.Frame(self.progress_detail_frame, style="AON.TFrame")
        progress_container.pack(fill=tk.X, pady=(0, 10))
        
        self.detailed_progress_var = tk.DoubleVar()
        self.detailed_progress_bar = ttk.Progressbar(
            progress_container,
            variable=self.detailed_progress_var,
            mode='determinate',
            length=300
        )
        self.detailed_progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.progress_percentage_label = ttk.Label(
            progress_container,
            text="0%",
            font=('Segoe UI', 9),
            background=AON_WHITE,
            foreground=AON_DARK_GRAY
        )
        self.progress_percentage_label.pack()
        
        # Footer no final do container principal
        footer_frame = ttk.Frame(main_container, style="AON.TFrame")
        footer_frame.pack(fill=tk.X, pady=(20, 0))
        
        footer_label = ttk.Label(
            footer_frame,
            text=f"© {datetime.now().year} AON Brasil - Todos os direitos reservados",
            font=('Segoe UI', 8),
            background=AON_WHITE,
            foreground=AON_DARK_GRAY
        )
        footer_label.pack()
        
        # Bind Enter para executar
        self.root.bind('<Return>', lambda e: self.execute_automation())
        
        # Focar no campo de usuário
        self.username_entry.focus()
        
        # Validar estado inicial do botão
        self.validate_button_state()
    
    def update_pending_count(self):
        """Atualiza a contagem de processos pendentes"""
        try:
            # Importar funções necessárias
            from services.email_service import get_emails_24h_new_only, get_processed_sinistros_count
            
            # Buscar emails novos
            new_emails = get_emails_24h_new_only()
            
            if new_emails is not None:
                count = len(new_emails)
                self.pending_processes = count  # Atualizar variável de controle
                
                if count == 0:
                    self.pending_label.configure(
                        text="✅ Nenhum processo pendente",
                        foreground="#28a745"
                    )
                    self.add_history_entry("✅ Verificação completa - Nenhum processo pendente")
                elif count == 1:
                    self.pending_label.configure(
                        text="📧 1 processo pendente para automação",
                        foreground=AON_RED
                    )
                    self.add_history_entry("📧 Encontrado 1 processo pendente")
                else:
                    self.pending_label.configure(
                        text=f"📧 {count} processos pendentes para automação",
                        foreground=AON_RED
                    )
                    self.add_history_entry(f"📧 Encontrados {count} processos pendentes")
            else:
                self.pending_processes = 0  # Nenhum processo se houver erro
                self.pending_label.configure(
                    text="❌ Erro ao conectar com Outlook",
                    foreground="#dc3545"
                )
                self.add_history_entry("❌ Erro de conexão com Outlook")
            
            # Atualizar timestamp
            self.last_update_label.configure(
                text=f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            )
            
            # Validar estado do botão após atualizar contagem
            self.validate_button_state()
            
        except Exception as e:
            self.pending_processes = 0  # Reset em caso de erro
            self.pending_label.configure(
                text="❌ Erro ao verificar processos pendentes",
                foreground="#dc3545"
            )
            logging.error(f"Erro ao atualizar contagem: {e}")
            
            # Validar estado do botão mesmo com erro
            self.validate_button_state()
    
    def add_history_entry(self, message):
        """Adiciona uma entrada no histórico de execuções"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            entry = f"[{timestamp}] {message}\n"
            
            self.history_text.configure(state=tk.NORMAL)
            self.history_text.insert(tk.END, entry)
            self.history_text.configure(state=tk.DISABLED)
            self.history_text.see(tk.END)  # Scroll para o final
        except Exception as e:
            logging.error(f"Erro ao adicionar entrada no histórico: {e}")
    
    def validate_button_state(self, *args):
        """Valida e atualiza o estado do botão de execução"""
        try:
            # Verificar se campos estão preenchidos
            username_filled = len(self.username_var.get().strip()) > 0
            password_filled = len(self.password_var.get().strip()) > 0
            
            # Verificar se há processos disponíveis
            processes_available = self.pending_processes > 0
            
            # Verificar se não está executando
            not_running = not self.is_running
            
            # Habilitar botão se credenciais estão preenchidas e não está executando
            if username_filled and password_filled and not_running:
                self.execute_btn.configure(state='normal')
                
                if processes_available:
                    self.execute_btn.configure(text="🚀 EXECUTAR AUTOMAÇÃO")
                else:
                    self.execute_btn.configure(text="🔍 BUSCAR NOVOS PROCESSOS")
            else:
                self.execute_btn.configure(state='disabled')
                
                # Mostrar mensagem específica do que está faltando
                if not username_filled or not password_filled:
                    self.execute_btn.configure(text="⚠️ PREENCHA USUÁRIO E SENHA")
                elif self.is_running:
                    self.execute_btn.configure(text="⏳ EXECUTANDO...")
                    
        except Exception as e:
            logging.error(f"Erro ao validar estado do botão: {e}")
    
    def validate_credentials(self):
        """Valida as credenciais inseridas"""
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if not username:
            messagebox.showerror("Erro", "Por favor, insira seu usuário.")
            self.username_entry.focus()
            return False
        
        if not password:
            messagebox.showerror("Erro", "Por favor, insira sua senha.")
            self.password_entry.focus()
            return False
        
        return True
    
    def save_credentials_to_env(self):
        """Salva as credenciais no arquivo .env temporariamente"""
        try:
            username = self.username_var.get().strip()
            password = self.password_var.get().strip()
            
            # Ler arquivo .env atual
            env_path = ".env"
            env_content = ""
            
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    env_content = f.read()
            
            # Atualizar credenciais
            lines = env_content.split('\n')
            updated_lines = []
            username_found = False
            password_found = False
            url_found = False
            
            for line in lines:
                if line.startswith('AON_USERNAME='):
                    updated_lines.append(f'AON_USERNAME={username}')
                    username_found = True
                elif line.startswith('AON_PASSWORD='):
                    updated_lines.append(f'AON_PASSWORD={password}')
                    password_found = True
                elif line.startswith('AON_URL='):
                    updated_lines.append('AON_URL=https://aonaccessv5br.aonnet.aon.net/InbrokerV5Web_BR/Home/index.aspx')
                    url_found = True
                else:
                    updated_lines.append(line)
            
            # Adicionar se não existirem
            if not username_found:
                updated_lines.append(f'AON_USERNAME={username}')
            if not password_found:
                updated_lines.append(f'AON_PASSWORD={password}')
            if not url_found:
                updated_lines.append('AON_URL=https://aonaccessv5br.aonnet.aon.net/InbrokerV5Web_BR/Home/index.aspx')
            
            # Salvar arquivo
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(updated_lines))
            
            return True
            
        except Exception as e:
            logging.error(f"Erro ao salvar credenciais: {e}")
            return False
    
    def update_progress_panel(self, sinistro_num="", position="0/0", step="", percentage=0):
        """Atualiza o painel de progresso detalhado"""
        try:
            if sinistro_num:
                self.current_sinistro.set(sinistro_num)
            self.current_position.set(position)
            if step:
                self.current_step.set(step)
            
            # Atualizar barra de progresso
            self.detailed_progress_var.set(percentage)
            self.progress_percentage_label.config(text=f"{percentage:.1f}%")
            
        except Exception as e:
            logging.error(f"Erro ao atualizar painel de progresso: {e}")
    
    def show_progress_panel(self):
        """Mostra o painel de progresso detalhado"""
        self.progress_detail_frame.pack(fill=tk.X, pady=(0, 20))
        self.is_running = True
        
        # Reset do painel
        self.current_sinistro.set("Inicializando...")
        self.current_position.set("0/0")
        self.current_step.set("Preparando execução...")
        self.detailed_progress_var.set(0)
        self.progress_percentage_label.config(text="0%")
        
        # Validar estado do botão
        self.validate_button_state()
    
    def hide_progress_panel(self):
        """Oculta o painel de progresso detalhado"""
        self.progress_detail_frame.pack_forget()
        self.is_running = False
        
        # Reset do painel
        self.current_sinistro.set("Aguardando...")
        self.current_position.set("0/0")
        self.current_step.set("Sistema pronto")
        self.detailed_progress_var.set(0)
        self.progress_percentage_label.config(text="0%")
        
        # Validar estado do botão
        self.validate_button_state()
    
    def simulate_progress(self):
        """Simula o progresso da automação enquanto ela roda"""
        if not self.is_running:
            return
        
        try:
            # Buscar emails novos para estimar total
            from services.email_service import get_emails_24h_new_only
            emails = get_emails_24h_new_only()
            total_emails = len(emails) if emails else 1
            
            # Etapas da automação
            steps = [
                "Validando credenciais...",
                "Conectando ao Outlook...",
                "Buscando emails novos...",
                "Iniciando navegador...",
                "Fazendo login no sistema...",
                "Processando sinistros..."
            ]
            
            # Simular progresso por etapas
            for i, step in enumerate(steps):
                if not self.is_running:
                    return
                
                percentage = (i + 1) * (80 / len(steps))  # 80% para etapas iniciais
                self.root.after(0, self.update_progress_panel, "", f"0/{total_emails}", step, percentage)
                
                # Aguardar um pouco entre etapas
                import time
                time.sleep(1)
            
            # Simular processamento de emails
            for i in range(total_emails):
                if not self.is_running:
                    return
                
                sinistro_num = f"Sinistro #{i+1}"
                if emails and i < len(emails):
                    # Usar número real do sinistro se disponível
                    sinistro_num = emails[i][0] if emails[i][0] else f"Sinistro #{i+1}"
                
                position = f"{i+1}/{total_emails}"
                step = "Processando sinistro..."
                percentage = 80 + (i + 1) * (20 / total_emails)  # 20% restante para processamento
                
                self.root.after(0, self.update_progress_panel, sinistro_num, position, step, percentage)
                
                # Simular tempo de processamento
                import time
                time.sleep(2)
                
        except Exception as e:
            logging.error(f"Erro na simulação de progresso: {e}")
    
    def execute_automation(self):
        """Executa a automação em thread separada"""
        # Salvar credenciais
        if not self.save_credentials_to_env():
            messagebox.showerror("Erro", "Erro ao salvar credenciais.")
            self.add_history_entry("❌ Erro ao salvar credenciais")
            return
        
        self.add_history_entry("🚀 Iniciando automação...")
        
        # Mostrar progress bars e painel de progresso
        self.progress_bar.pack(fill=tk.X, pady=(10, 0))
        self.progress_bar.start(10)
        self.show_progress_panel()
        
        self.execution_status.configure(
            text="Iniciando automação...",
            foreground=AON_BLUE
        )
        
        # Executar automação em thread separada
        automation_thread = threading.Thread(target=self._run_automation)
        automation_thread.daemon = True
        automation_thread.start()
        
        # Executar simulação de progresso em thread separada
        progress_thread = threading.Thread(target=self.simulate_progress)
        progress_thread.daemon = True
        progress_thread.start()
    
    def _run_automation(self):
        """Executa a automação (roda em thread separada)"""
        try:
            # Simular progresso inicial
            self.root.after(0, self.update_progress_panel, "", "0/0", "Conectando ao sistema...", 10)
            
            # Caminho absoluto para o script principal
            main_script = os.path.join(project_root, "core", "main.py")
            
            # Verificar se o arquivo existe
            if not os.path.exists(main_script):
                raise FileNotFoundError(f"Script principal não encontrado: {main_script}")
            
            # Executar o script principal
            result = subprocess.run(
                [sys.executable, main_script],
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=3600  # 1 hora de timeout
            )
            
            # Atualizar interface na thread principal
            self.root.after(0, self._automation_finished, result.returncode == 0, result.stdout, result.stderr)
            
        except subprocess.TimeoutExpired:
            self.root.after(0, self._automation_finished, False, "", "Timeout: Processo demorou mais de 1 hora")
        except FileNotFoundError as e:
            self.root.after(0, self._automation_finished, False, "", f"Arquivo não encontrado: {e}")
        except Exception as e:
            self.root.after(0, self._automation_finished, False, "", f"Erro inesperado: {e}")
    
    def _automation_finished(self, success, stdout, stderr):
        """Callback quando a automação termina"""
        # Parar progress bar
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        
        # Ocultar painel de progresso detalhado (já atualiza o botão)
        self.hide_progress_panel()
        
        if success:
            self.execution_status.configure(
                text="✅ Automação concluída com sucesso!",
                foreground="#28a745"
            )
            messagebox.showinfo(
                "Sucesso",
                "Automação executada com sucesso!\n\nVerifique os logs para mais detalhes."
            )
        else:
            self.execution_status.configure(
                text="❌ Erro durante a execução",
                foreground="#dc3545"
            )
            
            # Preparar mensagem de erro mais detalhada
            error_details = ""
            if stderr:
                error_details = f"Erro reportado:\n{stderr[:300]}"
            elif stdout:
                error_details = f"Saída do programa:\n{stdout[:300]}"
            else:
                error_details = "Nenhum detalhe de erro disponível"
            
            messagebox.showerror(
                "Erro na Execução",
                f"Erro durante a execução da automação.\n\n{error_details}\n\n" +
                "Verifique:\n" +
                "• Se o Outlook está instalado e configurado\n" +
                "• Se as credenciais estão corretas\n" +
                "• Se há conexão com a internet\n" +
                "• Os logs do sistema para mais detalhes"
            )
        
        # Atualizar contagem
        self.update_pending_count()
        
        # Limpar senha por segurança
        self.password_var.set("")
    
    def run(self):
        """Executa a interface"""
        self.root.mainloop()

def main():
    """Função principal"""
    try:
        # Configurar logging básico
        logging.basicConfig(level=logging.INFO)
        
        # Criar e executar interface
        app = AONAutomationGUI()
        app.run()
        
    except Exception as e:
        messagebox.showerror("Erro Fatal", f"Erro ao iniciar aplicação:\n{e}")
        logging.error(f"Erro fatal: {e}")

if __name__ == "__main__":
    main()