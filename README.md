# CRM de Orçamentos e Propostas

Aplicação local em Python/Flask, SQLite, Tailwind CSS e ReportLab. O desenvolvimento é dividido em fases; esta primeira entrega prepara o ambiente e o banco. As telas serão implementadas nas fases seguintes.

## Requisitos

- Python 3.10 ou superior com `pip`.
- Git para acompanhar as fases. Git é um programa do sistema e não uma dependência Python.

## Preparar e iniciar a Fase 1

No Windows, abra o PowerShell nesta pasta e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

O primeiro início cria `config.py` com chave de sessão e senha aleatórias persistentes, cria o banco `instance/crm.sqlite3` e salva a senha do admin apenas como hash no banco. A senha inicial é exibida no terminal e também fica em `config.py`. Guarde-a em local seguro. A configuração local e o banco são ignorados pelo Git.

As informações da empresa em `config.py` são fictícias e podem ser substituídas. Para executar a validação da Fase 1, use `python -m unittest discover -s tests`.

## Fases seguintes

O login e a interface passam a funcionar após a Fase 2. As funcionalidades de clientes, produtos, orçamentos e PDFs serão entregues nas fases autorizadas correspondentes.
