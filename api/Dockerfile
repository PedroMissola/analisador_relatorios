# 1. Imagem base com Python
FROM python:3.13-slim

# 2. Define o diretório de trabalho dentro do container
WORKDIR /app

# 3. Copia o arquivo de dependências
COPY ./requirements.txt /app/requirements.txt

# 4. Instala as dependências
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# 5. Copia todo o código da API (main.py) para dentro do container
COPY . /app/

# 6. Comando para iniciar o servidor da API
#    Ele vai procurar por um arquivo "main.py" e uma variável "app"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]