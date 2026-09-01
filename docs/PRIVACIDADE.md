# Privacidade e tratamento de dados

## Dados processados

Dependendo do comando, a aplicação pode ler remetente, assunto, prévia, partes textuais do corpo e marcadores de mensagens. Esses dados podem conter informações pessoais ou sigilosas.

## Processamento local

Consultas, regras determinísticas, aplicação de marcadores e geração do PDF acontecem na máquina da pessoa usuária, com comunicação direta com a API do Gmail.

## Processamento pelo Gemini

Quando `--allow-ai-processing` é informado, o programa pode enviar ao Gemini:

- assunto;
- prévia da mensagem;
- trecho limitado do corpo;
- nomes de categorias e instruções de classificação.

O projeto não deve ser demonstrado com e-mails reais sem base legal, consentimento adequado e revisão das condições do provedor. Para atividades acadêmicas, prefira uma conta de teste e mensagens sintéticas.

## Retenção

O projeto não mantém banco de dados próprio. Entretanto, tokens OAuth e relatórios PDF são gravados localmente. O tratamento posterior desses arquivos é responsabilidade de quem executa a aplicação.

## Controles da pessoa usuária

- `--dry-run`: impede alterações no Gmail;
- ausência de `--allow-ai-processing`: impede o envio de conteúdo ao Gemini;
- ausência de `--confirm-trash`: impede operações de lixeira;
- revogação OAuth: encerra o acesso concedido à aplicação.
