# Project Allmaid

Assistente pessoal e sistema de automação de tarefas desenvolvido em Python, com interface gráfica leve, integração com Inteligência Artificial, pesquisa na web em tempo real e suporte ao Discord.

## Funcionalidades Principais
- **Automação no Windows:** Abertura e fechamento de aplicativos, pesquisa rápida na web, notícias do dia e gerenciamento controlado de arquivos.
- **Integração com Discord:** Respostas contextuais, controle de modo foco/estudo e gerenciamento de interações no servidor.
- **Memória Persistente:** Armazenamento local em JSON para histórico de consultas e contexto de uso.
- **Tratamento de Erros:** Validação de entradas e registro de logs para evitar travamentos durante a execução.

## Tecnologias Utilizadas
- Python 3
- CustomTkinter (Interface Gráfica)
- API Groq (Processamento de Linguagem Natural)
- Discord.py & DuckDuckGo Search (`ddgs`)

## Como Configurar e Executar
1. Baixe ou clone este repositório.
2. Renomeie o arquivo `.env.example` para `.env` e insira sua chave gratuita da API (`GROQ_API_KEY`).
3. Dê um duplo clique no arquivo **`run.bat`** para instalar as dependências e iniciar o programa automaticamente.
