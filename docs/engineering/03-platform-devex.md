# Módulo 3 — Platform Engineering e Developer Experience

## 1. Conceito

**Platform Engineering** organiza capacidades compartilhadas para que um time consiga desenvolver e executar software com menos configuração repetida. **Developer Experience (DevEx)** é a qualidade da experiência de quem instala, entende, executa, testa e altera o projeto.

Neste CRM local, uma boa plataforma não exige Kubernetes ou vários serviços. Ela deve tornar claro como iniciar o app, onde configurar valores, como validar o ambiente e quais ferramentas só são necessárias para tarefas específicas.

## 2. O que foi escolhido e por quê

- **Sem Docker ou Compose:** o app precisa de um processo Flask e um arquivo SQLite local; containers adicionariam configuração e não resolvem uma necessidade atual demonstrada.
- **Sem Makefile obrigatório:** comandos PowerShell e shell já são curtos e estão documentados; manter uma ferramenta adicional não melhora o onboarding o suficiente.
- **Configuração local existente:** `config.py` é gerado privadamente na primeira execução; `.env` é opcional para sobrescritas.
- **CSS pré-compilado:** `static/css/tailwind.css` está versionado; Node.js é necessário para editar/recompilar CSS, não para executar o CRM.
- **Health check mínimo:** `GET /health` verifica conexão SQLite com `SELECT 1`, sem retornar caminho ou conteúdo do banco.

## 3. Onboarding

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Prompt de Comando:

```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
```

macOS/Linux:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Ao iniciar pela primeira vez, o app cria `config.py` local e o banco em `instance/crm.sqlite3`. A senha inicial do administrador fica somente no arquivo privado `config.py`. Para personalizar configurações, copie `.env.example` para `.env` e descomente somente as opções desejadas. Não compartilhe esses arquivos locais.

## 4. Arquivos e fluxo técnico

- `README.md`: onboarding, configurações, CSS, testes e limites conhecidos.
- `.env.example`: lista opções sem definir credenciais administrativas padrão.
- `app.py`: gera configuração local ausente, carrega sobrescritas, inicializa banco e serve Flask no loopback.
- `db.py` / `schema.sql`: criam e migram o banco sem apagar registros.
- `GET /health`: verifica processo e disponibilidade básica do SQLite.
- `package.json` e `package-lock.json`: ferramentas de desenvolvimento de CSS; não entram no caminho normal de runtime.

## 5. Verificações e diagnóstico

Com o servidor ativo, visite `http://127.0.0.1:5000/health`. Resposta esperada:

```json
{"status":"ok"}
```

Se receber `503` com `{"status":"unavailable"}`, o processo respondeu, mas não conseguiu consultar SQLite. Confira o erro no terminal e a disponibilidade do diretório/banco sem imprimir ou enviar dados privados.

Verifique dependências e testes:

```powershell
python -m pip check
python -m unittest discover -s tests -v
```

`pip check` procura conflitos entre dependências instaladas. A suíte executa testes com bancos temporários para não alterar o banco real. Se uma importação falhar, confirme que o ambiente virtual está ativado e reinstale `requirements.txt` nele.

Para alterar classes Tailwind, instale Node.js e rode `npm ci` seguido de `npm run build:css`. Não é preciso executar esses comandos em instalação comum do CRM.

## 6. Como empresas usam essas práticas

Projetos profissionais costumam oferecer onboarding reproduzível, configuração por ambiente, checks rápidos de saúde e comandos padronizados. Em equipes maiores, essas capacidades podem ser fornecidas por templates ou plataformas internas. O CRM usa versões locais e leves dessas práticas, dimensionadas para um projeto individual.

## 7. Problemas comuns

- **Copiar `.env.example` e sobrescrever credenciais sem querer:** as opções administrativas permanecem comentadas. Descomente-as somente se desejar substituir o administrador inicial.
- **Ativar `COOKIE_SECURE` em HTTP local:** o navegador pode deixar de enviar o cookie; ative apenas com HTTPS.
- **Esperar Node.js em toda instalação:** o CSS gerado já está no repositório; Node serve apenas para desenvolvimento de estilos.
- **Usar `pip` de outro Python:** ative `.venv` ou invoque o executável diretamente antes de instalar/verificar dependências.
- **Tratar health check como prova de saúde completa:** ele só confirma resposta do processo e uma consulta simples ao banco; não valida login, geração PDF, espaço em disco ou fluxos comerciais.

## 8. Exercício

Crie um ambiente virtual descartável, instale `requirements.txt`, inicie o servidor e abra `/health`. Depois encerre com `Ctrl+C` e responda: quais passos foram necessários? O que o health check confirma e o que ele não confirma?

Critérios: executar sem Node/Docker, obter `{"status":"ok"}`, verificar dependências sem conflitos e não compartilhar `config.py`, `.env` ou banco local.

