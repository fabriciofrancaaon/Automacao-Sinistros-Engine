# Sistema de Automação de Sinistros AON

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Sistema profissional de automação para processamento de sinistros da AON, desenvolvido com arquitetura limpa e padrões de desenvolvimento modernos.

## 🚀 Funcionalidades

- **Processamento Automático**: Processa emails de sinistros automaticamente
- **Integração Outlook**: Conecta diretamente com o Microsoft Outlook
- **Automação Web**: Utiliza Selenium para navegação no sistema AON
- **Monitoramento**: Sistema de monitoramento em tempo real
- **Relatórios**: Geração automática de relatórios de processamento
- **Logs Detalhados**: Sistema completo de logging com diferentes níveis
- **Screenshots**: Captura automática de telas para auditoria
- **Recuperação de Falhas**: Tratamento robusto de erros com fallbacks

## 📁 Estrutura do Projeto

```
automacao_sinistros/
├── automacao_sinistros/           # Código fonte principal
│   ├── core/                     # Módulos principais
│   │   └── main.py              # Ponto de entrada principal
│   ├── services/                # Serviços de negócio
│   │   ├── email_service.py     # Gerenciamento de emails
│   │   ├── login_service.py     # Autenticação AON
│   │   └── navigation_service.py # Navegação web
│   ├── utils/                   # Utilitários
│   │   ├── helpers.py           # Funções auxiliares
│   │   ├── screenshot_manager.py # Gerenciamento de screenshots
│   │   └── webdriver_setup.py   # Configuração do WebDriver
│   └── monitors/                # Monitores de sistema
│       └── file_monitor.py      # Monitor de arquivos
├── config/                      # Configurações
├── data/                        # Dados e templates
├── logs/                        # Arquivos de log
├── screenshots/                 # Capturas de tela
│   ├── errors/                  # Screenshots de erros
│   └── general/                 # Screenshots gerais
├── tests/                       # Testes automatizados
├── .env                         # Variáveis de ambiente
├── requirements.txt             # Dependências Python
├── pyproject.toml              # Configuração moderna do projeto
└── executar.bat                # Script de execução Windows
```

## 🛠️ Pré-requisitos

### Software Necessário
- **Python 3.12+** - [Download Python](https://www.python.org/downloads/)
- **Google Chrome** - Navegador para automação web
- **Microsoft Outlook** - Para integração de email
- **Windows 10/11** - Sistema operacional suportado

### Dependências Python
```bash
selenium>=4.27.0       # Automação web
webdriver-manager>=4.0.0 # Gerenciamento do ChromeDriver
python-dotenv>=1.0.0    # Variáveis de ambiente
pywin32>=308           # Integração Windows/Outlook
requests>=2.32.0       # Requisições HTTP
pandas>=2.2.0          # Manipulação de dados
watchdog>=4.0.0        # Monitoramento de arquivos
```

## ⚙️ Instalação

### 1. Clone o Repositório
```bash
git clone https://github.com/aon/automacao-sinistros.git
cd automacao-sinistros
```

### 2. Configurar Ambiente Virtual
```bash
# Criar ambiente virtual
python -m venv env

# Ativar ambiente (Windows)
env\Scripts\activate

# Ativar ambiente (Linux/Mac)
source env/bin/activate
```

### 3. Instalar Dependências
```bash
# Instalação básica
pip install -r requirements.txt

# Ou instalação com desenvolvimento
pip install -e .[dev]
```

### 4. Configurar Variáveis de Ambiente
Copie o arquivo `.env.example` para `.env` e configure:

```env
# Credenciais AON
AON_USERNAME=seu_usuario
AON_PASSWORD=sua_senha
AON_URL=https://aon-access.com

# Configurações de Email
EMAIL_FOLDER=ALARME AUTOMATICO
EMAIL_SUBJECT_LIST=Sinistro,Claim,Aviso
EMAIL_TO_PROCESSED=relatorios@aon.com
EMAIL_SUBJECT_PROCESSED=Processamento Concluído

# Caminhos e Configurações
PROCESSED_CLAIMS_DIR=./data/processados
LOG_FILENAME_PREFIX=automacao_sinistros
SCREENSHOTS_DIR=./screenshots

# Configurações Avançadas
HEADLESS_MODE=false
DEBUG_MODE=true
MAX_RETRIES=3
TIMEOUT_SECONDS=30
```

## 🚀 Uso

### Execução Básica
```bash
# Executar processamento único
python -m automacao_sinistros.core.main

# Ou usar o script de conveniência
./executar.bat
```

### Execução com Monitoramento
```bash
# Monitoramento contínuo de emails
python -m automacao_sinistros.monitors.file_monitor

# Ou usar o script de monitor
./monitor.bat
```

### Modos de Execução

#### Modo Interativo
```bash
python -m automacao_sinistros.core.main --interactive
```

#### Modo Headless (sem interface gráfica)
```bash
python -m automacao_sinistros.core.main --headless
```

#### Modo Debug (com logs detalhados)
```bash
python -m automacao_sinistros.core.main --debug
```

## 📊 Monitoramento e Logs

### Logs do Sistema
- **Localização**: `./logs/`
- **Formato**: `automacao_sinistros_YYYYMMDD_HHMMSS.log`
- **Níveis**: INFO, WARNING, ERROR, DEBUG

### Screenshots Automáticos
- **Erros**: `./screenshots/errors/`
- **Gerais**: `./screenshots/general/`
- **Limpeza**: Arquivos antigos removidos automaticamente (30 dias)

### Relatórios
- **Processados**: Lista de sinistros processados com sucesso
- **Falhas**: Relatório de erros e falhas no processamento
- **Estatísticas**: Métricas de performance e tempo de execução

## 🧪 Testes

### Executar Testes
```bash
# Todos os testes
pytest

# Testes específicos
pytest tests/test_email_service.py

# Com cobertura
pytest --cov=automacao_sinistros
```

### Tipos de Teste
- **Unitários**: Testam funções individuais
- **Integração**: Testam interação entre módulos
- **E2E**: Testam fluxo completo do sistema

## 🔧 Desenvolvimento

### Configuração do Ambiente de Desenvolvimento
```bash
# Instalar dependências de desenvolvimento
pip install -e .[dev]

# Configurar hooks de pré-commit
pre-commit install
```

### Padrões de Código
- **Formatação**: Black (line-length=88)
- **Linting**: Flake8 + MyPy
- **Documentação**: Docstrings no padrão Google
- **Imports**: Ordenação automática com isort

### Estrutura de Commits
```
tipo(escopo): descrição

feat(email): adicionar suporte a anexos
fix(login): corrigir timeout de autenticação
docs(readme): atualizar instruções de instalação
```

## 📈 Performance

### Otimizações Implementadas
- **WebDriver**: Configurações otimizadas para performance
- **Memory Management**: Limpeza automática de recursos
- **Parallel Processing**: Processamento paralelo quando possível
- **Caching**: Cache de configurações e dados frequentes

### Métricas Típicas
- **Tempo por sinistro**: 2-5 minutos
- **Taxa de sucesso**: >95%
- **Uso de memória**: <500MB
- **Tolerância a falhas**: 3 tentativas automáticas

## 🚨 Solução de Problemas

### Problemas Comuns

#### WebDriver não encontrado
```bash
# Reinstalar webdriver-manager
pip install --upgrade webdriver-manager
```

#### Timeout de login
```env
# Aumentar timeout no .env
TIMEOUT_SECONDS=60
```

#### Erro de permissões do Outlook
```bash
# Executar como administrador
# Verificar configurações de segurança do Outlook
```

### Logs de Debug
Para diagnóstico detalhado, ativar modo debug:
```bash
python -m automacao_sinistros.core.main --debug --log-level=DEBUG
```

## 📄 Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.

## 👥 Contribuição

1. Faça um Fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📞 Suporte

- **Email**: suporte-automacao@aon.com
- **Teams**: Canal #automacao-sinistros
- **Documentação**: [Wiki do Projeto](https://github.com/aon/automacao-sinistros/wiki)

## 🔄 Roadmap

### Próximas Versões
- [ ] **v2.1**: Interface web para monitoramento
- [ ] **v2.2**: Integração com API REST
- [ ] **v2.3**: Suporte a múltiplas bases de dados
- [ ] **v3.0**: Arquitetura de microserviços

### Melhorias Planejadas
- [ ] Dashboard em tempo real
- [ ] Notificações via Teams/Slack
- [ ] Machine Learning para classificação automática
- [ ] Integração com Power BI

---

**Desenvolvido pela equipe de Inovação AON**
