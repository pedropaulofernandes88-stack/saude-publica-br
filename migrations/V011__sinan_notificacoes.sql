-- =============================================================================
-- V011__sinan_notificacoes.sql
-- Tabela de notificações do SINAN (Sistema de Informação de Agravos de
-- Notificação) — doenças: dengue (DENG), chikungunya (CHIK), zika (ZIKA).
--
-- Estratégia de particionamento: por uf_notif (HASH 27 partições)
-- Índices: (agravo, ano_notif, mes_notif), (municipio_notif), (classi_fin)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Tabela principal
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.sinan_notificacoes (
    -- Identificação
    nu_notific          TEXT,                       -- número de notificação
    agravo              TEXT NOT NULL,              -- DENG | CHIK | ZIKA
    dt_notific          TEXT,                       -- AAAAMMDD
    ano_notif           SMALLINT,
    mes_notif           SMALLINT,

    -- Localização de notificação
    uf_notif            CHAR(2) NOT NULL,           -- UF do serviço notificador
    municipio_notif     TEXT,                       -- código IBGE 6 dígitos
    cnes_unidade        TEXT,                       -- CNES da unidade notificadora

    -- Localização de residência
    uf_res              CHAR(2),
    municipio_res       TEXT,

    -- Dados do paciente
    dt_sin_pri          TEXT,                       -- data primeiros sintomas
    dt_nasc             TEXT,
    nu_idade_n          SMALLINT,                   -- idade codificada PySUS
    idade_anos          SMALLINT,                   -- idade em anos (calculada)
    cs_sexo             CHAR(1),                    -- M | F | I
    cs_raca             SMALLINT,                   -- 1=branca…5=indígena
    cs_gestant          SMALLINT,                   -- 1=1T 2=2T 3=3T 4=idade gest.

    -- Classificação e desfecho
    classi_fin          SMALLINT,                   -- 1=dengue 2=c/sinais alarme 3=grave | 1=chik confirmado | 1=zika confirmado
    criterio            SMALLINT,                   -- 1=laboratorial 2=clínico-epid
    evolucao            SMALLINT,                   -- 1=cura 2=óbito doença 3=óbito outras 4=óbito investigação 9=ignorado
    dt_obito            TEXT,
    dt_encerra          TEXT,                       -- data de encerramento

    -- Manifestações clínicas (dengue/chik)
    febre               SMALLINT,                   -- 1=sim 2=não
    mialgia             SMALLINT,
    cefaleia            SMALLINT,
    exantema            SMALLINT,
    vomito              SMALLINT,
    artralgia           SMALLINT,
    artrite             SMALLINT,

    -- Exames laboratoriais
    sorotipo            SMALLINT,                   -- 1=DEN1 2=DEN2 3=DEN3 4=DEN4 (dengue)
    resul_ns1           SMALLINT,                   -- 1=positivo 2=negativo 3=inconclusivo
    resul_prnt          SMALLINT,
    resul_soro          SMALLINT,
    resul_pcr           SMALLINT,
    dt_soro             TEXT,
    dt_pcr              TEXT,

    -- Metadados de carga
    uf_arquivo          CHAR(2),
    loaded_at           TIMESTAMPTZ DEFAULT NOW()
)
PARTITION BY LIST (uf_notif);

-- ---------------------------------------------------------------------------
-- Partições por UF
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    ufs TEXT[] := ARRAY[
        'AC','AL','AP','AM','BA','CE','DF','ES','GO',
        'MA','MT','MS','MG','PA','PB','PR','PE','PI',
        'RJ','RN','RS','RO','RR','SC','SP','SE','TO'
    ];
    uf TEXT;
BEGIN
    FOREACH uf IN ARRAY ufs LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS public.sinan_notificacoes_%s
             PARTITION OF public.sinan_notificacoes
             FOR VALUES IN (%L)',
            lower(uf), uf
        );
    END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- Índices
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_sinan_agravo_periodo
    ON public.sinan_notificacoes (agravo, ano_notif, mes_notif);

CREATE INDEX IF NOT EXISTS idx_sinan_municipio_notif
    ON public.sinan_notificacoes (municipio_notif);

CREATE INDEX IF NOT EXISTS idx_sinan_municipio_res
    ON public.sinan_notificacoes (municipio_res);

CREATE INDEX IF NOT EXISTS idx_sinan_classi_fin
    ON public.sinan_notificacoes (agravo, classi_fin);

CREATE INDEX IF NOT EXISTS idx_sinan_evolucao
    ON public.sinan_notificacoes (evolucao)
    WHERE evolucao IN (2, 3);  -- óbitos

-- ---------------------------------------------------------------------------
-- Row-Level Security
-- ---------------------------------------------------------------------------

ALTER TABLE public.sinan_notificacoes ENABLE ROW LEVEL SECURITY;

CREATE POLICY sinan_anon_read
    ON public.sinan_notificacoes
    FOR SELECT
    USING (true);

-- ---------------------------------------------------------------------------
-- Comentários
-- ---------------------------------------------------------------------------

COMMENT ON TABLE public.sinan_notificacoes IS
    'Notificações SINAN — dengue (DENG), chikungunya (CHIK), zika (ZIKA).
     Particionada por uf_notif. Fonte: DataSUS via PySUS.';

COMMENT ON COLUMN public.sinan_notificacoes.agravo IS
    'Código do agravo: DENG=dengue, CHIK=chikungunya, ZIKA=zika';

COMMENT ON COLUMN public.sinan_notificacoes.classi_fin IS
    'Classificação final: dengue→1=dengue/2=c/sinais alarme/3=grave; chik/zika→1=confirmado/2=descartado/8=inconclusivo';

COMMENT ON COLUMN public.sinan_notificacoes.nu_idade_n IS
    'Idade codificada DataSUS: centena=unidade (1=dias,2=meses,3=anos), ex: 320=20 anos';
