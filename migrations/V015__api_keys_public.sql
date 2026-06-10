-- =============================================================================
-- V015 — API Pública v1.0: chaves de API, tiers, rate limiting e usage tracking
-- =============================================================================

-- ── Enum: tiers da API pública ────────────────────────────────────────────────
CREATE TYPE api_tier AS ENUM ('free', 'pro', 'enterprise');

-- ── Tabela principal de API keys ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.api_keys (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID        REFERENCES auth.users(id) ON DELETE CASCADE,
    nome          TEXT        NOT NULL,          -- nome descritivo (ex.: "Meu projeto TCC")
    key_hash      TEXT        UNIQUE NOT NULL,   -- SHA-256 da chave real (nunca armazenada)
    key_prefix    CHAR(8)     NOT NULL,          -- prefixo exibido (spbr_xxxx) para identificação
    tier          api_tier    NOT NULL DEFAULT 'free',
    ativa         BOOLEAN     NOT NULL DEFAULT true,
    descricao     TEXT,
    scopes        TEXT[]      NOT NULL DEFAULT ARRAY['read'],  -- ['read','export']
    -- limites (NULL = sem limite)
    rate_limit_hora  INTEGER DEFAULT 100,        -- requisições por hora
    rate_limit_dia   INTEGER DEFAULT 1000,       -- requisições por dia
    -- contadores acumulados (atualizados via trigger)
    total_requests   BIGINT  NOT NULL DEFAULT 0,
    ultimo_uso       TIMESTAMPTZ,
    -- metadados
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    expira_em     TIMESTAMPTZ,                   -- NULL = não expira
    CONSTRAINT key_prefix_format CHECK (key_prefix ~ '^[a-zA-Z0-9]{8}$')
);

-- rate limits por tier (referência)
COMMENT ON TABLE public.api_keys IS
    'Chaves de acesso à API pública v1. '
    'free: 100 req/h · pro: 5000 req/h · enterprise: sem limite. '
    'Apenas key_prefix fica visível; key_hash (SHA-256) é o segredo.';

-- ── Tabela de uso da API (time-series) ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.api_usage_log (
    id            BIGSERIAL   PRIMARY KEY,
    api_key_id    UUID        NOT NULL REFERENCES public.api_keys(id) ON DELETE CASCADE,
    endpoint      TEXT        NOT NULL,   -- ex.: /v1/producao
    metodo        TEXT        NOT NULL DEFAULT 'GET',
    status_code   SMALLINT    NOT NULL,
    duracao_ms    INTEGER,               -- latência em milissegundos
    uf_filtro     CHAR(2),              -- UF consultada (para analytics)
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY RANGE (criado_em);

-- partições mensais para 2026
CREATE TABLE api_usage_log_2026_05 PARTITION OF public.api_usage_log
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE api_usage_log_2026_06 PARTITION OF public.api_usage_log
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE api_usage_log_2026_07 PARTITION OF public.api_usage_log
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE api_usage_log_2026_08 PARTITION OF public.api_usage_log
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE api_usage_log_2026_09 PARTITION OF public.api_usage_log
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE api_usage_log_2026_10 PARTITION OF public.api_usage_log
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE api_usage_log_2026_11 PARTITION OF public.api_usage_log
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE api_usage_log_2026_12 PARTITION OF public.api_usage_log
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

-- ── Índices ───────────────────────────────────────────────────────────────────
CREATE INDEX ON public.api_keys(user_id);
CREATE INDEX ON public.api_keys(key_hash);
CREATE INDEX ON public.api_keys(ativa) WHERE ativa = true;
CREATE INDEX ON public.api_usage_log(api_key_id, criado_em);

-- ── View: contagem de uso na janela atual ─────────────────────────────────────
CREATE VIEW public.v_api_rate_limit AS
SELECT
    k.id              AS api_key_id,
    k.tier,
    k.rate_limit_hora,
    k.rate_limit_dia,
    COALESCE((
        SELECT COUNT(*) FROM public.api_usage_log u
        WHERE u.api_key_id = k.id
          AND u.criado_em  >= now() - INTERVAL '1 hour'
    ), 0)             AS uso_ultima_hora,
    COALESCE((
        SELECT COUNT(*) FROM public.api_usage_log u
        WHERE u.api_key_id = k.id
          AND u.criado_em  >= now() - INTERVAL '24 hours'
    ), 0)             AS uso_ultimo_dia
FROM public.api_keys k
WHERE k.ativa = true;

-- ── Função: criar API key (retorna chave real UMA ÚNICA VEZ) ─────────────────
CREATE OR REPLACE FUNCTION public.criar_api_key(
    p_user_id   UUID,
    p_nome      TEXT,
    p_tier      api_tier  DEFAULT 'free',
    p_descricao TEXT      DEFAULT NULL,
    p_scopes    TEXT[]    DEFAULT ARRAY['read']
) RETURNS TABLE (
    key_id        UUID,
    chave_real    TEXT,   -- retornada apenas aqui, nunca mais
    key_prefix    TEXT,
    tier          api_tier
) LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_raw_key  TEXT;
    v_prefix   TEXT;
    v_hash     TEXT;
    v_id       UUID;
    v_rl_hora  INTEGER;
    v_rl_dia   INTEGER;
BEGIN
    -- gera chave aleatória: prefixo fixo + 48 chars hex
    v_prefix  := left(replace(gen_random_uuid()::text, '-', ''), 8);
    v_raw_key := 'spbr_' || v_prefix || '_' || encode(gen_random_bytes(32), 'hex');
    v_hash    := encode(digest(v_raw_key, 'sha256'), 'hex');

    -- define rate limits por tier
    v_rl_hora := CASE p_tier
        WHEN 'free'       THEN 100
        WHEN 'pro'        THEN 5000
        WHEN 'enterprise' THEN NULL   -- sem limite
    END;
    v_rl_dia := CASE p_tier
        WHEN 'free'       THEN 1000
        WHEN 'pro'        THEN 100000
        WHEN 'enterprise' THEN NULL
    END;

    INSERT INTO public.api_keys
        (user_id, nome, key_hash, key_prefix, tier, descricao, scopes, rate_limit_hora, rate_limit_dia)
    VALUES
        (p_user_id, p_nome, v_hash, v_prefix, p_tier, p_descricao, p_scopes, v_rl_hora, v_rl_dia)
    RETURNING id INTO v_id;

    RETURN QUERY SELECT v_id, v_raw_key, v_prefix, p_tier;
END;
$$;

-- ── Função: verificar API key + rate limit ────────────────────────────────────
CREATE OR REPLACE FUNCTION public.verificar_api_key(p_chave TEXT)
RETURNS TABLE (
    valida        BOOLEAN,
    api_key_id    UUID,
    user_id       UUID,
    tier          api_tier,
    scopes        TEXT[],
    rate_limit_ok BOOLEAN,
    uso_hora      BIGINT,
    limite_hora   INTEGER
) LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_hash      TEXT;
    v_key       RECORD;
    v_uso_hora  BIGINT;
BEGIN
    v_hash := encode(digest(p_chave, 'sha256'), 'hex');

    SELECT k.* INTO v_key
    FROM public.api_keys k
    WHERE k.key_hash = v_hash AND k.ativa = true;

    IF NOT FOUND THEN
        RETURN QUERY SELECT false, NULL::UUID, NULL::UUID, NULL::api_tier,
                            NULL::TEXT[], false, 0::BIGINT, NULL::INTEGER;
        RETURN;
    END IF;

    -- checa expiração
    IF v_key.expira_em IS NOT NULL AND v_key.expira_em < now() THEN
        RETURN QUERY SELECT false, NULL::UUID, NULL::UUID, NULL::api_tier,
                            NULL::TEXT[], false, 0::BIGINT, NULL::INTEGER;
        RETURN;
    END IF;

    -- conta uso na última hora
    SELECT COUNT(*) INTO v_uso_hora
    FROM public.api_usage_log
    WHERE api_key_id = v_key.id AND criado_em >= now() - INTERVAL '1 hour';

    -- atualiza ultimo_uso (não-bloqueante)
    UPDATE public.api_keys
    SET ultimo_uso = now(), total_requests = total_requests + 1
    WHERE id = v_key.id;

    RETURN QUERY SELECT
        true,
        v_key.id,
        v_key.user_id,
        v_key.tier,
        v_key.scopes,
        (v_key.rate_limit_hora IS NULL OR v_uso_hora < v_key.rate_limit_hora),
        v_uso_hora,
        v_key.rate_limit_hora;
END;
$$;

-- ── Endpoint: listar chaves do usuário (RLS via app.current_user_id) ──────────
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "api_keys_owner" ON public.api_keys
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

-- ── Grants mínimos ────────────────────────────────────────────────────────────
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT ON public.v_api_rate_limit TO authenticated;
GRANT SELECT ON public.api_keys TO authenticated;
