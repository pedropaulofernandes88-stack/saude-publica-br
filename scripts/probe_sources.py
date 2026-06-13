import requests
from ftplib import FTP

MB = 1000000

sinan = set()
for y in ['2024', '2023', '2022', '21', '22', '23', '24']:
    sinan.add(f'https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/DENG/DENGBR{y}.csv')
    sinan.add(f'https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/dengue/DENGBR{y}.csv')
for u in sinan:
    try:
        r = requests.head(u, timeout=15)
        if r.status_code == 200:
            print('SINAN CSV OK', int(r.headers.get('Content-Length', 0)) // MB, 'MB', u)
    except Exception:
        pass

ftp = FTP('ftp.datasus.gov.br', timeout=60)
ftp.login()
for d in ['/dissemin/publicos/SINAN/DADOS/FINAIS', '/dissemin/publicos/SINAN/DADOS/PRELIM',
          '/dissemin/publicos/SIHSUS/200801_/Dados']:
    try:
        names = [n.split('/')[-1] for n in ftp.nlst(d)]
        deng = [s for s in names if s.upper().startswith('DENG')][:8]
        rd = [s for s in names if s.upper().startswith('RD')][:8]
        print(d, '| total', len(names), '| DENG:', deng, '| RD:', rd)
    except Exception as e:
        print(d, 'ERR', e)
# tamanho de um RD mensal de SP
try:
    sz = ftp.size('/dissemin/publicos/SIHSUS/200801_/Dados/RDSP2401.dbc')
    print('RDSP2401.dbc =', (sz or 0) // MB, 'MB')
except Exception as e:
    print('size RD err', e)
ftp.quit()
