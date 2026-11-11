# CRM de Orçamentos e Propostas

Aplicação local em Python/Flask, SQLite, Tailwind CSS e ReportLab. Login, clientes, catálogo, controle de orçamentos e geração de propostas PDF estão disponíveis.

## Requisitos

- Python 3.10 ou superior com `pip`.
- Git instalado no sistema para acompanhar as fases. Git é um programa do sistema, não uma dependência Python.

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

As informações da empresa em `config.py` são fictícias e podem ser editadas. Configure nome, e-mail, telefone e endereço antes de usar propostas. A opção `COMPANY_LOGO` aponta para o logotipo PNG/JPEG; se não houver arquivo válido, o PDF usa uma marca vetorial simples. `config.py`, o banco e o ambiente virtual são ignorados pelo Git.

## Testes

```powershell
python -m unittest discover -s tests -v
```

## Uso

1. Execute `python app.py` e aguarde a abertura do navegador.
2. Entre com o usuário e a senha inicial.
3. Use **Clientes** para cadastrar, pesquisar por nome, editar e excluir contatos. Cadastros associados a orçamentos não podem ser excluídos.
4. Use **Produtos e serviços** para cadastrar, editar e excluir itens. Informe o preço em reais, usando vírgula ou ponto para os centavos; por exemplo, `125,50` ou `125.50`. Itens associados a orçamentos não podem ser excluídos.
5. Em **Orçamentos**, monte uma proposta escolhendo cliente, itens e quantidades. O total exibido é atualizado na tela e recalculado pelo servidor ao salvar. O histórico fica disponível na lista de orçamentos e no cadastro de cada cliente.
6. Abra um orçamento para atualizar o status para **Enviado**, **Aprovado** ou **Recusado**.
7. Na tela do orçamento, use **Gerar PDF** para baixar `orcamento-[id].pdf`, com dados da empresa e do cliente, itens, total, observações e status.
8. Para sair, use o botão **Sair** no cabeçalho.

Para incluir dados fictícios de demonstração sem duplicar nem substituir cadastros existentes, execute `python scripts/seed_demo_data.py`. O script cria quatro clientes, seis produtos e quatro orçamentos relacionados.

Encerre o servidor com `Ctrl+C` no terminal. Para preservar os dados, mantenha uma cópia da pasta `instance` e do arquivo `config.py` em local privado e seguro. A interface usa Tailwind via CDN, então a estilização requer conexão com a internet; o banco e a geração de PDF são locais.
