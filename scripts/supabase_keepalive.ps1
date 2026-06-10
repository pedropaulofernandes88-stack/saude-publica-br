# Keep-alive do Supabase free tier (pausa após 7 dias sem requisições).
# Registrado no Agendador de Tarefas do Windows para rodar a cada 6 dias.
# A anon key é pública por design (somente leitura via RLS).

$url = "https://zekjhmxjamatlxpkykde.supabase.co/rest/v1/meta_dataset?select=chave,valor&chave=eq.gerado_em"
$key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpla2pobXhqYW1hdGx4cGt5a2RlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwNzY4MzIsImV4cCI6MjA5NjY1MjgzMn0.px8FcU0QK8w9v95kwGlGzASKpY3drsxAvFe0e6wUoCU"

try {
    $resp = Invoke-RestMethod -Uri $url -Headers @{ apikey = $key } -TimeoutSec 60
    $log = "$(Get-Date -Format o) OK $($resp | ConvertTo-Json -Compress)"
} catch {
    $log = "$(Get-Date -Format o) ERRO $($_.Exception.Message)"
}
Add-Content -Path (Join-Path $PSScriptRoot "supabase_keepalive.log") -Value $log -Encoding utf8
