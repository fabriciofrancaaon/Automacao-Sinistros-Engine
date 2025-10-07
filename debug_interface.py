#!/usr/bin/env python3
"""
Debug da Interface - Verificar se o botão está visível
"""

import sys
import os
import tkinter as tk
from tkinter import ttk

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_interface():
    """Debug da interface para verificar o botão"""
    try:
        from gui_launcher import AONAutomationGUI
        
        print("🔍 DEBUG DA INTERFACE - VERIFICAÇÃO DO BOTÃO")
        print("=" * 60)
        
        # Criar interface
        app = AONAutomationGUI()
        
        # Informações sobre o botão
        print(f"\n📋 INFORMAÇÕES DO BOTÃO:")
        print(f"   Existe: {'Sim' if hasattr(app, 'execute_btn') else 'Não'}")
        
        if hasattr(app, 'execute_btn'):
            btn = app.execute_btn
            print(f"   Texto: {btn['text']}")
            print(f"   Estado: {btn['state']}")
            print(f"   Classe: {btn.__class__.__name__}")
            
            # Verificar se está empacotado
            pack_info = btn.pack_info()
            print(f"   Pack Info: {pack_info}")
            
            # Verificar geometria
            try:
                print(f"   Posição X: {btn.winfo_x()}")
                print(f"   Posição Y: {btn.winfo_y()}")
                print(f"   Largura: {btn.winfo_width()}")
                print(f"   Altura: {btn.winfo_height()}")
                print(f"   Visível: {'Sim' if btn.winfo_viewable() else 'Não'}")
            except:
                print("   Geometria: Não disponível (janela não renderizada)")
        
        # Informações sobre a janela
        print(f"\n🪟 INFORMAÇÕES DA JANELA:")
        print(f"   Tamanho: {app.root.geometry()}")
        print(f"   Título: {app.root.title()}")
        
        # Preencher credenciais para testar
        print(f"\n🔐 TESTANDO COM CREDENCIAIS:")
        app.username_var.set("A0868855")
        app.password_var.set("teste123")
        
        # Forçar atualização
        app.root.update()
        
        print(f"   Usuário: {app.username_var.get()}")
        print(f"   Senha: {'***' if app.password_var.get() else 'vazia'}")
        print(f"   Texto do botão: {app.execute_btn['text']}")
        print(f"   Estado do botão: {app.execute_btn['state']}")
        
        # Mostrar a interface por 3 segundos para visualizar
        print(f"\n👁️ MOSTRANDO INTERFACE POR 3 SEGUNDOS...")
        app.root.after(3000, app.root.quit)  # Fechar após 3 segundos
        app.run()
        
        print(f"\n✅ DEBUG CONCLUÍDO!")
        
    except Exception as e:
        print(f"❌ Erro no debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_interface()