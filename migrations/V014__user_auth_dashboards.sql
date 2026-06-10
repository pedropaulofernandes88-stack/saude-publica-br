-- ============================================================
-- V014 — Autenticação, Dashboards Customizáveis e Exportações
-- Fase 11: Portal Público com autenticação e personalização
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- 1. EXTENSÕES NECESSÁRIAS
-- ────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid(), crypt()

-- ────────────────────────────────────────────────────────────
-- 2. ENUM TIPOS
-- ────────────────────────────────────────────────────────────
CREATE TYPE auth.user_role AS ENUM ('viewer', 'analyst', 'admin');
CREATE TYPE auth.user_status AS ENUM ('pending', 'active', 'suspended');
CREATE TYPE public.export_format AS ENUM ('csv', 'excel', 'json');
CREATE TYPE public.export_status AS ENUM ('queued', 'processing', 'done', 'error');
CREATE TYPE public.widget_type AS ENUM (
    'bar_chart',
    'line_chart',
    'area_chart',
    'pie_chart',
    'map_choropleth',
    'kpi_card',
    'data_table',
    'ranking_table'
);

-- ────────────────────────────────────────────────────────────
-- 3. SCHEMA auth
-- ────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS auth;

-- Tabela de usuários
CREATE TABLE auth.users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL UNIQUE,
    nome            TEXT NOT NULL,
    senha_hash      TEXT NOT NULL,                          -- bcrypt via pgcrypto
    role            auth.user_role NOT NULL DEFAULT 'viewer',
    status          auth.user_status NOT NULL DEFAULT 'pending',
    email_verificado BOOLEAN NOT NULL DEFAULT FALSE,
    token_verificacao TEXT,                                  -- token de confirmação de email
    ultimo_login    TIMESTAMPTZ,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE auth.users IS 'Usuários registrados no portal público';
COMMENT ON COLUMN auth.users.senha_hash IS 'Hash bcrypt gerado com pgcrypto crypt()';

-- Índices
CREATE INDEX idx_users_email ON auth.users (email);
CREATE INDEX idx_users_status ON auth.users (status);

-- Tabela de refresh tokens (rotação segura)
CREATE TABLE auth.refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL UNIQUE,   -- SHA-256 do token real
    expirado_em     TIMESTAMPTZ NOT NULL,
    revogado        BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_origem       INET,
    user_agent      TEXT
);

COMMENT ON TABLE auth.refresh_tokens IS 'Refresh tokens com rotação; token real nunca armazenado';

CREATE INDEX idx_refresh_tokens_user ON auth.refresh_tokens (user_id);
CREATE INDEX idx_refresh_tokens_hash ON auth.refresh_tokens (token_hash) WHERE NOT revogado;

-- Trigger: atualiza updated_at em users
CREATE OR REPLACE FUNCTION auth.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON auth.users
    FOR EACH ROW EXECUTE FUNCTION auth.set_updated_at();

-- ────────────────────────────────────────────────────────────
-- 4. DASHBOARDS CUSTOMIZÁVEIS
-- ────────────────────────────────────────────────────────────

-- Dashboard: container com múltiplos widgets
CREATE TABLE public.dashboards (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    titulo          TEXT NOT NULL,
    descricao       TEXT,
    publico         BOOLEAN NOT NULL DEFAULT FALSE,   -- se TRUE, acessível sem auth
    slug            TEXT UNIQUE,                      -- URL amigável para dashboards públicos
    config          JSONB NOT NULL DEFAULT '{}',      -- filtros globais padrão
    thumbnail_url   TEXT,                             -- preview gerado automaticamente
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.dashboards IS 'Dashboards customizáveis por usuário';
COMMENT ON COLUMN public.dashboards.config IS 'Filtros globais padrão: {ufs, anos, meses, regioes}';
COMMENT ON COLUMN public.dashboards.slug IS 'URL amigável: /portal/d/{slug}';

CREATE INDEX idx_dashboards_user ON public.dashboards (user_id);
CREATE INDEX idx_dashboards_publico ON public.dashboards (publico) WHERE publico = TRUE;
CREATE INDEX idx_dashboards_slug ON public.dashboards (slug) WHERE slug IS NOT NULL;

-- Trigger updated_at para dashboards
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_dashboards_updated_at
    BEFORE UPDATE ON public.dashboards
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Widgets: elementos individuais de um dashboard
CREATE TABLE public.dashboard_widgets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id    UUID NOT NULL REFERENCES public.dashboards(id) ON DELETE CASCADE,
    tipo            public.widget_type NOT NULL,
    titulo          TEXT NOT NULL,
    posicao         JSONB NOT NULL DEFAULT '{"x":0,"y":0,"w":6,"h":4}',  -- grid 12 colunas
    config          JSONB NOT NULL DEFAULT '{}',  -- configuração específica do widget
    fonte           TEXT NOT NULL,                -- endpoint: 'producao', 'mortalidade', 'capacidade', 'doencas', 'ranking'
    filtros         JSONB NOT NULL DEFAULT '{}',  -- filtros específicos (override do dashboard)
    ordem           SMALLINT NOT NULL DEFAULT 0,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.dashboard_widgets IS 'Widgets individuais de cada dashboard';
COMMENT ON COLUMN public.dashboard_widgets.posicao IS 'Grid layout: {x, y, w, h} — grid 12 colunas';
COMMENT ON COLUMN public.dashboard_widgets.config IS 'Config do widget: {cores, metricas, eixos, topN}';
COMMENT ON COLUMN public.dashboard_widgets.filtros IS 'Override de filtros do dashboard pai';

CREATE INDEX idx_widgets_dashboard ON public.dashboard_widgets (dashboard_id);

-- Dashboards favoritos (bookmarks)
CREATE TABLE public.dashboard_favoritos (
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    dashboard_id    UUID NOT NULL REFERENCES public.dashboards(id) ON DELETE CASCADE,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, dashboard_id)
);

-- ────────────────────────────────────────────────────────────
-- 5. LOG DE EXPORTAÇÕES
-- ────────────────────────────────────────────────────────────
CREATE TABLE public.exports_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES auth.users(id) ON DELETE SET NULL,  -- NULL = exportação anônima
    endpoint        TEXT NOT NULL,          -- ex: 'nacional/producao'
    formato         public.export_format NOT NULL,
    filtros         JSONB NOT NULL DEFAULT '{}',
    total_linhas    INTEGER,                -- preenchido após conclusão
    tamanho_bytes   BIGINT,                 -- tamanho do arquivo gerado
    status          public.export_status NOT NULL DEFAULT 'queued',
    erro_msg        TEXT,
    iniciado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    concluido_em    TIMESTAMPTZ,
    ip_origem       INET
);

COMMENT ON TABLE public.exports_log IS 'Auditoria de exportações de dados';

CREATE INDEX idx_exports_user ON public.exports_log (user_id);
CREATE INDEX idx_exports_status ON public.exports_log (status);
CREATE INDEX idx_exports_iniciado ON public.exports_log (iniciado_em DESC);

-- ────────────────────────────────────────────────────────────
-- 6. RATE LIMITING POR USUÁRIO
-- ────────────────────────────────────────────────────────────
CREATE TABLE auth.rate_limit_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    ip          INET NOT NULL,
    endpoint    TEXT NOT NULL,
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rate_limit_user_ts ON auth.rate_limit_log (user_id, ts DESC);
CREATE INDEX idx_rate_limit_ip_ts ON auth.rate_limit_log (ip, ts DESC);

-- Limpa entradas > 1 hora automaticamente via particionamento temporal (simplificado)
CREATE OR REPLACE FUNCTION auth.cleanup_rate_limit()
RETURNS void LANGUAGE sql AS $$
    DELETE FROM auth.rate_limit_log WHERE ts < NOW() - INTERVAL '1 hour';
$$;

-- ────────────────────────────────────────────────────────────
-- 7. FUNÇÕES AUXILIARES
-- ────────────────────────────────────────────────────────────

-- Função: criar usuário com hash de senha bcrypt
CREATE OR REPLACE FUNCTION auth.criar_usuario(
    p_email   TEXT,
    p_nome    TEXT,
    p_senha   TEXT,
    p_role    auth.user_role DEFAULT 'viewer'
) RETURNS auth.users LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_user auth.users;
BEGIN
    INSERT INTO auth.users (email, nome, senha_hash, role, token_verificacao)
    VALUES (
        lower(trim(p_email)),
        trim(p_nome),
        crypt(p_senha, gen_salt('bf', 12)),   -- bcrypt custo 12
        p_role,
        encode(gen_random_bytes(32), 'hex')    -- token de verificação de email
    )
    RETURNING * INTO v_user;

    RETURN v_user;
END;
$$;

-- Função: verificar senha
CREATE OR REPLACE FUNCTION auth.verificar_senha(
    p_email TEXT,
    p_senha TEXT
) RETURNS auth.users LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
    v_user auth.users;
BEGIN
    SELECT * INTO v_user
    FROM auth.users
    WHERE email = lower(trim(p_email))
      AND status = 'active'
      AND senha_hash = crypt(p_senha, senha_hash);

    IF FOUND THEN
        -- Atualiza último login
        UPDATE auth.users SET ultimo_login = NOW() WHERE id = v_user.id;
        RETURN v_user;
    END IF;

    RETURN NULL;
END;
$$;

-- Função: verificar email
CREATE OR REPLACE FUNCTION auth.verificar_email(p_token TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE auth.users
    SET email_verificado = TRUE,
        status = 'active',
        token_verificacao = NULL
    WHERE token_verificacao = p_token
      AND status = 'pending';

    RETURN FOUND;
END;
$$;

-- ────────────────────────────────────────────────────────────
-- 8. DADOS INICIAIS
-- ────────────────────────────────────────────────────────────

-- Usuário admin padrão (senha: Admin@2024! — MUDAR EM PRODUÇÃO)
SELECT auth.criar_usuario(
    'admin@saude-publica-br.gov.br',
    'Administrador',
    'Admin@2024!',
    'admin'
);

UPDATE auth.users
SET status = 'active', email_verificado = TRUE, token_verificacao = NULL
WHERE email = 'admin@saude-publica-br.gov.br';

-- Dashboard público de demonstração
DO $$
DECLARE v_admin_id UUID;
BEGIN
    SELECT id INTO v_admin_id FROM auth.users WHERE email = 'admin@saude-publica-br.gov.br';

    INSERT INTO public.dashboards (user_id, titulo, descricao, publico, slug, config)
    VALUES (
        v_admin_id,
        'Panorama Nacional de Saúde 2019–2024',
        'Visão consolidada dos principais indicadores de saúde pública do Brasil',
        TRUE,
        'panorama-nacional',
        '{"anos": [2019,2020,2021,2022,2023,2024], "regioes": ["Norte","Nordeste","Centro-Oeste","Sudeste","Sul"]}'
    );

    -- Widgets do dashboard demo
    INSERT INTO public.dashboard_widgets
        (dashboard_id, tipo, titulo, posicao, fonte, filtros, ordem)
    SELECT
        id,
        widget_type::public.widget_type,
        titulo,
        posicao::jsonb,
        fonte,
        filtros::jsonb,
        ordem
    FROM (VALUES
        (
            (SELECT id FROM public.dashboards WHERE slug = 'panorama-nacional'),
            'kpi_card', 'Total de Procedimentos',
            '{"x":0,"y":0,"w":3,"h":2}', 'producao', '{}', 1
        ),
        (
            (SELECT id FROM public.dashboards WHERE slug = 'panorama-nacional'),
            'kpi_card', 'Total de Óbitos',
            '{"x":3,"y":0,"w":3,"h":2}', 'mortalidade', '{}', 2
        ),
        (
            (SELECT id FROM public.dashboards WHERE slug = 'panorama-nacional'),
            'kpi_card', 'Leitos SUS (mil)',
            '{"x":6,"y":0,"w":3,"h":2}', 'capacidade', '{}', 3
        ),
        (
            (SELECT id FROM public.dashboards WHERE slug = 'panorama-nacional'),
            'kpi_card', 'Casos Notificados',
            '{"x":9,"y":0,"w":3,"h":2}', 'doencas', '{}', 4
        ),
        (
            (SELECT id FROM public.dashboards WHERE slug = 'panorama-nacional'),
            'line_chart', 'Evolução de Procedimentos por Região',
            '{"x":0,"y":2,"w":8,"h":5}', 'producao',
            '{"agrupar_por":"regiao"}', 5
        ),
        (
            (SELECT id FROM public.dashboards WHERE slug = 'panorama-nacional'),
            'ranking_table', 'Ranking: Taxa de Mortalidade por Estado',
            '{"x":8,"y":2,"w":4,"h":5}', 'ranking',
            '{"metrica":"taxa_mortalidade_100k","ordem":"desc"}', 6
        ),
        (
            (SELECT id FROM public.dashboards WHERE slug = 'panorama-nacional'),
            'map_choropleth', 'Mapa: Leitos SUS por Estado',
            '{"x":0,"y":7,"w":6,"h":6}', 'capacidade',
            '{"metrica":"taxa_leitos_sus_1k"}', 7
        ),
        (
            (SELECT id FROM public.dashboards WHERE slug = 'panorama-nacional'),
            'bar_chart', 'Alertas Epidemiológicos Ativos',
            '{"x":6,"y":7,"w":6,"h":6}', 'doencas',
            '{"alertas":true}', 8
        )
    ) AS t(dashboard_id, widget_type, titulo, posicao, fonte, filtros, ordem);
END;
$$;

-- ────────────────────────────────────────────────────────────
-- 9. ROW LEVEL SECURITY (RLS)
-- ────────────────────────────────────────────────────────────
ALTER TABLE public.dashboards ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dashboard_widgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dashboard_favoritos ENABLE ROW LEVEL SECURITY;

-- Dashboards: público pode ler públicos; owner pode ler/escrever os seus
CREATE POLICY dashboards_select_public ON public.dashboards
    FOR SELECT USING (publico = TRUE);

CREATE POLICY dashboards_owner ON public.dashboards
    FOR ALL USING (user_id::text = current_setting('app.current_user_id', TRUE));

-- Widgets: herda acesso do dashboard pai
CREATE POLICY widgets_select ON public.dashboard_widgets
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.dashboards d
            WHERE d.id = dashboard_id
              AND (d.publico = TRUE OR d.user_id::text = current_setting('app.current_user_id', TRUE))
        )
    );

-- Favoritos: apenas o próprio usuário
CREATE POLICY favoritos_owner ON public.dashboard_favoritos
    FOR ALL USING (user_id::text = current_setting('app.current_user_id', TRUE));

-- ────────────────────────────────────────────────────────────
-- GRANT de permissões
-- ────────────────────────────────────────────────────────────
GRANT USAGE ON SCHEMA auth TO anon, authenticated;
GRANT SELECT ON auth.users TO authenticated;
GRANT ALL ON public.dashboards TO authenticated;
GRANT ALL ON public.dashboard_widgets TO authenticated;
GRANT ALL ON public.dashboard_favoritos TO authenticated;
GRANT INSERT, SELECT ON public.exports_log TO anon, authenticated;

