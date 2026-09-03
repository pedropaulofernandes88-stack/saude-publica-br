"""
reconciliacao_denominador.py — Série populacional reconciliada + teste de convergência
======================================================================================
Reconcilia o TOTAL populacional por UF interpolando geometricamente entre os Censos
2010 e 2022 (remove o overcount pré-Censo das estimativas e o degrau de 2022), aplica
a forma etária da projeção IBGE 2018 (validada: 60+ 12,3%->16,0%), e recomputa o
excesso de mortalidade padronizado por idade — testando se converge para o método de
tendência publicado (~643 mil no biênio pandêmico).

Resultado (ver metodologia §6): NÃO converge. Mesmo com denominador reconciliado, o
excesso padronizado (~530 mil) fica ~18% abaixo da tendência (643 mil) e do consenso
independente (~680 mil). O problema do excesso não era só o denominador — é
metodológico. O método de tendência foi retido por ter melhor validação externa.

Nota: uma reconciliação da ESTRUTURA etária censo-a-censo (não só do total) exige a
população por idade do Censo 2010 por UF, cujo agregado no SIDRA (t/1378) tem dimensões
adicionais (situação/parentesco) que precisam de tratamento cuidadoso — refinamento
pendente. Aqui usa-se a estrutura da projeção como aproximação declarada.
Uso: .venv311/Scripts/python scripts/reconciliacao_denominador.py
"""
from __future__ import annotations
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sim_obitos import caminho_populacao  # noqa: E402
import numpy as np, pandas as pd, requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]; REFS = ROOT/"data"/"refs"
UFCOD={11:'RO',12:'AC',13:'AM',14:'RR',15:'PA',16:'AP',17:'TO',21:'MA',22:'PI',23:'CE',24:'RN',25:'PB',26:'PE',27:'AL',28:'SE',29:'BA',31:'MG',32:'ES',33:'RJ',35:'SP',41:'PR',42:'SC',43:'RS',50:'MS',51:'MT',52:'GO',53:'DF'}

def env():
    e={}
    for ln in (ROOT/'.env').read_text(encoding='utf-8').splitlines():
        ln=ln.strip()
        if ln and not ln.startswith('#') and '=' in ln: k,_,v=ln.partition('='); e[k.strip()]=v.strip()
    e.update({k:v for k,v in os.environ.items() if k.startswith('SUPABASE')}); return e

def main():
    E=env(); URL=E['SUPABASE_URL'].rstrip('/'); KEY=E['SUPABASE_ANON_KEY']; H={"apikey":KEY,"Authorization":f"Bearer {KEY}"}
    # totais censitários
    j=requests.get("https://apisidra.ibge.gov.br/values/t/200/n3/all/v/93/p/2010",timeout=60).json()
    t2010={UFCOD[int(r['D1C'])]:float(r['V']) for r in j[1:]}
    pr=pd.read_parquet(caminho_populacao(REFS)); pr['uf']=pr.municipio_cod.astype(str).str[:2].astype(int).map(UFCOD)
    t2022=pr[pr.ano==2022].groupby('uf')['populacao'].sum().to_dict()
    def tot(uf,ano): return t2010[uf]*(t2022[uf]/t2010[uf])**((ano-2010)/12.0)
    # estrutura da projeção -> shares
    proj=pd.read_parquet(REFS/'pop_idade_uf_ano.parquet').rename(columns={'faixa':'fx','populacao':'pop'})
    proj['share']=proj['pop']/proj.groupby(['uf_sigla','ano'])['pop'].transform('sum')
    proj['pop']=proj.apply(lambda x: tot(x['uf_sigla'],x['ano'])*x['share'],axis=1)
    popr=proj[['uf_sigla','ano','fx','pop']].copy()
    popr.to_parquet(REFS/'pop_idade_uf_ano_reconciliada.parquet',index=False)
    # óbitos mensais por faixa (paginação ordenada)
    def rest(p):
        rows=[];off=0;sep='&' if '?' in p else '?'
        while True:
            r=requests.get(f"{URL}/rest/v1/{p}{sep}order=uf_sigla,ano,mes,faixa_etaria",headers={**H,"Range-Unit":"items","Range":f"{off}-{off+999}"},timeout=90)
            r.raise_for_status();c=r.json();rows+=c
            if len(c)<1000:break
            off+=1000
        return rows
    d=pd.DataFrame(rest("mart_mortalidade_uf_mes?capitulo_cid=eq.TOTAL&sexo=eq.TOTAL&faixa_etaria=neq.TOTAL&select=uf_sigla,ano,mes,faixa_etaria,obitos"))
    d['obitos']=d['obitos'].astype(int)
    m7={'<1':'0-4','1-4':'0-4','5-14':'5-14','15-29':'15-29','30-44':'30-44','45-59':'45-59','60-74':'60-74','75+':'75+'}
    ign=d[d.faixa_etaria=='IGN'].groupby(['uf_sigla','ano','mes'])['obitos'].sum().rename('ign')
    d=d[d.faixa_etaria!='IGN'].copy(); d['fx']=d.faixa_etaria.map(m7)
    g=d.groupby(['uf_sigla','ano','mes','fx'],as_index=False)['obitos'].sum().merge(ign,on=['uf_sigla','ano','mes'],how='left').fillna({'ign':0})
    tc=g.groupby(['uf_sigla','ano','mes'])['obitos'].transform('sum'); g['obitos']=(g['obitos']+g['ign']*g['obitos']/tc.replace(0,np.nan)).fillna(0)
    base=g[g.ano.between(2015,2019)].groupby(['uf_sigla','mes','fx'],as_index=False)['obitos'].sum().rename(columns={'obitos':'ob'})
    pb=popr[popr.ano.between(2015,2019)].groupby(['uf_sigla','fx'],as_index=False)['pop'].sum().rename(columns={'pop':'pb'})
    rate=base.merge(pb,on=['uf_sigla','fx']);rate['taxa']=rate.ob/rate.pb
    e=rate.merge(popr,on=['uf_sigla','fx']);e['esp']=e.taxa*e['pop']
    esp=e.groupby(['ano','mes'],as_index=False)['esp'].sum(); obs=g.groupby(['ano','mes'],as_index=False)['obitos'].sum().rename(columns={'obitos':'obs'})
    R=esp.merge(obs,on=['ano','mes']);R['exc']=R.obs-R.esp
    trA={}
    for mes in range(1,13):
        s=obs[(obs.mes==mes)&(obs.ano.between(2015,2019))];b,a0=np.polyfit(s.ano,s.obs,1)
        for ano in range(2020,2025):trA[(ano,mes)]=b*ano+a0
    def sA(a):return sum(obs[(obs.ano==y)&(obs.mes==m)].obs.values[0]-trA[(y,m)] for y in a for m in range(1,13))
    def sR(a):return R[R.ano.isin(a)].exc.sum()
    print(f"Pop nacional reconciliada 2020={popr[popr.ano==2020]['pop'].sum():,.0f} (era 211,8M nas estimativas antigas)")
    print(f"\n{'Período':<12}{'Tendência':>11}{'Reconciliado':>14}")
    for rot,a in [("2020-2021",[2020,2021]),("2022",[2022]),("2023",[2023]),("2024",[2024]),("2020-2024",list(range(2020,2025)))]:
        print(f"{rot:<12}{sA(a):>11,.0f}{sR(a):>14,.0f}")

if __name__=="__main__": main()
