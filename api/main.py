import redis
import uuid
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from enum import Enum

class TipoRelatorio(str, Enum):
    GASTOS_POR_DEPARTAMENTO = "GASTOS_POR_DEPARTAMENTO"
    PAGAMENTOS_PENDENTES = "PAGAMENTOS_PENDENTES"
    RESUMO_POR_DIVISAO = "RESUMO_POR_DIVISAO"

class PedidoRelatorio(BaseModel):
    tipo_relatorio: TipoRelatorio = Field(
        ...,
        title="Tipo do Relatório",
        description="O tipo de relatório que deve ser gerado."
    )

    parametros: dict = Field(
        default_factory=dict,
        title="Parâmetros para o Filtro",
        description="Ex: {'departamento': 'Engenharia de Software'} ou {'mes_referencia': '2025-10'}"
    )

class TaskPayload(BaseModel):
    task_id: str
    tipo_relatorio: str
    parametros: dict
    output_filename: str

NOME_FILA_REDIS = "fila_relatorios"

app = FastAPI(
    title="Gerador de RelAT (Relatórios Assíncronos)",
    description="API para solicitar relatórios pesados que são processados em C.",
    version="1.0.0"
)

try:
    redis_client = redis.Redis(host='redis', port=6379, db=0)
    redis_client.ping()
    print("Conectado ao Redis com sucesso!")
except redis.exceptions.ConnectionError as e:
    print(f"Erro ao conectar ao Redis: {e}")
    redis_client = None

@app.post("/gerar-relatorio", status_code=status.HTTP_202_ACCEPTED)
async def gerar_relatorio(pedido: PedidoRelatorio):
    if not redis_client:
        raise HTTPException(
            status_code=503,
            detail="Serviço indisponível (Redis não conectado)."
        )

    task_id = str(uuid.uuid4())

    output_filename = f"relatorio_{pedido.tipo_relatorio.value}_{task_id}.csv"

    task = TaskPayload(
        task_id=task_id,
        tipo_relatorio=pedido.tipo_relatorio.value,
        parametros=pedido.parametros,
        output_filename=output_filename
    )

    task_json = task.model_dump_json()

    try:
        redis_client.lpush(NOME_FILA_REDIS, task_json)

        return {
            "status": "Relatório enfileirado",
            "task_id": task_id,
            "output_filename_esperado": output_filename,
            "info": "O relatório será processado em segundo plano."
        }

    except redis.exceptions.ConnectionError as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enfileirar tarefa: {e}")


@app.get("/health/redis", summary="Verifica a conexão com o Redis")
async def health_check_redis():
    if not redis_client:
        raise HTTPException(status_code=503, detail="Serviço indisponível (configuração).")

    try:
        redis_client.ping()
        return {"status": "ok", "redis": "conectado"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis desconectado: {e}")


@app.get("/health", summary="Verifica se a API está no ar")
async def health_check():
    return {"status": "ok"}