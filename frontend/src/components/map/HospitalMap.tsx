"use client";

import { useMemo, useState } from "react";
import { useTheme } from "next-themes";
import Map, { Marker, Popup, Source, Layer, NavigationControl } from "react-map-gl/maplibre";
import type { StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { HospitalRead } from "@/lib/types";
import { cn, formatPercent } from "@/lib/utils";

export interface TransferArc {
  id: string;
  source: HospitalRead;
  destination: HospitalRead;
  /** Arc color — callers pass their own semantic color (e.g. AI-recommended
   * vs manual), keeping this component agnostic of that distinction. */
  color?: string;
}

interface HospitalMapProps {
  hospitals: HospitalRead[];
  selectedHospitalId?: string | null;
  onSelectHospital?: (hospitalId: string) => void;
  /** Per-hospital marker color override (e.g. surplus/deficit on the
   * Optimization page) — defaults to the primary brand color. */
  getMarkerColor?: (hospital: HospitalRead) => string;
  arcs?: TransferArc[];
  className?: string;
}

// Free, keyless raster tiles (CARTO basemaps) — chosen over Mapbox GL JS
// specifically to avoid a second external API-key dependency, per the
// Milestone D plan's map-provider decision (see docs/architecture.md).
function rasterStyle(url: string): StyleSpecification {
  return {
    version: 8,
    sources: {
      basemap: {
        type: "raster",
        tiles: [url],
        tileSize: 256,
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions">CARTO</a>',
      },
    },
    layers: [{ id: "basemap", type: "raster", source: "basemap" }],
  };
}

const LIGHT_STYLE = rasterStyle("https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png");
const DARK_STYLE = rasterStyle("https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png");

function boundsFor(hospitals: HospitalRead[]): { longitude: number; latitude: number; zoom: number } {
  if (hospitals.length === 0) return { longitude: 0, latitude: 20, zoom: 1 };
  const lats = hospitals.map((h) => h.latitude);
  const lons = hospitals.map((h) => h.longitude);
  const centerLat = (Math.min(...lats) + Math.max(...lats)) / 2;
  const centerLon = (Math.min(...lons) + Math.max(...lons)) / 2;
  const spread = Math.max(Math.max(...lats) - Math.min(...lats), Math.max(...lons) - Math.min(...lons));
  const zoom = spread < 0.5 ? 8 : spread < 2 ? 6 : spread < 8 ? 4 : 2;
  return { longitude: centerLon, latitude: centerLat, zoom };
}

export function HospitalMap({
  hospitals,
  selectedHospitalId,
  onSelectHospital,
  getMarkerColor,
  arcs = [],
  className,
}: HospitalMapProps) {
  const { resolvedTheme } = useTheme();
  const [popupHospitalId, setPopupHospitalId] = useState<string | null>(null);
  const initialView = useMemo(() => boundsFor(hospitals), [hospitals]);

  const arcGeoJson = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: arcs.map((arc) => ({
        type: "Feature" as const,
        properties: { color: arc.color ?? "hsl(213 68% 50%)" },
        geometry: {
          type: "LineString" as const,
          coordinates: [
            [arc.source.longitude, arc.source.latitude],
            [arc.destination.longitude, arc.destination.latitude],
          ],
        },
      })),
    }),
    [arcs]
  );

  const popupHospital = hospitals.find((h) => h.id === popupHospitalId);

  return (
    <div className={cn("overflow-hidden rounded-lg border border-border", className)}>
      <Map
        initialViewState={initialView}
        mapStyle={resolvedTheme === "dark" ? DARK_STYLE : LIGHT_STYLE}
        style={{ width: "100%", height: "100%" }}
      >
        <NavigationControl position="top-right" showCompass={false} />

        {arcs.length > 0 && (
          <Source id="transfer-arcs" type="geojson" data={arcGeoJson}>
            <Layer
              id="transfer-arcs-line"
              type="line"
              paint={{
                "line-color": ["get", "color"],
                "line-width": 2,
                "line-dasharray": [2, 1.5],
              }}
            />
          </Source>
        )}

        {hospitals.map((hospital) => {
          const isSelected = hospital.id === selectedHospitalId;
          const color = getMarkerColor?.(hospital) ?? "hsl(213 68% 50%)";
          return (
            <Marker
              key={hospital.id}
              longitude={hospital.longitude}
              latitude={hospital.latitude}
              onClick={(event) => {
                event.originalEvent.stopPropagation();
                setPopupHospitalId(hospital.id);
                onSelectHospital?.(hospital.id);
              }}
            >
              <button
                type="button"
                aria-label={hospital.name}
                className={cn(
                  "h-3.5 w-3.5 rounded-full border-2 border-white shadow-md transition-transform hover:scale-125",
                  isSelected && "scale-150 ring-2 ring-offset-1"
                )}
                style={{ backgroundColor: color }}
              />
            </Marker>
          );
        })}

        {popupHospital && (
          <Popup
            longitude={popupHospital.longitude}
            latitude={popupHospital.latitude}
            onClose={() => setPopupHospitalId(null)}
            closeOnClick={false}
            offset={12}
            className="text-foreground"
          >
            <div className="text-xs">
              <p className="font-medium">{popupHospital.name}</p>
              <p className="text-muted-foreground">
                {popupHospital.city}, {popupHospital.region}
              </p>
              <p className="mt-1">
                Occupancy: <span className="font-medium">{formatPercent(popupHospital.occupancy_rate)}</span>
              </p>
            </div>
          </Popup>
        )}
      </Map>
    </div>
  );
}
