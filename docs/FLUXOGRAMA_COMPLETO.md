# 🔄 FLUXOGRAMA COMPLETO - AUTOMAÇÃO DE SINISTROS AON

## 📋 Visão Geral

Este documento descreve o fluxograma completo da automação de sinistros, incluindo todos os caminhos possíveis, decisões, fallbacks e tratamentos de erro.

---

## 🚀 FASE 1: INICIALIZAÇÃO DO SISTEMA

### 1.1 Carregamento de Variáveis de Ambiente
```
INÍCIO → Carregar .env → Verificar variáveis obrigatórias
├─ ✅ Sucesso: Continuar para 1.2
└─ ❌ Falha: PARAR execução
```

### 1.2 Configuração do Sistema de Logs
```
Logger Setup → Configurar arquivo de log → Definir níveis
├─ ✅ Sucesso: Continuar para 1.3
└─ ❌ Falha: PARAR execução
```

### 1.3 Carregamento de Configurações
```
Configurações → MAX_RETRIES → LOGIN_ERROR_MESSAGE
├─ ✅ Sucesso: Continuar para 1.4
└─ ❌ Falha: Usar valores padrão
```

### 1.4 Inicialização de Estruturas de Controle
```
Listas de Controle → processed_list → non_processed_list
└─ ✅ Continuar para FASE 2
```

---

## 🧹 FASE 2: LIMPEZA E PREPARAÇÃO

### 2.1 Limpeza de Emails Antigos
```
Buscar emails processados → Filtrar > 7 dias → Remover registros
├─ ✅ Sucesso: Continuar para 2.2
├─ ⚠️ Aviso: Continuar mesmo com erros
└─ ❌ Erro: Log erro e continuar
```

### 2.2 Limpeza de Processos Encerrados
```
Buscar processos encerrados → Filtrar > 30 dias → Remover registros
├─ ✅ Sucesso: Continuar para FASE 3
├─ ⚠️ Aviso: Continuar mesmo com erros
└─ ❌ Erro: Log erro e continuar
```

---

## 📧 FASE 3: OBTENÇÃO DE EMAILS

### 3.1 Conectar ao Outlook
```
Conectar Outlook → Acessar caixa de entrada → Verificar conectividade
├─ ✅ Sucesso: Continuar para 3.2
└─ ❌ Falha: PARAR execução
```

### 3.2 Filtrar Emails das Últimas 24h
```
Obter emails → Filtrar por data → Aplicar critérios
├─ ✅ Emails encontrados: Continuar para 3.3
├─ ℹ️ Nenhum email: Pular para FASE 6 (Relatórios)
└─ ❌ Erro: PARAR execução
```

### 3.3 Filtrar Emails Novos (Não Processados)
```
Para cada email:
├─ Verificar se já foi processado
├─ ✅ Novo: Adicionar à fila
├─ ⚠️ Já processado: Pular (se controle ativo)
└─ ❌ Erro na verificação: Adicionar à fila
```

### 3.4 Validação da Fila de Emails
```
Fila final → Contar emails → Validar dados
├─ ✅ Fila válida: Continuar para FASE 4
├─ ℹ️ Fila vazia: Pular para FASE 6
└─ ❌ Erro: PARAR execução
```

---

## 🔐 FASE 4: VALIDAÇÃO DE CREDENCIAIS

### 4.1 Obter Credenciais
```
Buscar credenciais → URL, USERNAME, PASSWORD
├─ ✅ Todas presentes: Continuar para FASE 5
└─ ❌ Faltando dados: PARAR execução
```

---

## ⚙️ FASE 5: PROCESSAMENTO DE EMAILS

### 5.1 Loop Principal da Fila
```
Para cada email na fila (índice 1 até N):
├─ PASSO 1: Validar número do sinistro
├─ PASSO 2: Verificar se processo está encerrado
├─ PASSO 3: Loop de tentativas (até MAX_RETRIES)
└─ Atualizar listas de controle
```

### PASSO 1: Validação do Número do Sinistro
```
Verificar número do sinistro:
├─ ✅ Válido (6 dígitos, inicia com 6): Continuar PASSO 2
├─ ❌ Inválido: Marcar como falha e próximo email
└─ ⚠️ Erro na validação: Log aviso e continuar
```

### PASSO 2: Verificação de Processo Encerrado
```
Consultar base de processos encerrados:
├─ ✅ Processo ativo: Continuar PASSO 3
├─ ⏹️ Processo encerrado: Marcar como falha e próximo email
└─ ⚠️ Erro na consulta: Log aviso e continuar
```

### PASSO 3: Loop de Tentativas (Por Email)
```
Para tentativa 1 até MAX_RETRIES:
├─ SUB-PASSO 3.1: Configurar navegador
├─ SUB-PASSO 3.2: Realizar login
├─ SUB-PASSO 3.3: Executar navegação e ações
├─ SUB-PASSO 3.4: Finalizar (sucesso/erro)
└─ Limpar recursos
```

#### SUB-PASSO 3.1: Configuração do Navegador
```
Setup WebDriver:
├─ ✅ Navegador iniciado: Continuar 3.2
└─ ❌ Falha na inicialização: Próxima tentativa
```

#### SUB-PASSO 3.2: Realizar Login
```
Login no sistema AON:
├─ Acessar URL → Inserir credenciais → Verificar sucesso
├─ ✅ Login bem-sucedido: Continuar 3.3
└─ ❌ Falha no login: Próxima tentativa
```

#### SUB-PASSO 3.3: Navegação e Ações (核心)
```
Executar fluxo de navegação:
├─ Resultado 1: Sucesso completo
├─ Resultado -1: Processo encerrado (histórico atualizado)
├─ Resultado 0: Falha geral
└─ Ver FLUXO DE NAVEGAÇÃO detalhado abaixo
```

#### SUB-PASSO 3.4: Finalização
```
Baseado no resultado da navegação:
├─ ✅ Sucesso (1): Enviar email confirmação → Retornar True
├─ 🔒 Encerrado (-1): Enviar email confirmação → Retornar True
├─ ❌ Falha (0): Se última tentativa → Enviar email erro
└─ 🔄 Falha: Próxima tentativa
```

---

## 🧭 FLUXO DE NAVEGAÇÃO DETALHADO (NavigationManager)

### ETAPA N1: Navegação para Menu de Sinistros
```
Localizar menu de sinistros:
├─ Método 1: Seletor direto
├─ Método 2: JavaScript (fallback)
├─ ✅ Sucesso: Continuar N2
└─ ❌ Falha: Retornar 0
```

### ETAPA N2: Acessar Opção de Busca
```
Clicar em "Buscar":
├─ Método 1: Selenium click
├─ Método 2: JavaScript (fallback)
├─ ✅ Sucesso: Continuar N3
└─ ❌ Falha: Retornar 0
```

### ETAPA N3: Configurar Vista Padrão
```
Setup da vista de busca:
├─ Preencher campo de busca → Selecionar "Vista Padrão"
├─ ✅ Sucesso: Continuar N4
└─ ❌ Falha: Retornar 0
```

### ETAPA N4: Buscar Sinistro
```
Buscar por número do sinistro:
├─ Inserir número → Executar busca → Aguardar resultados
├─ ✅ Sinistro encontrado: Continuar N5
└─ ❌ Sinistro não encontrado: Retornar 0
```

### ETAPA N5: Abrir Sinistro
```
Abrir sinistro encontrado:
├─ Clicar no resultado → Aguardar carregamento
├─ ✅ Sinistro aberto: Continuar N6
└─ ❌ Falha ao abrir: Retornar 0
```

### ETAPA N6: Verificar Status do Processo
```
Verificar se processo está encerrado:
├─ ✅ Processo ativo: Continuar N7 (fluxo normal)
├─ 🔒 Processo encerrado: Continuar N6.1 (fluxo encerrado)
└─ ❌ Erro na verificação: Retornar 0
```

#### FLUXO N6.1: Processo Encerrado (Histórico Apenas)
```
Adicionar apenas ao histórico:
├─ Acessar aba "Histórico"
├─ Adicionar entrada no histórico
├─ Preencher dados do email
├─ Salvar alterações
├─ ✅ Sucesso: Retornar -1 (encerrado mas atualizado)
└─ ❌ Falha: Retornar 0
```

### ETAPA N7: Editar Sinistro (Processo Ativo)
```
Habilitar edição:
├─ Clicar botão "Editar" → Aguardar modo edição
├─ ✅ Edição habilitada: Continuar N8
└─ ❌ Falha na edição: Retornar 0
```

### ETAPA N8: Acessar Opções/Histórico
```
Navegar para histórico:
├─ Clicar "Opções" → Selecionar "Histórico"
├─ ✅ Histórico acessado: Continuar N9
└─ ❌ Falha no acesso: Retornar 0
```

### ETAPA N9: Adicionar Entrada no Histórico
```
Criar nova entrada:
├─ Clicar "Adicionar Atualização"
├─ ✅ Formulário aberto: Continuar N10
└─ ❌ Falha ao abrir: Retornar 0
```

### ETAPA N10: Preencher Formulário do Histórico
```
Preencher campos obrigatórios:
├─ N10.1: Preencher Tipo de Informe (00029)
├─ N10.2: Preencher Observações (cabeçalho do email)
├─ N10.3: Preencher Comentários (corpo do email) - VIA CLIPBOARD
├─ ✅ Todos preenchidos: Continuar N11
└─ ❌ Falha em algum campo: Retornar 0
```

#### DETALHAMENTO N10.3: Preenchimento de Comentários
```
Método de preenchimento por CLIPBOARD:
├─ Salvar clipboard atual
├─ Copiar texto do email para clipboard
├─ Clicar no campo de comentários
├─ Colar conteúdo (Ctrl+V)
├─ Restaurar clipboard original
├─ ✅ Sucesso: Continuar
└─ ❌ Falha: Fallback para send_keys
```

### ETAPA N11: Salvar Histórico
```
Salvar entrada do histórico:
├─ Clicar botão "Salvar" → Aguardar confirmação
├─ ✅ Histórico salvo: Continuar N12
└─ ❌ Falha ao salvar: Retornar 0
```

### ETAPA N12: Atualizar Campo Telefone
```
Atualizar informações de contato:
├─ Localizar campo telefone → Inserir/Atualizar número
├─ ✅ Telefone atualizado: Continuar N13
├─ ⚠️ Campo não encontrado: Log aviso e continuar N13
└─ ❌ Erro crítico: Retornar 0
```

### ETAPA N13: Salvar Alterações Finais
```
Salvar todas as alterações:
├─ Clicar "Salvar Edição" → Aguardar confirmação
├─ ✅ Alterações salvas: Retornar 1 (SUCESSO)
└─ ❌ Falha ao salvar: Retornar 0
```

---

## 📊 FASE 6: GERAÇÃO DE RELATÓRIOS

### 6.1 Compilar Resultados
```
Processar listas de controle:
├─ Contar sucessos (processed_list)
├─ Contar falhas (non_processed_list)
├─ Calcular estatísticas
└─ Preparar dados para relatório
```

### 6.2 Gerar Relatório Detalhado
```
Criar relatório final:
├─ Cabeçalho com horários
├─ Resumo executivo
├─ Lista detalhada de processados
├─ Lista detalhada de falhas
├─ Estatísticas finais
└─ Informações do sistema
```

### 6.3 Enviar Relatório por Email
```
Distribuir relatório:
├─ Preparar email de relatório
├─ Anexar logs (se configurado)
├─ Enviar para destinatários
├─ ✅ Sucesso: Log confirmação
└─ ❌ Falha: Log erro
```

### 6.4 Finalização
```
Limpeza final:
├─ Fechar conexões
├─ Salvar logs finais
├─ Liberar recursos
└─ TERMINAR execução
```

---

## 🔀 CAMINHOS DE DECISÃO E FALLBACKS

### 🎯 Principais Pontos de Decisão

| Condição | Caminho A (✅) | Caminho B (❌) | Fallback |
|----------|---------------|---------------|----------|
| **Emails encontrados** | Processar fila | Pular para relatórios | - |
| **Sinistro válido** | Continuar processamento | Próximo email | - |
| **Processo encerrado** | Apenas histórico | Falha | - |
| **Login bem-sucedido** | Continuar navegação | Próxima tentativa | Retry |
| **Elemento não encontrado** | Método Selenium | Fallback JavaScript | Timeout |
| **Campo não preenchível** | Método send_keys | Clipboard ou JS | Falha |
| **Sinistro não encontrado** | - | Falha na tentativa | Retry |

### 🔄 Sistemas de Fallback

#### 1. **Fallback para Interação com Elementos**
```
Selenium Direto → JavaScript → Falha
├─ Selenium: Método preferido
├─ JavaScript: Quando Selenium falha
└─ Falha: Log erro e continuar
```

#### 2. **Fallback para Preenchimento de Campos**
```
Clipboard → send_keys → JavaScript → Falha
├─ Clipboard: Método para comentários longos
├─ send_keys: Método padrão
├─ JavaScript: Para campos especiais
└─ Falha: Log erro
```

#### 3. **Fallback para Busca de Elementos**
```
ID Direto → XPath → CSS Selector → JavaScript
├─ ID: Mais rápido e confiável
├─ XPath: Para elementos complexos
├─ CSS: Para seletores específicos
└─ JavaScript: Último recurso
```

---

## ⚠️ TRATAMENTO DE ERROS E EXCEÇÕES

### 🚨 Erros Críticos (Param execução)
- Falha no carregamento de variáveis de ambiente
- Impossibilidade de conectar ao Outlook
- Credenciais inválidas ou ausentes
- Falha na inicialização do WebDriver (todas as tentativas)

### ⚠️ Erros Recuperáveis (Retry)
- Falha temporária no login
- Timeout na busca de elementos
- Erro de rede temporário
- Elemento temporariamente não interativo

### ℹ️ Avisos (Continuar execução)
- Campo telefone não encontrado
- Processo já encerrado
- Sinistro não encontrado
- Erro na validação de número

---

## 📈 MÉTRICAS E MONITORAMENTO

### 📊 Métricas Coletadas
- **Tempo total de execução**
- **Número de emails processados**
- **Taxa de sucesso (%)**
- **Número de tentativas por email**
- **Tempo médio por processamento**
- **Tipos de erro mais comuns**

### 📝 Logs Gerados
- **Log principal**: Todas as operações
- **Log de erro**: Apenas erros e avisos
- **Log de performance**: Tempos e métricas
- **Screenshots**: Capturas em caso de erro

### 📧 Notificações
- **Email de confirmação**: Para cada sinistro processado
- **Email de erro**: Para falhas críticas
- **Relatório consolidado**: Resumo da execução
- **Alertas de sistema**: Para monitoramento

---

## 🔧 CONFIGURAÇÕES E PARÂMETROS

### ⚙️ Variáveis de Ambiente Principais
- `MAX_RETRIES`: Máximo de tentativas por email (padrão: 3)
- `LOGIN_ERROR_MESSAGE`: Mensagem de erro personalizada
- `AON_URL`: URL do sistema AON
- `AON_USERNAME`: Usuário do sistema
- `AON_PASSWORD`: Senha do sistema

### 🎛️ Configurações de Comportamento
- **Timeout padrão**: 30 segundos
- **Timeout longo**: 60 segundos
- **Timeout curto**: 10 segundos
- **Delay entre ações**: 1-3 segundos
- **Chunk size para texto**: 500 caracteres

---

## 📋 RESUMO DOS CÓDIGOS DE RETORNO

| Código | Significado | Ação |
|--------|-------------|------|
| **1** | ✅ Sucesso completo | Email confirmação + próximo |
| **0** | ❌ Falha geral | Retry ou email erro |
| **-1** | 🔒 Processo encerrado (histórico OK) | Email confirmação + próximo |

---

*Documentação atualizada em: {{ current_date }}*
*Versão do sistema: Automação de Sinistros AON v2.0*