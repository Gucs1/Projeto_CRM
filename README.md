# CRM de Orçamentos e Propostas

Aplicação local em Python/Flask, SQLite, Tailwind CSS e ReportLab. O projeto é entregue em fases. Login, clientes e catálogo de produtos/serviços já estão disponíveis; orçamentos e PDFs serão habilitados nas próximas fases.

## Requisitos

- Python 3.10 ou superior com `pip`.
- Git para acompanhar as fases. Git é um programa do sistema e não uma dependência Python.

## Instalação e início

No Windows, abra o PowerShell nesta pasta e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

O servidor fica restrito ao próprio computador. Por padrão, o navegador abre a tela de login quando o servidor estiver pronto. Para iniciar sem abrir o navegador, altere `AUTO_OPEN_BROWSER = False` em `config.py`.

No primeiro uso, o sistema cria `config.py` com chave de sessão e senha de administrador aleatórias e persistentes, inicializa o banco `instance/crm.sqlite3` e grava a senha apenas como hash no banco. As credenciais iniciais são usuário `admin` e a senha exibida no terminal durante a configuração inicial, também guardada em `config.py`. Preserve essa configuração para não perder o acesso.

As informações da empresa em `config.py` são fictícias e podem ser editadas. `config.py`, o banco e o ambiente virtual são ignorados pelo Git.

## Testes

```powershell
python -m unittest discover -s tests -v
```

## Uso

1. Execute `python app.py` e aguarde a abertura do navegador.
2. Entre com o usuário e a senha inicial.
3. Use **Clientes** para cadastrar, pesquisar por nome, editar e excluir contatos. Cadastros associados a orçamentos não podem ser excluídos.
4. Use **Produtos e serviços** para cadastrar, editar e excluir itens. Informe o preço em reais, usando vírgula ou ponto para os centavos; por exemplo, `125,50` ou `125.50`. Itens associados a orçamentos não podem ser excluídos.
5. Para sair, use o botão **Sair** no cabeçalho.

Encerre o servidor com `Ctrl+C` no terminal. Para preservar os dados, mantenha uma cópia da pasta `instance` e do arquivo `config.py` em local privado e seguro.
