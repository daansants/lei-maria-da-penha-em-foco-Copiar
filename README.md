# Lei Maria da Penha em Foco — atualização automática

## O que está incluído
- `index.html`: portal responsivo com pesquisa e categorias.
- `news.json`: banco público de manchetes, inicialmente vazio.
- `update_news.py`: coleta RSS de pesquisas temáticas no Google Notícias, sem instalar bibliotecas.
- `.github/workflows/atualizar-noticias.yml`: executa a coleta a cada 3 horas e permite execução manual no GitHub Actions.

## Como ativar sem SSH ou Cron da Hostinger
1. Crie um repositório **privado** no GitHub e envie todos os arquivos, inclusive a pasta `.github`.
2. Abra **Actions > Atualizar noticias > Run workflow** para executar o primeiro teste. Confira o resultado e o arquivo `news.json`.
3. No Cloudflare Pages, crie um projeto conectado ao repositório GitHub. Use `lmp-portal` como diretório raiz se estiver dentro de outro repositório; se estiver na raiz, não precisa configurar comando de build. O diretório de saída deve ser a raiz do projeto (ou `.` quando solicitado).
4. Cada alteração de `news.json` enviada pelo GitHub Actions dispara uma nova publicação no Cloudflare Pages, se a integração Git estiver ativa.
5. Confirme o endereço temporário e só depois altere o domínio do portal antigo.

## Limitações e segurança editorial
- Este é um agregador de **manchetes com links**. Não copia matérias nem gera reportagens automaticamente.
- O Google Notícias pode mudar ou limitar seu RSS; uma falha geral mantém o JSON anterior.
- As categorias vêm da busca usada e **não** equivalem a classificação jurídica ou checagem de fatos.
- Não classifique arquivamento, absolvição ou falta de provas como denúncia comprovadamente falsa.
- A coleta depende da disponibilidade das fontes e de execução do GitHub Actions, que pode atrasar ou ser suspensa por inatividade.
- Nenhuma publicação foi testada em produção. Execute o workflow e confira as manchetes antes de divulgar.
