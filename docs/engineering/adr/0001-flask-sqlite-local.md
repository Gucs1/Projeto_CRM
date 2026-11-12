# ADR-0001: Flask, SQLite e páginas Jinja para execução local

- **Estado:** aceito (arquitetura atual)
- **Data:** 2026-11-12

## Contexto

O projeto é um CRM demonstrativo para execução local. Precisa de cadastro, autenticação, orçamento e PDF sem exigir hospedagem nem serviços externos. A simplicidade de instalação e operação é uma prioridade.

## Decisão

Manter uma aplicação Flask de processo único, páginas renderizadas por Jinja, persistência SQLite local e geração de PDF em memória com ReportLab. Organizar as responsabilidades entre controllers, models, templates/static e pdf.

## Consequências

- Uma pessoa pode instalar dependências e iniciar o sistema localmente sem provisionar banco ou serviços remotos.
- Testes podem usar bancos SQLite temporários e rodar sem ambiente de hospedagem.
- SQLite não é uma escolha para alta concorrência ou operação distribuída; crescer para esse cenário exige reavaliar banco, execução e backup.
- A aplicação permanece vinculada a `127.0.0.1`; este ADR não autoriza exposição em rede.

