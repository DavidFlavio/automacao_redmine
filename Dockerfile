# Arquivo: Dockerfile

# 1. A IMAGEM DE BASE (A "cozinha" que vamos usar)
# Usamos uma imagem oficial do Python, na versão 3.10, do tipo "slim".
# "slim" é uma versão mais leve, o que torna nossa imagem final menor.
FROM python:3.10-slim

# 2. DIRETÓRIO DE TRABALHO (A "bancada" da nossa mini-cozinha)
# Define a pasta padrão onde todos os comandos seguintes serão executados dentro do contêiner.
WORKDIR /app

# 3. COPIAR E INSTALAR AS DEPENDÊNCIAS (Os "ingredientes")
# Copiamos apenas a lista de ingredientes primeiro. Isso é uma otimização!
# O Docker guarda o resultado dessa etapa em cache. Se não mudarmos o requirements.txt,
# ele não precisará reinstalar tudo da próxima vez que construirmos a imagem.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. COPIAR O RESTO DO PROJETO (A "receita" do nosso prato)
# Agora copiamos todos os outros arquivos do nosso projeto para a bancada.
COPY . .

# 5. COMANDO DE EXECUÇÃO (A ordem para "preparar e servir o prato")
# Define o comando que será executado quando o contêiner iniciar.
CMD ["python", "consultar_chamados.py"]