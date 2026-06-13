import io
import tempfile
from ftplib import FTP
from pathlib import Path

import datasus_dbc
import dbfread


def grab(path: str, name: str):
    ftp = FTP('ftp.datasus.gov.br', timeout=120)
    ftp.login()
    buf = io.BytesIO()
    ftp.retrbinary(f'RETR {path}', buf.write)
    ftp.quit()
    tmp = Path(tempfile.gettempdir())
    dbc = tmp / f'{name}.dbc'
    dbf = tmp / f'{name}.dbf'
    dbc.write_bytes(buf.getvalue())
    datasus_dbc.decompress(str(dbc), str(dbf))
    rows = []
    for i, rec in enumerate(dbfread.DBF(str(dbf), encoding='latin-1', char_decode_errors='replace')):
        rows.append(rec)
        if i >= 2:
            break
    dbf2 = dbfread.DBF(str(dbf), encoding='latin-1')
    return list(dbf2.field_names), rows


# SINAN dengue 2024
campos, amostra = grab('/dissemin/publicos/SINAN/DADOS/FINAIS/DENGBR24.dbc', 'DENG24')
print('=== DENGBR24 ===')
print('n campos:', len(campos))
chave = [c for c in campos if c in (
    'ID_MUNICIP', 'DT_NOTIFIC', 'DT_SIN_PRI', 'SEM_NOT', 'SEM_PRI', 'NU_ANO', 'ANO',
    'CLASSI_FIN', 'CRITERIO', 'EVOLUCAO', 'CS_SEXO', 'NU_IDADE_N', 'SG_UF_NOT', 'ID_MN_RESI', 'SG_UF')]
print('campos-chave presentes:', chave)
print('amostra[0] (subset):', {k: amostra[0].get(k) for k in chave})

# SIH RD SP 2024-01
campos2, amostra2 = grab('/dissemin/publicos/SIHSUS/200801_/Dados/RDSP2401.dbc', 'RDSP2401')
print()
print('=== RDSP2401 ===')
print('n campos:', len(campos2))
chave2 = [c for c in campos2 if c in (
    'MUNIC_RES', 'MUNIC_MOV', 'ANO_CMPT', 'MES_CMPT', 'DIAG_PRINC', 'PROC_REA',
    'DIAS_PERM', 'VAL_TOT', 'MORTE', 'SEXO', 'IDADE', 'COD_IDADE', 'UF_ZI', 'CAR_INT')]
print('campos-chave presentes:', chave2)
print('amostra[0] (subset):', {k: amostra2[0].get(k) for k in chave2})
