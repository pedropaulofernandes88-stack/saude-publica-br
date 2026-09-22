-- V051 — RHC: a fonte estava com o dobro dos casos, e os campos que importam
-- não estavam sendo lidos
--
-- O QUE ACONTECEU
-- ---------------
-- A V050 publicou o RHC como 16ª fonte em 2026-09-21. No mesmo dia, ao ampliar
-- a extração de 10 para 18 dos 46 campos do arquivo, apareceu isto:
--
--   **o exportador do INCA grava cada página duas vezes.**
--
-- Páginas de 50.000 registros, cada uma seguida de uma cópia byte por byte. O
-- cabeçalho do dBase declara o total DOBRADO e a geometria fecha com ele —
-- `1505 + 518.186 × 921` é exatamente o tamanho do arquivo de 2019. Vale nos
-- onze anos, com razão de 2,004 a 2,011 (passa de 2,000 porque existem
-- pacientes genuinamente idênticos nos campos publicados, e é por isso que a
-- correção divide a MULTIPLICIDADE por dois em vez de "remover duplicata":
-- deduplicar por valor apagaria os gêmeos verdadeiros).
--
-- POR QUE NENHUMA GUARDA PEGOU
-- -----------------------------
-- Porque dobrar tudo preserva toda proporção. Os 53% sem estadiamento, os
-- 21,7% de divergência de ano, os 25,9% de não analíticos, a queda de 2023, o
-- carimbo `ano_incompleto` — todos continuavam certos. A forma fechava, a
-- cobertura somava, o prazo classificava. O que denunciou foi **paridade**:
-- 119 categorias de idade e 224 de CNES, e nenhuma contagem ímpar em nenhuma.
--
-- É a lição que já está em `guardas-de-integridade-de-dado`, uma volta acima:
-- contagem de linhas não detecta corrupção, e agora também **proporção não
-- detecta duplicação uniforme**.
--
-- A CORREÇÃO FOI VALIDADA CONTRA FORA, NÃO CONTRA ELA MESMA
-- ----------------------------------------------------------
-- Reproduzindo a coorte de Jomar RT et al., Cien Saude Colet 2023;28(7):
-- 2155-2164 (RJ, mama, mulheres ≥20 anos, casos analíticos, 2013–2019):
--
--     publicado por eles ......... 18.098 casos, 82,1% acima de 60 dias
--     meu recorte corrigido ...... 17.874 casos, 80,4% acima de 60 dias
--     meu recorte SEM corrigir ... 35.748 casos
--
-- 98,8% do n publicado, e 1,7 ponto no desfecho. A diferença residual é
-- compatível com a exclusão de tratamento prévio que eles aplicam e este
-- recorte não. É a primeira vez que um número deste projeto é conferido contra
-- uma coorte publicada e bate.
--
-- OS VALORES CORRIGIDOS
-- ---------------------
--     ano      publicado (dobro)     real
--     2019           518.186      259.093
--     2022           461.166      230.583
--     2023           142.038       71.019
--
-- DOIS MARTS NOVOS, SÓ EM PARQUET
-- --------------------------------
-- `mart_rhc_perfil` (1.325.892 linhas) cruza sexo, faixa etária, raça/cor e
-- escolaridade com CID-3, estadiamento e prazo. É o único lugar do projeto
-- onde iniquidade no acesso oncológico é mensurável: nenhuma das outras quinze
-- fontes traz raça/cor declarada nem escolaridade.
--
-- `mart_rhc_tratamento` (612.564 linhas) traz `PRITRATH` — o primeiro
-- tratamento de QUALQUER modalidade, que é o que a Lei 12.732/2012 conta e o
-- que a APAC de quimioterapia não consegue observar — mais a razão de não
-- tratar e o estado da doença ao fim do primeiro tratamento.
--
-- Os dois ficam fora do Postgres pelo critério de sempre: não há tela que os
-- consulte, e o Parquet já é citável, versionado e com checksum. São também um
-- recorte ESTRITAMENTE mais grosso que o microdado que o INCA publica aberto,
-- então agregá-los aqui não acrescenta risco de identificação nenhum.

alter table mart_rhc_cobertura
    add column if not exists sexo_ignorado                integer not null default 0,
    add column if not exists idade_ignorada               integer not null default 0,
    add column if not exists raca_ignorada                integer not null default 0,
    add column if not exists escolaridade_ignorada        integer not null default 0,
    add column if not exists primeiro_tratamento_ignorado integer not null default 0,
    add column if not exists com_data_obito               integer not null default 0;

comment on table mart_rhc_cobertura is
    'RHC/INCA: o que entrou em cada ano e UF, e o que faltou. A unidade é a '
    'PESSOA (caso com confirmação histopatológica), não a autorização. O ano é '
    'o da PRIMEIRA CONSULTA no hospital, não o do diagnóstico. Os valores '
    'anteriores a 2026-09-21 estavam DOBRADOS: o exportador do INCA grava cada '
    'página de 50.000 registros duas vezes — ver V051.';

comment on column mart_rhc_cobertura.casos is
    'Casos, já corrigidos da duplicação de página do exportador do INCA. A '
    'primeira publicação trazia o dobro (2022: 461.166 no ar, 230.583 reais), '
    'e nenhuma guarda de forma pegou, porque duplicação uniforme preserva '
    'toda proporção.';

comment on column mart_rhc_cobertura.raca_ignorada is
    'Casos com RACACOR = 9 ("sem informação") ou fora do dicionário do INCA. '
    'São ~9% em 2019. Zero nesta coluna seria a assinatura de o código 9 ter '
    'voltado a ser lido como categoria válida — há guarda para isso.';

comment on column mart_rhc_cobertura.escolaridade_ignorada is
    'Casos com INSTRUC = 9 ou fora do dicionário. São ~24,7% em 2019, e a '
    'ausência NÃO é aleatória: quem tem escolaridade ausente tem perfil de '
    'prazo diferente de quem a declara, então excluí-los enviesa.';

comment on column mart_rhc_cobertura.sexo_ignorado is
    'SEXO fora de {1,2}. O código 0 EXISTE no dado (dois registros em 2019) e '
    'NÃO existe no r_sexo.cnv do próprio INCA.';

comment on column mart_rhc_cobertura.idade_ignorada is
    'IDADE = 999 ("sem informação" no r_fxeta5.cnv) ou não numérica. Vazio '
    'nunca é lido como zero ano.';

comment on column mart_rhc_cobertura.primeiro_tratamento_ignorado is
    'PRITRATH = 9 ("sem informação"). NÃO inclui o código 1, que é "nenhum" — '
    'tratamento não recebido é resposta, não ausência, e confundir os dois '
    'apaga o denominador de qualquer estudo de acesso.';

comment on column mart_rhc_cobertura.com_data_obito is
    'Casos com DATAOBITO preenchida de verdade: ~15,9%. O campo vem com a '
    'máscara literal "/  /" em 83% dos registros, e um `if valor.strip()` a '
    'conta como preenchida — foi assim que ela mediu 99,6%. NÃO serve para '
    'sobrevida: sem seguimento sistemático, "sem data" e "vivo" são '
    'indistinguíveis, e um Kaplan-Meier sobre isto trataria ausência como '
    'censura informativa. É contagem de completude, e só.';
