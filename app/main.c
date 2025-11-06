#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <hiredis/hiredis.h>
#include <sqlite3.h>
#include <cjson/cJSON.h>

const char* REDIS_HOST = "redis";
const int REDIS_PORT = 6379;
const char* REDIS_QUEUE_NAME = "fila_relatorios";
const char* DB_PATH = "/app/data/empresa.db";
const char* EXPORT_DIR = "/app/export/";

redisContext* conectar_redis() {
    redisContext *ctx = NULL;
    int tentativas = 0;
    while (tentativas < 5) {
        ctx = redisConnect(REDIS_HOST, REDIS_PORT);
        if (ctx != NULL && ctx->err == 0) {
            printf("Worker C: Conectado ao Redis em %s:%d\n", REDIS_HOST, REDIS_PORT);
            return ctx;
        }
        if (ctx) {
            printf("Worker C: Erro ao conectar ao Redis: %s\n", ctx->errstr);
            redisFree(ctx);
        } else {
            printf("Worker C: Não foi possível alocar contexto do Redis.\n");
        }
        tentativas++;
        printf("Tentando novamente em 5 segundos...\n");
        sleep(5);
    }
    return NULL;
}


sqlite3* conectar_sqlite() {
    sqlite3 *db;
    int rc = sqlite3_open_v2(DB_PATH, &db, SQLITE_OPEN_READONLY, NULL);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Worker C: Erro ao abrir banco de dados SQLite: %s\n", sqlite3_errmsg(db));
        return NULL;
    }
    printf("Worker C: Conectado ao banco de dados SQLite (somente leitura): %s\n", DB_PATH);
    return db;
}

void processar_tarefa(const char* task_json_str, sqlite3 *db) {
    cJSON *root = NULL;
    FILE *fp_csv = NULL;
    sqlite3_stmt *stmt = NULL;
    char* tipo_relatorio = NULL;
    char* output_filename = NULL;
    
    printf("----------------------------------------\n");
    printf("Worker C: Nova tarefa recebida. Processando...\n");

    root = cJSON_Parse(task_json_str);
    if (root == NULL) {
        fprintf(stderr, "Erro: Falha ao analisar JSON da tarefa.\n");
        goto cleanup;
    }

    cJSON *tipo_json = cJSON_GetObjectItemCaseSensitive(root, "tipo_relatorio");
    cJSON *params_json = cJSON_GetObjectItemCaseSensitive(root, "parametros");
    cJSON *filename_json = cJSON_GetObjectItemCaseSensitive(root, "output_filename");

    if (!cJSON_IsString(tipo_json) || !cJSON_IsString(filename_json) || !cJSON_IsObject(params_json)) {
        fprintf(stderr, "Erro: JSON da tarefa está mal formatado ou faltando campos.\n");
        goto cleanup;
    }

    tipo_relatorio = tipo_json->valuestring;
    output_filename = filename_json->valuestring;
    
    char output_path[512];
    snprintf(output_path, sizeof(output_path), "%s%s", EXPORT_DIR, output_filename);

    printf("ID da Tarefa: %s\n", cJSON_GetObjectItemCaseSensitive(root, "task_id")->valuestring);
    printf("Tipo de Relatório: %s\n", tipo_relatorio);
    printf("Salvando em: %s\n", output_path);

    fp_csv = fopen(output_path, "w");
    if (fp_csv == NULL) {
        fprintf(stderr, "Erro: Não foi possível criar o arquivo de relatório: %s\n", output_path);
        goto cleanup;
    }

    char sql_query[1024];
    int rc;

    if (strcmp(tipo_relatorio, "GASTOS_POR_DEPARTAMENTO") == 0) {
        cJSON *depto_json = cJSON_GetObjectItemCaseSensitive(params_json, "departamento");
        if (!cJSON_IsString(depto_json)) {
            fprintf(stderr, "Erro: 'GASTOS_POR_DEPARTAMENTO' requer o parâmetro 'departamento'.\n");
            fprintf(fp_csv, "ERRO: Parametro 'departamento' ausente.\n"); // Escreve erro no CSV
            goto cleanup;
        }
        char* depto_nome = depto_json->valuestring;

        snprintf(sql_query, sizeof(sql_query),
            "SELECT f.nome, f.cargo, g.descricao, g.valor, g.data_gasto "
            "FROM gastos_internos g "
            "JOIN funcionarios f ON g.id_funcionario = f.id "
            "WHERE f.departamento = ? AND g.status_aprovacao = 'Aprovado' AND f.status = 'Ativo' "
            "ORDER BY g.valor DESC"
        );
        
        rc = sqlite3_prepare_v2(db, sql_query, -1, &stmt, NULL);
        if (rc != SQLITE_OK) {
            fprintf(stderr, "Erro ao preparar SQL: %s\n", sqlite3_errmsg(db));
            goto cleanup;
        }
        
        sqlite3_bind_text(stmt, 1, depto_nome, -1, SQLITE_STATIC);
        
        fprintf(fp_csv, "Nome,Cargo,Descricao_Gasto,Valor,Data\n");

    } else if (strcmp(tipo_relatorio, "PAGAMENTOS_PENDENTES") == 0) {
        
        snprintf(sql_query, sizeof(sql_query),
            "SELECT f.nome, f.email, f.departamento, p.mes_referencia, p.valor_pago "
            "FROM pagamentos p "
            "JOIN funcionarios f ON p.id_funcionario = f.id "
            "WHERE p.status = 'Pendente' "
            "ORDER BY f.departamento, p.mes_referencia"
        );
        
        rc = sqlite3_prepare_v2(db, sql_query, -1, &stmt, NULL);
        if (rc != SQLITE_OK) {
            fprintf(stderr, "Erro ao preparar SQL: %s\n", sqlite3_errmsg(db));
            goto cleanup;
        }
        
        fprintf(fp_csv, "Nome,Email,Departamento,Mes_Referencia,Valor_Pendente\n");
        
    } else {
        fprintf(stderr, "Erro: Tipo de relatório desconhecido: %s\n", tipo_relatorio);
        fprintf(fp_csv, "ERRO: Tipo de relatorio '%s' nao reconhecido.\n", tipo_relatorio);
        goto cleanup;
    }

    printf("Executando consulta SQL pesada...\n");
    int row_count = 0;

    while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        
        int col_count = sqlite3_column_count(stmt);
        for (int i = 0; i < col_count; i++) {
            const char *valor = (const char*)sqlite3_column_text(stmt, i);
            if (valor == NULL) {
                valor = "";
            }
            
            if (sqlite3_column_type(stmt, i) == SQLITE_TEXT) {
                fprintf(fp_csv, "\"%s\"", valor);
            } else {
                fprintf(fp_csv, "%s", valor);
            }
            
            if (i < col_count - 1) {
                fprintf(fp_csv, ",");
            }
        }
        fprintf(fp_csv, "\n");
        row_count++;
    }
    
    if (rc != SQLITE_DONE) {
        fprintf(stderr, "Erro ao executar consulta: %s\n", sqlite3_errmsg(db));
    }

    printf("Relatório gerado com sucesso! %d linhas escritas em %s\n", row_count, output_path);

cleanup:
    printf("Limpando recursos da tarefa...\n");
    if (fp_csv != NULL) {
        fclose(fp_csv);
    }
    if (stmt != NULL) {
        sqlite3_finalize(stmt); // Liberar o statement do SQL
    }
    if (root != NULL) {
        cJSON_Delete(root); // Liberar o objeto JSON
    }
    printf("----------------------------------------\n\n");
}


int main() {
    redisContext *redis_ctx = conectar_redis();
    if (redis_ctx == NULL) {
        fprintf(stderr, "Falha crítica: Não foi possível conectar ao Redis após 5 tentativas. Saindo.\n");
        return 1;
    }
    
    sqlite3 *db = conectar_sqlite();
    if (db == NULL) {
        fprintf(stderr, "Falha crítica: Não foi possível abrir o banco de dados. Saindo.\n");
        redisFree(redis_ctx);
        return 1;
    }

    while (1) {
        printf("Worker C: Aguardando por tarefas na fila '%s' (Comando BRPOP)...\n", REDIS_QUEUE_NAME);

        redisReply *reply = (redisReply*)redisCommand(redis_ctx, "BRPOP %s 0", REDIS_QUEUE_NAME);
        
        if (reply == NULL) {
            fprintf(stderr, "Erro crítico no Redis (conexão perdida?). Tentando reconectar...\n");
            redisFree(redis_ctx);
            sleep(5);
            redis_ctx = conectar_redis();
            if (redis_ctx == NULL) {
                fprintf(stderr, "Falha ao reconectar. Saindo.\M");
                break;
            }
            continue;
        }

        if (reply->type == REDIS_REPLY_ARRAY && reply->elements == 2) {
            const char* task_json_str = reply->element[1]->str;
            
            processar_tarefa(task_json_str, db);
            
        } else {
            fprintf(stderr, "Resposta inesperada do BRPOP. Tipo: %d\n", reply->type);
        }

        freeReplyObject(reply);
    }

    printf("Worker C: Encerrando...\n");
    sqlite3_close(db);
    redisFree(redis_ctx);

    return 0;
}