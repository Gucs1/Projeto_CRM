# Módulo 6 — Security Engineering e DevSecOps

## 1. Conceito

Security Engineering integra proteções ao desenho e à implementação. DevSecOps automatiza verificações de segurança junto ao ciclo de desenvolvimento. Nenhuma ferramenta sozinha prova que um sistema é seguro; cada uma detecta classes específicas de problemas.

## 2. Proteções já presentes no CRM

- Senhas persistidas como hash via Werkzeug; cadastro valida tamanho e confirmação.
- CSRF em formulários, validação no servidor, cookies HttpOnly/SameSite e sessão revogável.
- Consultas comerciais filtram por conta autenticada; testes cobrem acesso cruzado.
- SQL usa parâmetros para valores; migrações preservam dados e são testadas com bancos temporários.
- Configuração privada local, `.env`, banco e ferramentas virtuais são ignorados pelo Git.
- Flask escuta em `127.0.0.1` e debug permanece desativado; o projeto não é preparado para implantação pública.
- Logs evitam corpo, cookie, endereço IP e mensagens arbitrárias de exceções.

Esses controles reduzem riscos comuns, mas não fornecem recuperação de conta, MFA, e-mail verificado, backup automático ou operação pronta para produção.

## 3. Ferramentas adicionadas

- **Bandit 1.9.4:** análise estática Python baseada em AST. Fica em `requirements-dev.txt`, separada das dependências de runtime. O CI falha para achados médios/altos (`-ll`).
- **pip-audit:** compara dependências Python de desenvolvimento e runtime com advisories públicos no job GitHub.
- **npm audit:** verifica dependências do frontend com severidade moderada ou maior.
- **Gitleaks CLI em container (v8.24.3):** examina o histórico Git completo em busca de segredos commitados; não depende de um intervalo calculado a partir do SHA anterior do evento.

A varredura de segredos não recebe token nem requer licença: o container do Gitleaks lê o histórico já disponível no checkout e o workflow mantém somente a permissão `contents: read`.

## 4. Achados analisados durante a implementação

Bandit identificou `urllib.request.urlopen` no abridor automático do navegador e SQL de migração que interpolava identificadores. O abridor agora valida HTTP, host `127.0.0.1` e ausência de credenciais antes da chamada; um teste cobre rejeição de URLs externas e userinfo. O único `# nosec B310` fica nessa linha, justificado pela validação imediatamente anterior.

As consultas de migração foram convertidas para SQLs constantes escolhidos por mapas locais. Os dados (`admin_id`) continuam parametrizados. Assim Bandit não precisa ignorar B608; os testes de migração verificam preservação dos dados.

Bandit reportou `No issues identified` para achados médios/altos após as mudanças. `npm audit` reportou zero vulnerabilidades. A execução local posterior encontrou zero vulnerabilidades conhecidas no conjunto auditado.

## 5. Como executar localmente

```powershell
python -m pip install -r requirements-dev.txt
python -m pip check
python -m bandit -r app.py controllers models db.py pdf -ll
npm audit --audit-level=moderate
python -m unittest discover -s tests -v
```

O `pip-audit` também pode ser executado com `python -m pip_audit -r requirements-dev.txt`, quando o serviço público de advisories estiver acessível. `pip-audit` detecta vulnerabilidades conhecidas por versão; não é SAST e não prova que o uso local de uma biblioteca seja seguro.

O Gitleaks CI executa `gitleaks git --redact --verbose --exit-code 2` no repositório completo. Localmente, se tiver o CLI instalado, rode esse mesmo comando na raiz. Ao detectar um segredo já commitado, revogue/rotacione o segredo primeiro; apagar o arquivo num commit posterior não remove o valor do histórico.

## 6. Como interpretar os scanners

- **Bandit:** revise identificador, gravidade, confiança e fluxo real. Um padrão sinalizado pode ser falso positivo, mas só suprima regra pontual após validar o controle; explique o motivo ao lado do código.
- **pip-audit/npm audit:** identifique pacote, versão afetada e versão corrigida. Atualize as faixas/lock, rode os testes e não ignore advisory sem justificativa e prazo.
- **Gitleaks:** trate qualquer credencial real como comprometida; faça rotação e examine histórico/artefatos antes de considerar resolvido.
- **CI vermelho:** não desligue uma verificação para liberar o build. Reproduza localmente, corrija ou documente a exceção mínima com evidência.

## 7. Limitações

- Os scanners dependem de regras e feeds externos; podem gerar falsos positivos ou não conhecer uma vulnerabilidade nova.
- A correção usa o modo `git` do CLI oficial para que o scan completo aceite o primeiro commit, que não possui pai.
- No primeiro push, a Action tentou formar o intervalo `c3175ab^..HEAD`; como `c3175ab` é o commit raiz, essa referência não existe. O workflow agora roda o scanner no histórico inteiro sem esse intervalo.
- Bandit não cobre dependências, autenticação ponta a ponta, lógica comercial nem segurança operacional.
- O projeto permanece local e de demonstração; não se deve expô-lo à internet sem uma revisão de implantação.

## 8. Exercício

Rode Bandit, `npm audit` e a suíte de testes localmente. Depois revise o job `Security checks` em `.github/workflows/ci.yml` e explique o que cada etapa detecta, quais permissões recebe e por que uma vulnerabilidade corrigida no código não substitui a rotação de uma credencial que já foi exposta.

Critérios: diferenciar SAST, auditoria de dependências e secret scanning; interpretar resultados sem alegar cobertura total; manter o token do workflow read-only.

## Referências oficiais

- [Bandit — documentação e opções](https://github.com/PyCQA/bandit)
- [pip-audit — auditoria de dependências Python](https://github.com/pypa/pip-audit)
- [Gitleaks CLI](https://github.com/gitleaks/gitleaks)
- [GitHub Actions — práticas de segurança](https://docs.github.com/en/actions/reference/security/secure-use)
