# 1. Imagem base com o compilador GCC
#    Usamos 'gcc:latest' pois ela já vem com 'make' e 'build-essential'
FROM gcc:latest

# 2. Define o diretório de trabalho
WORKDIR /app

# 3. Instala as bibliotecas (libs) que o C precisa para se conectar
#    - libhiredis-dev: Para falar com o Redis
#    - libsqlite3-dev: Para falar com o SQLite
#    - libcjson-dev: Para ler (parse) o JSON vindo do Redis
RUN apt-get update && apt-get install -y \
    libhiredis-dev \
    libsqlite3-dev \
    libcjson-dev

# 4. Copia o código fonte (worker.c) para dentro do container
COPY ./main.c /app/

# 5. Compila o código C
#    -o worker: Define o nome do arquivo executável de saída
#    -l(nome): "Linka" as bibliotecas que instalamos
RUN gcc main.c -o main -lhiredis -lsqlite3 -lcjson -lm

# 6. Comando para iniciar o worker (rodar o executável que acabamos de compilar)
CMD ["./main"]