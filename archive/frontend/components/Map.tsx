"use client";

import { useEffect, useRef, useMemo } from "react";
import DeckGL from "@deck.gl/react";
import { GeoJsonLayer, PickingInfo } from "@deck.gl/layers";
import { Map as MapLibre } from "react-map-gl/maplibre";
import type { Feature, FeatureCollection, Geometry } from "geojson";

const MAPLIBRE_STYLE =
  "https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json";

/** Brazil bounding box centred on BH */
const INITIAL_VIEW_STATE = {
  longitude: -51.9,
  latitude: -14.5,
  zoom: 3.8,
  pitch: 0,
  bearing: 0,
};

export interface ChoroplethProperties {
  /** Identifier used for matching (cod_municipio or uf) */
  id: string | number;
  /** Pre-computed normalised value in [0, 1] driving colour interpolation */
  value: number | null;
  /** Human-readable label shown in tooltip */
  label?: string;
}

interface MapProps {
  /** GeoJSON FeatureCollection with ChoroplethProperties on each feature */
  geojson: FeatureCollection<Geometry, ChoroplethProperties>;
  /** Colour ramp end colour in RGBA (default: SUS green #16a34a) */
  highColor?: [number, number, number];
  /** Colour ramp start colour in RGBA (default: near-white) */
  lowColor?: [number, number, number];
  /** Optional tooltip content function; receives the feature on hover */
  getTooltip?: (
    feature: Feature<Geometry, ChoroplethProperties>
  ) => string | null;
  /** Optional click handler */
  onClick?: (feature: Feature<Geometry, ChoroplethProperties>) => void;
  /** Map height in px (default 420) */
  height?: number;
  /** ID of the currently selected feature (highlighted with outline) */
  selectedId?: string | number | null;
}

/**
 * Linearly interpolates between two 3-channel colour arrays.
 * t ∈ [0, 1]
 */
function lerpColor(
  a: [number, number, number],
  b: [number, number, number],
  t: number
): [number, number, number, number] {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
    200,
  ];
}

export function ChoroplethMap({
  geojson,
  highColor = [22, 163, 74], // sus-600
  lowColor = [220, 252, 231], // sus-100
  getTooltip,
  onClick,
  height = 420,
  selectedId = null,
}: MapProps) {
  const layer = useMemo(
    () =>
      new GeoJsonLayer<ChoroplethProperties>({
        id: "choropleth",
        data: geojson,
        pickable: true,
        stroked: true,
        filled: true,
        getFillColor: (f) => {
          const v = f.properties?.value;
          if (v == null) return [229, 229, 229, 160]; // neutral grey for missing data
          return lerpColor(lowColor, highColor, Math.max(0, Math.min(1, v)));
        },
        getLineColor: (f) => {
          const isSelected =
            selectedId != null && f.properties?.id === selectedId;
          return isSelected ? [0, 0, 0, 255] : [255, 255, 255, 100];
        },
        getLineWidth: (f) => {
          const isSelected =
            selectedId != null && f.properties?.id === selectedId;
          return isSelected ? 2 : 0.5;
        },
        lineWidthUnits: "pixels",
        updateTriggers: {
          getFillColor: [geojson, lowColor, highColor],
          getLineColor: [selectedId],
          getLineWidth: [selectedId],
        },
        onClick: ({ object }: PickingInfo<Feature<Geometry, ChoroplethProperties>>) => {
          if (object && onClick) onClick(object);
        },
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [geojson, highColor, lowColor, selectedId, onClick]
  );

  const deckTooltip = useMemo(
    () =>
      getTooltip
        ? ({
            object,
          }: PickingInfo<Feature<Geometry, ChoroplethProperties>>) => {
            if (!object) return null;
            const content = getTooltip(object);
            if (!content) return null;
            return {
              html: `<div class="map-tooltip">${content}</div>`,
              style: {
                background: "hsl(var(--popover))",
                color: "hsl(var(--popover-foreground))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "6px",
                fontSize: "12px",
                padding: "6px 10px",
                pointerEvents: "none",
              },
            };
          }
        : undefined,
    [getTooltip]
  );

  return (
    <div style={{ height, position: "relative" }} className="rounded-lg overflow-hidden">
      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller
        layers={[layer]}
        getTooltip={deckTooltip}
      >
        <MapLibre
          mapStyle={MAPLIBRE_STYLE}
          attributionControl={false}
          reuseMaps
        />
      </DeckGL>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 bg-background/90 backdrop-blur-sm border rounded-md px-3 py-2 text-xs flex items-center gap-2 shadow-sm">
        <span className="text-muted-foreground">Baixo</span>
        <div
          className="h-3 w-20 rounded-sm"
          style={{
            background: `linear-gradient(to right, rgb(${lowColor.join(",")}), rgb(${highColor.join(",")}))`,
          }}
        />
        <span className="text-muted-foreground">Alto</span>
      </div>
    </div>
  );
}
