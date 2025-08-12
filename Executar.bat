:: Arquivo: Executar_Validacao.bat

:: Desliga a exibicao dos comandos no terminal para uma saida mais limpa.
@echo off

:: Define um titulo para a janela do terminal, para ficar mais profissional.
title Validacao de Chamados Redmine

:: Exibe uma mensagem inicial para o usuario.
echo.
echo Executando a automacao de validacao... Por favor, aguarde.
echo.

:: O COMANDO PRINCIPAL
:: Executa nosso contêiner Docker.
:: ATENCAO: No arquivo .bat, usamos %cd% em vez de $(pwd) para indicar a pasta atual.
docker run --rm -it --env-file .env -v "%cd%/relatorios:/app/relatorios" projeto_redmine

:: Exibe uma mensagem final e pausa o script.
echo.
echo Processo concluido. Pressione qualquer tecla para fechar esta janela.

:: Mantem a janela aberta ate que uma tecla seja pressionada.
pause >nul