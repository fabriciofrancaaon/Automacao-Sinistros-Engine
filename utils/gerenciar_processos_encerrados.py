# -*- coding: utf-8 -*-
"""
Utilitário para gerenciar processos encerrados.

Este script permite visualizar, limpar e gerenciar a lista de processos
que foram marcados como encerrados (sem botão editar).
"""

import os
import sys
import json
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.email_service import (
    count_closed_processes, 
    clean_old_closed_processes,
    _load_closed_processes,
    _save_closed_processes
)

def exibir_processos_encerrados():
    """Exibe todos os processos marcados como encerrados"""
    print("=" * 60)
    print("PROCESSOS MARCADOS COMO ENCERRADOS")
    print("=" * 60)
    
    closed_processes = _load_closed_processes()
    
    if not closed_processes:
        print("Nenhum processo marcado como encerrado.")
        return
    
    print(f"Total de processos encerrados: {len(closed_processes)}")
    print()
    
    # Organizar por data
    processes_by_date = {}
    for item in closed_processes:
        try:
            parts = item.split('|')
            numero_sinistro = parts[0]
            data_str = parts[1]
            motivo = parts[2] if len(parts) > 2 else "Não especificado"
            
            data = datetime.fromisoformat(data_str)
            data_formatada = data.strftime("%d/%m/%Y %H:%M:%S")
            
            if data_formatada not in processes_by_date:
                processes_by_date[data_formatada] = []
            
            processes_by_date[data_formatada].append({
                'numero': numero_sinistro,
                'motivo': motivo
            })
        except Exception as e:
            print(f"Erro ao processar item: {item} - {e}")
    
    # Exibir ordenado por data
    for data in sorted(processes_by_date.keys(), reverse=True):
        print(f"\n📅 {data}")
        print("-" * 40)
        for processo in processes_by_date[data]:
            print(f"   🔒 Sinistro: {processo['numero']}")
            print(f"      Motivo: {processo['motivo']}")
            print()

def limpar_processos_antigos():
    """Remove processos encerrados antigos"""
    print("=" * 60)
    print("LIMPEZA DE PROCESSOS ENCERRADOS ANTIGOS")
    print("=" * 60)
    
    antes = count_closed_processes()
    print(f"Processos encerrados antes da limpeza: {antes}")
    
    try:
        dias = int(input("Digite quantos dias manter (padrão 30): ") or "30")
        clean_old_closed_processes(days_to_keep=dias)
        
        depois = count_closed_processes()
        removidos = antes - depois
        
        print(f"Processos encerrados após limpeza: {depois}")
        print(f"Processos removidos: {removidos}")
        
        if removidos > 0:
            print("✅ Limpeza realizada com sucesso!")
        else:
            print("ℹ️ Nenhum processo antigo encontrado para remoção.")
            
    except ValueError:
        print("❌ Valor inválido. Operação cancelada.")
    except Exception as e:
        print(f"❌ Erro durante a limpeza: {e}")

def remover_processo_especifico():
    """Remove um processo específico da lista de encerrados"""
    print("=" * 60)
    print("REMOVER PROCESSO ESPECÍFICO")
    print("=" * 60)
    
    numero_sinistro = input("Digite o número do sinistro para remover: ").strip()
    
    if not numero_sinistro:
        print("❌ Número do sinistro não pode estar vazio.")
        return
    
    closed_processes = _load_closed_processes()
    processo_encontrado = None
    
    # Encontrar o processo
    for item in closed_processes:
        if item.startswith(f"{numero_sinistro}|"):
            processo_encontrado = item
            break
    
    if not processo_encontrado:
        print(f"❌ Processo {numero_sinistro} não encontrado na lista de encerrados.")
        return
    
    # Confirmar remoção
    print(f"Processo encontrado: {processo_encontrado}")
    confirmacao = input("Deseja realmente remover este processo? (s/N): ").strip().lower()
    
    if confirmacao in ['s', 'sim', 'y', 'yes']:
        closed_processes.remove(processo_encontrado)
        
        if _save_closed_processes(closed_processes):
            print(f"✅ Processo {numero_sinistro} removido com sucesso!")
            print("ℹ️ O processo poderá ser processado novamente na próxima execução.")
        else:
            print("❌ Erro ao salvar alterações.")
    else:
        print("Operação cancelada.")

def exportar_lista():
    """Exporta a lista de processos encerrados para um arquivo texto"""
    print("=" * 60)
    print("EXPORTAR LISTA DE PROCESSOS ENCERRADOS")
    print("=" * 60)
    
    closed_processes = _load_closed_processes()
    
    if not closed_processes:
        print("Nenhum processo encerrado para exportar.")
        return
    
    filename = f"processos_encerrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("RELATÓRIO DE PROCESSOS ENCERRADOS\n")
            f.write("=" * 50 + "\n")
            f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Total de processos: {len(closed_processes)}\n\n")
            
            for item in sorted(closed_processes):
                try:
                    parts = item.split('|')
                    numero_sinistro = parts[0]
                    data_str = parts[1]
                    motivo = parts[2] if len(parts) > 2 else "Não especificado"
                    
                    data = datetime.fromisoformat(data_str)
                    data_formatada = data.strftime("%d/%m/%Y %H:%M:%S")
                    
                    f.write(f"Sinistro: {numero_sinistro}\n")
                    f.write(f"Data: {data_formatada}\n")
                    f.write(f"Motivo: {motivo}\n")
                    f.write("-" * 30 + "\n")
                    
                except Exception as e:
                    f.write(f"Erro ao processar: {item} - {e}\n")
        
        print(f"✅ Lista exportada para: {filename}")
        
    except Exception as e:
        print(f"❌ Erro ao exportar: {e}")

def menu_principal():
    """Menu principal do utilitário"""
    while True:
        print("\n" + "=" * 60)
        print("GERENCIADOR DE PROCESSOS ENCERRADOS")
        print("=" * 60)
        print("1. Exibir processos encerrados")
        print("2. Limpar processos antigos")
        print("3. Remover processo específico")
        print("4. Exportar lista")
        print("5. Estatísticas")
        print("0. Sair")
        print("=" * 60)
        
        opcao = input("Escolha uma opção: ").strip()
        
        if opcao == "1":
            exibir_processos_encerrados()
        elif opcao == "2":
            limpar_processos_antigos()
        elif opcao == "3":
            remover_processo_especifico()
        elif opcao == "4":
            exportar_lista()
        elif opcao == "5":
            print(f"\n📊 Total de processos encerrados: {count_closed_processes()}")
        elif opcao == "0":
            print("👋 Encerrando utilitário...")
            break
        else:
            print("❌ Opção inválida. Tente novamente.")
        
        input("\nPressione Enter para continuar...")

if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n👋 Utilitário encerrado pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
