# E-mail 3 de 3 — hídricas (SISAGUA × mortalidade intestinal)

**Para:** Helder Nakaya
**Assunto:** A alta da mortalidade por diarreia é real; a hipótese da água não sobrevive ao painel

---

Helder,

Terceiro e último. Este é o que mais mudou depois da sua revisão, e o que mudou
de conclusão.

**A alta existe e está melhor documentada do que antes.** Os óbitos por doenças
infecciosas intestinais passaram de 4.875 em 2019 para 7.177 em 2024. Você tinha
razão sobre a linha de base de um ano só: refiz contra uma tendência log-linear
ajustada apenas em 2015–2019, que é plana, com desvios entre −2,5% e +2,7%.
Contra ela, 2024 está **26,6% acima** medido por 10 mil óbitos do ano e **36%
acima** por milhão de habitantes.

**A hipótese hídrica não sobrevive.** Fiz o painel que você sugeriu — efeito
fixo de município, exposição defasada, cinco causas, bootstrap de município.
Dentro do município, ao longo de nove anos, a ausência de registro de vigilância
no ano anterior dá **IRR 0,99 [0,943–1,041]** para A00–A09, e 0,984, 0,996,
1,006 e 1,002 para os quatro controles. Nenhum exclui 1, e o maior de todos é o
das isquêmicas do coração.

**E dá para mostrar de onde vinha o 2,075 do desenho anterior.** Sem o efeito
fixo, no mesmo painel e com o mesmo código, o IRR é 1,074 para a causa
intestinal e **0,773** para o controle respiratório. Não era o desfecho estar
alto: era o controle estar baixo, e a razão de razões converteu o déficit do
denominador em excesso aparente do numerador. A prova de que isso não tinha nada
de específico está nas **causas externas** — acidentes e homicídios, que não
partilham caminho hídrico com nada — que produzem razão de razões de 1,339
contra o mesmo controle. E a dose-resposta que eu apresentava como apoio era a
do controle: a coluna dele é monotônica (0,558; 0,886; 0,903; 1) e a do desfecho
não é.

**Acrescentei a análise que remove a última escapatória.** A objeção óbvia ao
nulo é que a exposição media um ato administrativo — um município pode analisar
e não reportar. Então troquei a exposição: entre os município-anos em que
**houve** amostra reportada, ela passa a ser o que o laboratório encontrou,
*Escherichia coli* na água ou não. **IRR 0,991 [0,944–1,037]**, com os controles
em 1,009, 0,995, 1,018 e 0,997. Nulo de novo, e com mais informação que o painel
principal: 2.343 municípios mudam de estado de detecção e têm óbito intestinal,
contra 1.468 lá. O artefato previsível — quem coleta mais amostras acha mais
*E. coli* — foi testado e não explica: incluir o log do número de amostras move
o IRR para 0,985 sem trocar de direção em nenhuma causa.

**Duas correções que vieram de auditoria e que valem registro.** O denominador
populacional que eu usava era uma série remendada: estimativas até 2021, Censo
em 2022, interpolação em 2023. Com a série contínua da Revisão 2024 do IBGE, o
excesso de 2024 cai de 37,5% para 36% e **2022 troca de sinal**. E o conjunto
que identifica o efeito não são os 1.838 municípios que mudam de exposição, e
sim os 1.468 que mudam *e* têm óbito pela causa — município sem óbito algum sai
da verossimilhança condicional.

**O que eu proponho como enquadramento.** Não é "a água não importa". É que a
ausência de registro no SISAGUA — e a detecção de *E. coli* entre quem
registra — não antecede mortalidade detectavelmente maior dentro do município, e
que a associação transversal forte era composição. Para mim o valor do artigo
está tanto no achado quanto na demonstração de como um controle negativo bem
escolhido pode falhar sem que nenhum teste de sensibilidade do mesmo desenho
perceba.

Abraço,
Pedro

---

## Anexos

    artigo-agua/manuscrito-hidricas.docx
    artigo-agua/dados-hidricas.zip

## Procedência dos números citados

| Afirmação | Origem |
|---|---|
| 4.875 → 7.177 óbitos; excesso de 26,6% e 36% em 2024 | Tabela P4 |
| desvios de −2,5% a +2,7% na base 2015–2019 | Tabela P4 |
| IRR 0,99 [0,943–1,041] e os quatro controles | Tabela P2 |
| 1,074 e 0,773 sem efeito fixo; RRR 1,339 nas causas externas | Tabela P3 |
| 1.838 que mudam, 1.468 informativos | Tabela P1 |
| gradiente 0,558; 0,886; 0,903; 1 no controle | Tabela 7 |
| razão de razões de 2,075 no desenho transversal | Tabela 8 |
| IRR 0,991 [0,944–1,037] do E. coli e os controles | Tabela E2 |
| 2.343 municípios informativos na extensão | Tabela E1 |
| 0,991 → 0,985 ao ajustar por amostras | Tabela E4 |
