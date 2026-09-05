"use client";

import { useEffect, useState } from "react";
import { slugify } from "@/lib/metodologia-secoes";

/**
 * Índice das seções de uma página longa.
 *
 * POR QUE ELE EXISTE
 * ------------------
 * A visão hospitalar tem **28 mil pixels** de altura e cinco seções, e nenhuma
 * delas tinha endereço nem aparecia num sumário: quem chegava para ver a
 * projeção de demanda rolava a página inteira, e quem queria mandar a seção de
 * leitos para alguém mandava a página. O mesmo vale para a atenção primária.
 *
 * POR QUE ELE LÊ O DOM EM VEZ DE RECEBER UMA LISTA
 * -------------------------------------------------
 * Uma lista de seções passada por prop é uma segunda cópia dos títulos, e
 * copiar título é como a "Vigência por base" e a coluna de linhas do catálogo
 * envelheceram. Aqui o índice é o que a página TEM: se uma seção nasce, morre
 * ou muda de nome, ele acompanha sem que ninguém precise lembrar.
 *
 * A ÂNCORA IGNORA A PARTE VARIÁVEL DO TÍTULO
 * -------------------------------------------
 * Os títulos carregam o recorte — "Mortalidade hospitalar ajustada (HSMR) —
 * Brasil, 2024". Derivar o slug do título inteiro faria a âncora mudar quando o
 * visitante trocasse de UF ou de ano, quebrando o link que ele acabou de
 * copiar. O slug sai do trecho ANTES do travessão, que é a parte estável.
 */
export function IndiceDaPagina() {
  const [secoes, setSecoes] = useState<{ id: string; titulo: string }[]>([]);
  const [ativa, setAtiva] = useState<string>("");

  useEffect(() => {
    const h2 = [...document.querySelectorAll<HTMLHeadingElement>("h2")];
    const usados = new Set<string>();
    const achadas = h2.map((h) => {
      const texto = (h.textContent ?? "").trim();
      const estavel = texto.split("—")[0].trim() || texto;
      let id = h.id || slugify(estavel);
      let n = 2;
      while (usados.has(id)) id = `${slugify(estavel)}-${n++}`;
      usados.add(id);
      if (!h.id) h.id = id;
      h.style.scrollMarginTop = "5rem";
      return { id, titulo: estavel };
    });
    setSecoes(achadas.filter((s) => s.titulo.length > 2));

    // Marca a seção visível. `rootMargin` negativo no topo evita que a seção
    // seguinte "ganhe" assim que encosta na borda inferior da janela.
    const obs = new IntersectionObserver(
      (entradas) => {
        const visivel = entradas.filter((e) => e.isIntersecting)[0];
        if (visivel) setAtiva(visivel.target.id);
      },
      { rootMargin: "-80px 0px -70% 0px" },
    );
    h2.forEach((h) => obs.observe(h));
    return () => obs.disconnect();
  }, []);

  if (secoes.length < 3) return null; // índice de duas seções é ruído

  return (
    <nav
      aria-label="Seções desta página"
      className="sticky top-0 z-10 -mx-4 mb-6 border-b border-ink-200 bg-ink-50/95 px-4 py-2 backdrop-blur no-print sm:-mx-6 sm:px-6"
    >
      <ul className="flex gap-1 overflow-x-auto text-sm">
        {secoes.map((s) => (
          <li key={s.id}>
            <a
              href={`#${s.id}`}
              aria-current={ativa === s.id ? "true" : undefined}
              className={`inline-block whitespace-nowrap rounded-lg px-3 py-1.5 ${
                ativa === s.id
                  ? "bg-accent-700 font-medium text-white"
                  : "text-ink-600 hover:bg-ink-100 hover:text-ink-900"
              }`}
            >
              {s.titulo}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
