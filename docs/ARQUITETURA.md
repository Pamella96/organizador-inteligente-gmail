# Arquitetura

## Visão geral

O projeto segue uma separação simples entre autenticação, configuração de domínio, orquestração e apresentação:

```text
CLI (main.py)
  ├─ autenticação (auth.py) ── Gmail API
  ├─ catálogo (services.py)
  ├─ classificação opcional ── Gemini API
  └─ relatório (relatorio_pdf.py) ── PDF local
```

## Fluxo principal

1. A pessoa escolhe uma ação na CLI.
2. `auth.py` obtém ou renova a autorização OAuth.
3. `main.py` consulta mensagens conforme as regras do serviço.
4. Regras locais filtram domínio, assunto e remetente.
5. Quando `--allow-ai-processing` é informado, trechos podem ser enviados ao Gemini.
6. O programa calcula as alterações de marcadores.
7. `--dry-run` exibe a intenção; sem ele, as alterações são aplicadas em lotes.
8. Operações de lixeira ainda exigem `--confirm-trash`.

## Decisões

- `services.py` é declarativo para facilitar a inclusão de novos serviços sem duplicar o motor.
- A IA é opcional; sem autorização, os sincronizadores usam a categoria padrão.
- O programa não executa uma ação implícita quando chamado sem argumentos.
- Testes automatizados não dependem de contas ou serviços externos.

## Limitações conhecidas

- `main.py` ainda concentra muitos casos de uso e deve ser modularizado apenas quando houver testes de regressão suficientes.
- O gerador de PDF usa fontes do Windows e precisa de fallback portátil.
- A precisão das classificações depende das regras, do conteúdo disponível e do modelo externo.
- O histórico Git original precisa ser higienizado antes da publicação.
