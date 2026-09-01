# Como contribuir

## Fluxo de trabalho

1. Crie uma branch curta a partir da branch principal.
2. Faça mudanças pequenas e relacionadas a um único objetivo.
3. Não use mensagens ou credenciais reais em testes, issues ou commits.
4. Execute os testes e a compilação estática local.
5. Explique no pull request o comportamento alterado, os riscos e como foi validado.

## Padrões do projeto

- Python 3.11 ou superior;
- nomes e documentação em português, mantendo nomes de APIs oficiais quando necessário;
- testes com biblioteca padrão e dados sintéticos;
- nenhuma chamada real ao Gmail ou ao Gemini em testes automatizados;
- qualquer operação destrutiva deve ter simulação e confirmação explícita.

## Verificação local

```powershell
python -m unittest discover -s tests -v
python -m compileall -q .
```
