# Política de segurança

## Versões suportadas

O projeto está em fase acadêmica e somente a versão mais recente da branch principal recebe correções.

## Como reportar uma vulnerabilidade

Não abra uma issue pública contendo credenciais, tokens, conteúdo de e-mails ou dados pessoais. Após a publicação no GitHub, prefira um aviso privado pela opção **Security → Report a vulnerability** do repositório.

Inclua apenas:

- versão ou commit afetado;
- passos mínimos para reprodução com dados sintéticos;
- impacto esperado;
- sugestão de correção, se houver.

## Segredos

Nunca versione `credentials.json`, `token.json`, `.env` ou chaves de API. Se um segredo for incluído em um commit:

1. revogue ou rotacione o segredo imediatamente;
2. remova-o da versão atual;
3. reescreva o histórico antes de tornar o repositório público;
4. verifique forks, artefatos e logs que possam conter cópias.

## Modelo de ameaças resumido

Os principais riscos são acesso indevido à conta Gmail, vazamento de conteúdo ao provedor de IA, classificação incorreta e ações destrutivas sobre mensagens. Os controles atuais são escopo OAuth documentado, segredos fora do Git, autorização explícita para IA, simulação e confirmação adicional para lixeira.
