import os
import dbfread

for name in ['DENG24', 'RDSP2401']:
    p = os.path.join(os.environ['TEMP'], f'{name}.dbf')
    if not os.path.exists(p):
        print(name, 'ausente'); continue
    t = dbfread.DBF(p, encoding='latin-1', load=False)
    print(f'=== {name} === {len(t)} registros, {len(t.field_names)} campos')
    # só o cabeçalho + 1 registro
    it = iter(t)
    r0 = next(it)
    interesse = {
        'DENG24': ['ID_MUNICIP','ID_MN_RESI','DT_NOTIFIC','DT_SIN_PRI','SEM_PRI','SEM_NOT',
                   'NU_ANO','CLASSI_FIN','CRITERIO','EVOLUCAO','CS_SEXO','NU_IDADE_N','SG_UF'],
        'RDSP2401': ['MUNIC_RES','MUNIC_MOV','ANO_CMPT','MES_CMPT','DIAG_PRINC','PROC_REA',
                     'DIAS_PERM','VAL_TOT','MORTE','SEXO','IDADE','COD_IDADE','CAR_INT','UF_ZI'],
    }[name]
    presentes = [c for c in interesse if c in t.field_names]
    print('  presentes:', presentes)
    print('  amostra:', {k: r0.get(k) for k in presentes})
    print()
