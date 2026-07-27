-- =============================================================================
-- V018 — Desfazer inscrição pendente quando o envio do e-mail falha
-- =============================================================================
-- Descoberto na primeira inscrição real: o provedor de e-mail recusou o envio
-- DEPOIS de a inscrição já ter sido gravada. Isso deixava o assinante num beco
-- sem saída:
--   1. existe uma linha pendente que ele não consegue confirmar (o link com o
--      token nunca chegou, porque o e-mail não saiu);
--   2. ao tentar de novo dentro de uma hora, o anti-abuso de `alerta_assinar`
--      responde {ok:true, throttled:true} sem reenviar nada — a Edge Function
--      devolve sucesso e nenhum e-mail chega. Falha silenciosa.
--
-- Esta função desfaz a pendência para que a retentativa funcione de imediato.
-- Nunca remove quem já confirmou.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.alerta_desfazer_pendente(p_token uuid)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = alertas, public, pg_catalog
AS $$
DECLARE removidos integer;
BEGIN
  DELETE FROM alertas.assinantes
   WHERE token_confirmacao = p_token
     AND confirmado_em IS NULL;   -- nunca remove quem já confirmou
  GET DIAGNOSTICS removidos = ROW_COUNT;
  RETURN removidos > 0;
END;
$$;

REVOKE ALL ON FUNCTION public.alerta_desfazer_pendente(uuid) FROM public, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.alerta_desfazer_pendente(uuid) TO service_role;
