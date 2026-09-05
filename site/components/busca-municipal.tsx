"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { sdata } from "@/lib/api";
import { casaMunicipio } from "@/lib/busca";

/**
 * "Qual município você quer conhecer?" — a entrada por TERRITÓRIO.
 *
 * POR QUE ELA EXISTE
 * ------------------
 * O site se entra por TEMA: mortalidade, dengue, internações, atenção básica.
 * Quem chega com um município na cabeça — que é o gestor, o vereador, o
 * jornalista local — precisava escolher um tema, achar o painel, filtrar a UF,
 * baixar a lista e só então clicar no nome. O boletim municipal, que responde a
 * pergunta inteira numa página, ficava a cinco passos de distância.
 *
 * A lista dos 5.571 municípios é buscada na PRIMEIRA TECLA, nunca no
 * carregamento: são 173 kB que não servem a quem veio ver outra coisa.
 *
 * A BUSCA É A MESMA DO PAINEL
 * ---------------------------
 * `casaMunicipio` — acento opcional, caixa indiferente, código IBGE de 6 ou 7
 * dígitos. Uma definição só; duas divergiriam, e foi exatamente o que aconteceu
 * quando o normalizador existia copiado em duas páginas e faltava numa terceira.
 */

type Linha = [cod: string, nome: string, uf: string];

export function BuscaMunicipal() {
  const [termo, setTermo] = useState("");
  const [lista, setLista] = useState<Linha[] | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [ativo, setAtivo] = useState(0);
  const boxRef = useRef<HTMLDivElement>(null);

  const carregar = useCallback(() => {
    if (lista || carregando) return;
    setCarregando(true);
    sdata<Linha[]>("municipios")
      .then(setLista)
      .catch(() => setLista([]))
      .finally(() => setCarregando(false));
  }, [lista, carregando]);

  const q = termo.trim();
  const achados = q && lista
    ? lista.filter(([cod, nome]) => casaMunicipio(q, nome, cod)).slice(0, 8)
    : [];

  useEffect(() => { setAtivo(0); }, [termo]);

  // Fecha ao clicar fora, para a lista não ficar pendurada sobre o conteúdo.
  useEffect(() => {
    function fora(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setTermo("");
    }
    document.addEventListener("mousedown", fora);
    return () => document.removeEventListener("mousedown", fora);
  }, []);

  function abrir(cod: string) {
    window.location.href = `/boletim/?m=${cod}`;
  }

  function teclado(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!achados.length) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setAtivo((i) => (i + 1) % achados.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setAtivo((i) => (i - 1 + achados.length) % achados.length); }
    else if (e.key === "Enter") { e.preventDefault(); abrir(achados[ativo][0]); }
    else if (e.key === "Escape") { setTermo(""); }
  }

  return (
    <div ref={boxRef} className="relative mx-auto w-full max-w-xl">
      <label htmlFor="busca-home" className="sr-only">Buscar município</label>
      <input
        id="busca-home"
        className="w-full rounded-xl border border-ink-300 bg-white px-4 py-3 text-base text-ink-900 shadow-sm placeholder:text-ink-400 focus:border-accent-600 focus:outline-none focus:ring-1 focus:ring-accent-600"
        placeholder="Qual município você quer conhecer? — nome ou código IBGE"
        value={termo}
        autoComplete="off"
        role="combobox"
        aria-expanded={achados.length > 0}
        aria-controls="busca-home-lista"
        aria-autocomplete="list"
        onFocus={carregar}
        onChange={(e) => { carregar(); setTermo(e.target.value); }}
        onKeyDown={teclado}
      />

      {q && (
        <ul
          id="busca-home-lista"
          role="listbox"
          className="absolute z-20 mt-1 w-full overflow-hidden rounded-xl border border-ink-200 bg-white shadow-lg"
        >
          {carregando && <li className="px-4 py-3 text-sm text-ink-500">Carregando municípios…</li>}
          {!carregando && !achados.length && (
            <li className="px-4 py-3 text-sm text-ink-500">
              Nenhum município encontrado para “{q}”. Acento e maiúscula não importam; o código
              IBGE também funciona.
            </li>
          )}
          {achados.map(([cod, nome, uf], i) => (
            <li key={cod} role="option" aria-selected={i === ativo}>
              <button
                type="button"
                onMouseEnter={() => setAtivo(i)}
                onClick={() => abrir(cod)}
                className={`flex w-full items-baseline justify-between px-4 py-2.5 text-left text-sm ${
                  i === ativo ? "bg-accent-50 text-accent-800" : "text-ink-800"
                }`}
              >
                <span className="font-medium">{nome} <span className="text-ink-500">· {uf}</span></span>
                <span className="font-mono text-xs text-ink-400">{cod}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-2 text-center text-xs text-ink-500">
        Abre o boletim do município: mortalidade, contexto social, internações evitáveis e
        comparação com municípios semelhantes.
      </p>
    </div>
  );
}
