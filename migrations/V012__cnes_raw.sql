-- =============================================================================
-- V012__cnes_raw.sql
-- Tabelas do CNES (Cadastro Nacional de Estabelecimentos de Saúde).
--
-- Grupos implementados:
--   cnes_estabelecimentos (ST) — identificação e classificação das unidades
--   cnes_leitos          (LT) — capacidade de leitos por estabelecimento
--
-- Particionamento: por uf (LIST, 27 UFs)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- cnes_estabelecimentos (grupo ST)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.cnes_estabelecimentos (
    -- Identificação
    cnes                TEXT NOT NULL,              -- código CNES (7 dígitos)
    ano_cmpt            SMALLINT NOT NULL,
    mes_cmpt            SMALLINT NOT NULL,
    uf                  CHAR(2) NOT NULL,           -- UF do estabelecimento

    -- Localização
    municipio_cod       TEXT,                       -- código IBGE 6 dígitos
    municipio_nome      TEXT,
    cep                 TEXT,
    tp_unid             TEXT,                       -- tipo de unidade (código)
    tp_unid_desc        TEXT,                       -- descrição do tipo

    -- Identificação do prestador
    cnpj_mantenedora    TEXT,
    pf_pj               CHAR(1),                    -- F=física J=jurídica
    tp_prest            TEXT,                       -- tipo de prestador

    -- Esfera administrativa
    esfera_adm          TEXT,                       -- 1=federal 2=estadual 3=municipal 4=privado
    ret_obrig           TEXT,                       -- retaguarda obrigatória

    -- Natureza jurídica
    nat_jur             TEXT,

    -- Nível de atenção
    nivel_dep           TEXT,                       -- nível de dependência
    tp_gestao           TEXT,                       -- E=estadual M=municipal D=dupla

    -- Capacidades
    qt_leitos_sus       SMALLINT,
    qt_leitos_nao_sus   SMALLINT,
    qt_amb_sus          SMALLINT,
    qt_amb_nao_sus      SMALLINT,
    qt_cons_sus         SMALLINT,

    -- Serviços especializados (flags 0/1)
    serv_uti            SMALLINT,                   -- UTI
    serv_emer           SMALLINT,                   -- emergência
    serv_cirg           SMALLINT,                   -- cirurgia
    serv_obstet         SMALLINT,                   -- obstetrícia
    serv_hemot          SMALLINT,                   -- hemoterapia
    serv_diag           SMALLINT,                   -- diagnóstico/apoio

    -- Habilitações
    vinc_sus            CHAR(1),                    -- S=sim N=não

    -- Metadados
    uf_arquivo          CHAR(2),
    loaded_at           TIMESTAMPTZ DEFAULT NOW()
)
PARTITION BY LIST (uf);

-- ---------------------------------------------------------------------------
-- cnes_leitos (grupo LT)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.cnes_leitos (
    -- Identificação
    cnes                TEXT NOT NULL,
    ano_cmpt            SMALLINT NOT NULL,
    mes_cmpt            SMALLINT NOT NULL,
    uf                  CHAR(2) NOT NULL,

    -- Localização
    municipio_cod       TEXT,

    -- Tipo de leito
    tp_leito            TEXT,                       -- código tipo de leito
    tp_leito_desc       TEXT,                       -- descrição

    -- Especialidade
    cod_espec           TEXT,
    cod_espec_desc      TEXT,

    -- Quantidades
    qt_exist            SMALLINT,                   -- leitos existentes
    qt_sus              SMALLINT,                   -- leitos SUS
    qt_nao_sus          SMALLINT,                   -- leitos não-SUS
    qt_contr            SMALLINT,                   -- leitos contratualizados

    -- Metadados
    uf_arquivo          CHAR(2),
    loaded_at           TIMESTAMPTZ DEFAULT NOW()
)
PARTITION BY LIST (uf);

-- ---------------------------------------------------------------------------
-- Partições cnes_estabelecimentos
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
            'CREATE TABLE IF NOT EXISTS public.cnes_estabelecimentos_%s
             PARTITION OF public.cnes_estabelecimentos
             FOR VALUES IN (%L)',
            lower(uf), uf
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS public.cnes_leitos_%s
             PARTITION OF public.cnes_leitos
             FOR VALUES IN (%L)',
            lower(uf), uf
        );
    END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- Índices — cnes_estabelecimentos
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_cnes_estab_periodo
    ON public.cnes_estabelecimentos (ano_cmpt, mes_cmpt);

CREATE INDEX IF NOT EXISTS idx_cnes_estab_municipio
    ON public.cnes_estabelecimentos (municipio_cod);

CREATE INDEX IF NOT EXISTS idx_cnes_estab_tipo
    ON public.cnes_estabelecimentos (tp_unid);

CREATE INDEX IF NOT EXISTS idx_cnes_estab_vinc_sus
    ON public.cnes_estabelecimentos (vinc_sus)
    WHERE vinc_sus = 'S';

-- Índices — cnes_leitos
CREATE INDEX IF NOT EXISTS idx_cnes_leitos_periodo
    ON public.cnes_leitos (ano_cmpt, mes_cmpt);

CREATE INDEX IF NOT EXISTS idx_cnes_leitos_municipio
    ON public.cnes_leitos (municipio_cod);

CREATE INDEX IF NOT EXISTS idx_cnes_leitos_tipo
    ON public.cnes_leitos (tp_leito);

-- ---------------------------------------------------------------------------
-- Row-Level Security
-- ---------------------------------------------------------------------------

ALTER TABLE public.cnes_estabelecimentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cnes_leitos ENABLE ROW LEVEL SECURITY;

CREATE POLICY cnes_estab_anon_read
    ON public.cnes_estabelecimentos FOR SELECT USING (true);

CREATE POLICY cnes_leitos_anon_read
    ON public.cnes_leitos FOR SELECT USING (true);

-- ---------------------------------------------------------------------------
-- Comentários
-- ---------------------------------------------------------------------------

COMMENT ON TABLE public.cnes_estabelecimentos IS
    'CNES grupo ST — estabelecimentos de saúde cadastrados. Particionado por UF.
     Fonte: DataSUS via PySUS. Atualização mensal.';

COMMENT ON TABLE public.cnes_leitos IS
    'CNES grupo LT — leitos por estabelecimento e tipo. Particionado por UF.
     Fonte: DataSUS via PySUS. Atualização mensal.';

COMMENT ON COLUMN public.cnes_estabelecimentos.vinc_sus IS
    'S = estabelecimento vinculado ao SUS (presta serviços SUS)';

COMMENT ON COLUMN public.cnes_leitos.qt_exist IS
    'Total de leitos existentes no estabelecimento para este tipo/especialidade';
