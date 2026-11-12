# Módulo 4 — Observabilidade

## 1. Conceito

Observabilidade é a capacidade de entender o estado e o comportamento de um sistema usando sinais que ele produz. Os sinais mais comuns são **logs** (eventos), **métricas** (medidas ao longo do tempo) e **traces** (etapas de uma operação distribuída).

Este CRM é um processo Flask local com SQLite. Não há serviços distribuídos nem infraestrutura de coleta. Para seu estágio atual, logs estruturados e um identificador por requisição trazem valor sem adicionar dependências ou serviços permanentes.

## 2. O que foi implementado

- Cada requisição recebe um ID aleatório de 128 bits, enviado no cabeçalho `X-Request-ID`.
- A aplicação escreve eventos JSON com horário UTC, nível e nome do evento. Eventos de requisição também incluem método, rota Flask (sem valores de parâmetros), código HTTP e duração em milissegundos.
- O erro interno registra tipo da exceção, rota e ID. Não registra conteúdo de formulário, cookies, cabeçalhos, endereço IP ou mensagem arbitrária da exceção.
- O health check registra um evento genérico se SQLite não responder; a resposta pública continua sem detalhes internos.
- Nenhuma biblioteca ou serviço de observabilidade externo foi adicionado.

Exemplo aproximado de evento:

```json
{"timestamp":"2026-11-12T14:30:00+00:00","level":"info","event":"http_request","request_id":"b8d...","method":"GET","route":"quotes.detail","status":200,"duration_ms":12.4}
```

O ID é gerado pelo servidor, não aceito do cliente. Isso reduz risco de conteúdo malicioso ou sensível inserido no campo de correlação.

## 3. Caminho de uma requisição

1. Flask recebe a requisição e cria `request_id` e horário inicial.
2. A rota verifica sessão/CSRF conforme o tipo de operação e chama o controller.
3. O controller valida a entrada e chama o modelo.
4. O modelo usa `db.py` para consultar ou atualizar SQLite.
5. Flask monta HTML, PDF ou erro seguro.
6. O hook de resposta adiciona `X-Request-ID` e registra rota, status e duração.

Para investigar uma falha, copie o `X-Request-ID` da resposta e procure a mesma string na saída do terminal. O evento `internal_error` identifica a classe da exceção e rota sem registrar os valores privados enviados pelo usuário.

## 4. Arquivos relevantes

- `app.py`: formatter JSON, geração/cabeçalho de request ID, evento de conclusão e log seguro de erro.
- `tests/test_auth.py`: verifica formato do ID, associação ao erro e ausência de mensagem privada nos logs/resposta.
- `README.md`: verificações locais e health check.

## 5. Como usar e testar

Inicie localmente e faça uma requisição; em PowerShell:

```powershell
$r = Invoke-WebRequest http://127.0.0.1:5000/health
$r.Headers['X-Request-ID']
$r.Content
```

O terminal deve mostrar uma linha JSON `http_request`; a resposta deve conter `{"status":"ok"}`. Para a suíte:

```powershell
python -m unittest discover -s tests -v
```

## 6. O que ainda não existe

Não há métricas históricas, alertas, dashboards, traces distribuídos nem coleta persistente de logs. Duração por requisição é registrada como evento, mas sem retenção/consulta agregada ela não é uma série de latência. OpenTelemetry, Prometheus, Grafana, Loki e Tempo podem ser avaliados se o app ganhar processos/serviços ou operação compartilhada.

## 7. Problemas comuns

- **Um 500 aparece, mas não há stack trace:** isso é intencional para não expor dados potencialmente privados. Use ID, rota e tipo para localizar a requisição; em desenvolvimento, depure localmente sem registrar payloads.
- **ID da resposta não aparece no log:** confirme que a resposta veio do processo atualizado e procure a linha `http_request` correspondente.
- **Muitos logs no terminal:** cada requisição gera um evento. Em produção, agregação, níveis e retenção precisariam de configuração operacional própria.
- **Health responde `ok`, mas uma tela falha:** o health check só cobre processo e consulta básica ao SQLite; não valida todas as rotas.

## 8. Exercício

Abra `/health`, copie o `X-Request-ID` e localize a linha JSON equivalente no terminal. Identifique método, rota, status e duração. Depois explique por que corpo do formulário e cookie não devem ser incluídos nesses eventos.

Critérios: correlacionar a resposta com um log, interpretar status/duração e não expor dados pessoais ou credenciais.

