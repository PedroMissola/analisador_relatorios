# Projeto: Gerador de Relatórios com Worker-C Assíncrono
 
Este projeto demonstra uma arquitetura de microsserviços (Padrão Worker-Queue) para lidar com o processamento assíncrono de tarefas pesadas, simulando um ambiente corporativo real.
 
O sistema é composto por uma API de ingestão (FastAPI), uma fila de mensagens (Redis) e um worker de processamento de alta performance (C) que consulta um banco de dados (SQLite) com milhões de registros para gerar relatórios em CSV.
 
## O Conceito (O Fluxo de Dados)
 
O fluxo da arquitetura é projetado para ser desacoplado e resiliente:
 
1.  **Usuário** envia um JSON para a API (`POST /gerar-relatorio`).
2.  **API (FastAPI)** valida o pedido (Pydantic), o enriquece com um `task_id`, e o enfileira (LPUSH) no Redis. A API responde **imediatamente** ao usuário com um `Status 202 - Accepted`.
3.  **Worker (C)**, que estava "dormindo" (bloqueado em um `BRPOP`), acorda assim que a tarefa chega na fila do Redis.
4.  O Worker C analisa o JSON, entende a tarefa e abre uma conexão (Read-Only) com o banco **SQLite**.
5.  O C executa a consulta SQL pesada (com `JOINs`) e processa os resultados **linha por linha** (`sqlite3_step`), garantindo uso mínimo de memória (streaming).
6.  Os resultados são escritos, linha por linha, em um novo arquivo `.csv` na pasta `export/`.
7.  O Worker C volta a "dormir", aguardando a próxima tarefa.
 
## Tecnologias Utilizadas
 
* **API (Ingestão):** **Python 3.11+** com **FastAPI** (para I/O rápido e validação com Pydantic).
* **Fila (Broker):** **Redis** (para um buffer de mensagens leve e rápido).
* **Worker (Processamento):** **C (GCC)** (para performance máxima, eficiência de memória (streaming) e acesso de baixo nível).
* **Banco de Dados:** **SQLite** (para simplicidade de setup, populado com 5.000 funcionários e milhões de registros transacionais para simular volume).
* **Orquestração:** **Docker** e **Docker Compose** (para criar um ambiente de desenvolvimento idêntico e isolado).
* **Libs do Worker C:** `hiredis` (cliente Redis), `libsqlite3` (cliente SQLite), `cJSON` (parser JSON).
 
## Por que esta Arquitetura? (A Justificativa de Engenharia)
 
* **API (FastAPI) vs. Worker (C):** A API é otimizada para I/O (receber e enviar requisições web). O Worker C é otimizado para CPU e Memória (processar dados). Separar os dois permite que cada um escale de forma independente.
* **Por que C?** A principal justificativa para o C não é apenas a velocidade, mas a **eficiência de memória**. Enquanto um script Python poderia carregar todos os resultados do banco de dados na RAM antes de escrever o CSV (causando um "crash" com milhões de linhas), o C (com `sqlite3_step`) processa *linha por linha*. Ele pode gerar um relatório de 50GB usando apenas alguns MB de RAM.
* **Por que Redis?** O Redis atua como um "buffer" (amortecedor). Se 1000 usuários pedirem relatórios ao mesmo tempo, a API os aceita em milissegundos. O Worker C pode, então, processar essa fila no seu próprio ritmo, um por um, sem sobrecarregar o banco de dados.
 
## Estrutura do Projeto

```
/projeto_relatorios
|
|-- api/                    # O código da API FastAPI
|   |-- Dockerfile
|   |-- requirements.txt
|   |-- main.py
|
|-- app/                    # O código do Worker C
|   |-- Dockerfile
|   |-- app.c
|
|-- data/                   # O banco de dados (ignorado pelo git)
|   |-- empresa.db          <- (Este arquivo é GERADO pelo popular_banco.py)
|
|-- export/                 # Onde os relatórios CSV são salvos
|   |-- .gitkeep
|
|-- docker-compose.yml      # O orquestrador de todos os séviços
|-- popular_banco.py      # Script para gerar o 'empresa.db'
|-- README.md               # Este arquivo
```

## Como Executar (Quickstart)
 
O projeto é 100% orquestrado com Docker Compose.
 
### Pré-requisito 1: Gerar o Banco de Dados
 
O banco de dados é muito grande para ser comitado no Git. Você deve gerá-lo localmente primeiro.
 
1.  (Opcional) Crie um ambiente virtual Python: `python -m venv venv && source vent/bin/activate`
2.  Instale o Faker (necessário para o script):
    ```bash
    pip install faker
    ```
3.  Execute o script de população (isso pode demorar alguns segundos):
    ```bash
    python popular_banco.py
    ```
4.  Verifique se o arquivo `data/empresa.db` foi criado.
 
### Pré-requisito 2: Docker
 
Tenha o Docker e o Docker Compose instalados.
 
### Executando o Sistema
 
1.  Na raiz do projeto, construa e inicie todos os contêineres:
    ```bash
    docker-compose up --build
    ```
2.  O terminal mostrará os logs de todos os serviços (API, Worker C, Redis).
3.  Espere até ver o log do `app` (o C-worker) estabilizar em:
    `Worker C: Aguardando por tarefas na fila 'fila_relatorios' (Comando BRPOP)...`
 
## Como Testar (O "Full Loop")
 
Com o sistema rodando:
 
1.  Abra seu navegador e acesse a documentação interativa da API:
    **[http://localhost:8000/docs](http://localhost:8000/docs)**
 
2.  Encontre a rota `POST /gerar-relatorio`, clique em "Try it out".
 
3.  No "Request body", cole um JSON de pedido válido.
 
### Exemplo 1: Gastos por Departamento
 
```json
{
  "tipo_relatorio": "GASTOS_POR_DEPARTAMENTO",
  "parametros": {
    "departamento": "Engenharia de Software"
  }
}
```

Exemplo 2: Pagamentos Pendentes
```json
{
  "tipo_relatorio": "PAGAMENTOS_PENDENTES",
  "parametros": {}
}
```
 
4. Clique em "Execute".

### Oque Observar:
* No Navegador (API): Você receberá uma resposta imediata (Status 202) com o task_id e o nome do arquivo que será gerado.
* No Terminal (Worker C): No terminal do docker-compose, você verá o log do C-worker "acordar", imprimir "Nova tarefa recebida", "Executando consulta SQL pesada..." e, finalmente, "Relatório gerado com sucesso!".
* Na Pasta (Resultado): Verifique a pasta export/ no seu computador. O arquivo CSV (ex: relatorio_GASTOS_POR_DEPARTAMENTO_... .csv) estará lá, pronto para ser aberto.
