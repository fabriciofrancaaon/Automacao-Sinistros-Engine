#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste para verificar se o remetente do email está sendo extraído corretamente.
"""

import sys
import os
import logging
from datetime import datetime

# Adicionar o diretório raiz ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.email_service import get_emails_24h_new_only, _get_real_sender_email
import win32com.client

def test_sender_extraction():
    """Testa a extração do remetente dos emails"""
    
    print("=" * 60)
    print("🧪 TESTE: Verificação de Extração do Remetente")
    print("=" * 60)
    
    try:
        # 1. Buscar emails das últimas 24h (incluindo todos, sem filtro)
        print("\n📧 Buscando TODOS os emails das últimas 24h (sem filtro)...")
        from services.email_service import get_sent_emails_info, get_inbox_emails_info, _filter_last_24h_exact
        
        # Buscar emails de ambas as caixas
        sent_emails = get_sent_emails_info(days_back=1)
        inbox_emails = get_inbox_emails_info(days_back=1)
        
        # Filtrar últimas 24h
        sent_emails_24h = _filter_last_24h_exact(sent_emails)
        inbox_emails_24h = _filter_last_24h_exact(inbox_emails)
        
        # Combinar
        emails = sent_emails_24h + inbox_emails_24h
        
        print(f"📊 Enviados: {len(sent_emails_24h)}, Recebidos: {len(inbox_emails_24h)}")
        
        if not emails:
            print("❌ Nenhum email encontrado nas últimas 24h")
            return
            
        print(f"✅ Encontrados {len(emails)} emails")
        
        # 2. Analisar os primeiros 5 emails
        print(f"\n🔍 Analisando os primeiros {min(5, len(emails))} emails:")
        print("-" * 60)
        
        for i, email_info in enumerate(emails[:5], 1):
            numero_sinistro = email_info[0] if len(email_info) > 0 else "N/A"
            subject = email_info[1] if len(email_info) > 1 else "N/A"
            to_address = email_info[4] if len(email_info) > 4 else "N/A"
            cc_addresses = email_info[5] if len(email_info) > 5 else "N/A"
            from_address = email_info[6] if len(email_info) > 6 else "N/A"
            sent_time = email_info[7] if len(email_info) > 7 else "N/A"
            
            print(f"\n📬 EMAIL {i}:")
            print(f"   🔢 Sinistro: {numero_sinistro}")
            print(f"   📝 Assunto: {subject[:50]}{'...' if len(subject) > 50 else ''}")
            print(f"   📨 Para: {to_address}")
            print(f"   📋 CC: {cc_addresses}")
            print(f"   👤 De: {from_address}")
            print(f"   🕐 Enviado: {sent_time}")
            
            # Verificar se é um código em vez de email
            if from_address and not from_address.startswith("N/A"):
                if '@' in from_address:
                    if from_address.startswith('/'):
                        print(f"   ⚠️  CÓDIGO EXCHANGE DETECTADO!")
                    else:
                        print(f"   ✅ Email válido")
                else:
                    print(f"   ❌ Não parece ser um email válido")
            
        # 3. Teste direto com Outlook (opcional)
        print(f"\n🔬 Teste direto com Outlook...")
        test_direct_outlook()
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()

def test_direct_outlook():
    """Testa diretamente com objeto Outlook"""
    try:
        import win32com.client
        import pythoncom
        
        # Inicializar COM
        try:
            pythoncom.CoInitialize()
        except:
            pass
            
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        inbox = outlook.GetDefaultFolder(6)  # Inbox
        
        messages = inbox.Items
        messages.Sort("[ReceivedTime]", True)
        
        print(f"📬 Testando extração DETALHADA do Outlook...")
        
        # Pegar apenas a primeira mensagem para teste detalhado
        count = 0
        for message in messages:
            if count >= 1:
                break
                
            try:
                print(f"\n🔍 ANÁLISE DETALHADA - MENSAGEM {count + 1}:")
                print(f"   📝 Assunto: {message.Subject[:50]}...")
                
                # Testar todas as propriedades disponíveis
                print(f"\n   🔬 PROPRIEDADES TESTADAS:")
                
                # 1. SenderEmailAddress
                try:
                    sender_email = getattr(message, 'SenderEmailAddress', 'N/A')
                    print(f"   1️⃣ SenderEmailAddress: {sender_email[:100]}...")
                except Exception as e:
                    print(f"   1️⃣ SenderEmailAddress: ERRO - {e}")
                
                # 2. Sender.Address
                try:
                    if hasattr(message, 'Sender') and message.Sender:
                        sender_addr = getattr(message.Sender, 'Address', 'N/A')
                        print(f"   2️⃣ Sender.Address: {sender_addr[:100]}...")
                    else:
                        print(f"   2️⃣ Sender.Address: N/A")
                except Exception as e:
                    print(f"   2️⃣ Sender.Address: ERRO - {e}")
                
                # 3. Sender.Name
                try:
                    if hasattr(message, 'Sender') and message.Sender:
                        sender_name = getattr(message.Sender, 'Name', 'N/A')
                        print(f"   3️⃣ Sender.Name: {sender_name}")
                    else:
                        print(f"   3️⃣ Sender.Name: N/A")
                except Exception as e:
                    print(f"   3️⃣ Sender.Name: ERRO - {e}")
                
                # 4. SenderName
                try:
                    sender_name = getattr(message, 'SenderName', 'N/A')
                    print(f"   4️⃣ SenderName: {sender_name}")
                except Exception as e:
                    print(f"   4️⃣ SenderName: ERRO - {e}")
                
                # 5. Author
                try:
                    author = getattr(message, 'Author', 'N/A')
                    print(f"   5️⃣ Author: {author}")
                except Exception as e:
                    print(f"   5️⃣ Author: ERRO - {e}")
                
                # 6. Propriedades MAPI
                try:
                    mapi_sender = message.PropertyAccessor.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x0C1F001E")
                    print(f"   6️⃣ MAPI PR_SENDER_EMAIL_ADDRESS: {mapi_sender[:100]}...")
                except Exception as e:
                    print(f"   6️⃣ MAPI PR_SENDER_EMAIL_ADDRESS: ERRO - {e}")
                
                # 7. MAPI Representing
                try:
                    mapi_repr = message.PropertyAccessor.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x0065001E")
                    print(f"   7️⃣ MAPI PR_SENT_REPRESENTING_EMAIL: {mapi_repr[:100]}...")
                except Exception as e:
                    print(f"   7️⃣ MAPI PR_SENT_REPRESENTING_EMAIL: ERRO - {e}")
                
                print(f"\n   🚀 RESULTADO DA FUNÇÃO MELHORADA:")
                # Método melhorado
                from services.email_service import _get_real_sender_email
                sender_melhorado = _get_real_sender_email(message)
                print(f"   ✅ Email Final: {sender_melhorado}")
                    
                count += 1
                
            except Exception as msg_error:
                print(f"   ❌ Erro ao processar mensagem: {msg_error}")
                count += 1
                continue
                
    except Exception as e:
        print(f"❌ Erro no teste direto: {e}")

def main():
    """Função principal do teste"""
    
    # Configurar logging básico
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Iniciando teste de remetente...")
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    test_sender_extraction()
    
    print("\n" + "=" * 60)
    print("✅ Teste concluído!")
    print("=" * 60)

if __name__ == "__main__":
    main()