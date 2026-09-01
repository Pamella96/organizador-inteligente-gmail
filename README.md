# Organizador Inteligente de E-mails

[![CI](https://github.com/Pamella96/organizador-inteligente-gmail/actions/workflows/ci.yml/badge.svg)](https://github.com/Pamella96/organizador-inteligente-gmail/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue.svg)](LICENSE)

Projeto pessoal com aplicação acadêmica para organização assistida de mensagens do Gmail. A aplicação combina regras determinísticas e, quando autorizada explicitamente, o Gemini para classificar e-mails, aplicar marcadores e gerar um relatório em PDF.

> [!IMPORTANT]
> Este repositório não contém credenciais. Use chaves próprias, mantenha `credentials.json` e `token.json` somente na máquina local e faça os primeiros testes com uma conta separada.

## Objetivo acadêmico

Investigar como automação, classificação por IA e controles de privacidade podem reduzir o esforço de organização de caixas de entrada sem retirar do usuário o controle sobre ações destrutivas ou sobre o envio de conteúdo a serviços externos.

## Funcionalidades

- autenticação OAuth 2.0 com a API do Gmail;
- classificação por serviço com regras configuradas em `services.py`;
- classificação opcional com Gemini;
- criação de marcadores hierárquicos no Gmail;
- modo de simulação com `--dry-run`;
- confirmação explícita para envio de conteúdo à IA e para uso da lixeira;
- relatório local em PDF com categorias e urgência.

## Estrutura

```text
core.py             utilitários puros e regras de segurança testáveis
auth.py             autenticação e criação do cliente Gmail
main.py             CLI e casos de uso
services.py         catálogo declarativo de serviços e categorias
relatorio_pdf.py    geração do relatório local
docs/               arquitetura, privacidade e decisões acadêmicas
tests/              testes unitários sem acesso ao Gmail
```

Detalhes em [docs/ARQUITETURA.md](docs/ARQUITETURA.md) e [docs/PRIVACIDADE.md](docs/PRIVACIDADE.md).

## Requisitos

- Python 3.11 ou superior;
- projeto no Google Cloud com a Gmail API habilitada;
- cliente OAuth do tipo aplicativo para computador;
- chave da API Gemini, somente para os modos que usam IA.

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Baixe o cliente OAuth no Google Cloud, salve-o localmente como `credentials.json` e nunca o adicione ao Git. Na primeira autenticação, `token.json` será criado localmente e também deve permanecer fora do repositório.

Para os recursos de IA, configure a chave apenas no ambiente:

```powershell
$env:GEMINI_API_KEY = "sua-chave"
```

## Uso seguro

Sem uma ação explícita, o programa não altera a caixa de entrada:

```powershell
python main.py --help
python main.py --sync-spotify --dry-run
```

O envio de assunto, prévia e trechos do corpo ao Gemini exige autorização para a execução atual:

```powershell
python main.py --sync-spotify --allow-ai-processing --dry-run
```

Operações que movem mensagens para a lixeira exigem `--confirm-trash`. Faça primeiro uma simulação:

```powershell
python main.py --process-inbox --allow-ai-processing --dry-run
python main.py --process-inbox --allow-ai-processing --confirm-trash
```

## Segurança e privacidade

- Não use credenciais que já tenham sido versionadas.
- O escopo OAuth atual é `gmail.modify`, necessário para aplicar marcadores e mover mensagens.
- `--dry-run` impede alterações no Gmail, mas não impede processamento externo; use também o controle `--allow-ai-processing` conscientemente.
- E-mails podem conter dados pessoais, financeiros e acadêmicos. Use uma conta de teste e dados sintéticos nas demonstrações públicas.

Consulte [SECURITY.md](SECURITY.md) para reporte de vulnerabilidades.

## Desenvolvimento

```powershell
python -m unittest discover -s tests -v
python -m compileall -q .
```

As contribuições devem seguir [CONTRIBUTING.md](CONTRIBUTING.md).

## Licença

Distribuído sob a licença MIT. Consulte [LICENSE](LICENSE).

Este é um projeto independente, sem vínculo ou endosso do Google.
