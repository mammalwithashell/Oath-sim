import type { SiteState, PlayerState } from "../types/game";
import SiteCard from "./SiteCard";

interface Props {
  sites: SiteState[];
  players: PlayerState[];
  highlightedSites: Set<number>;
  cardHighlights: Map<number, Set<number>>;
}

const REGIONS = ["CRADLE", "PROVINCES", "HINTERLAND"] as const;
const REGION_LABELS: Record<string, string> = {
  CRADLE: "Cradle",
  PROVINCES: "Provinces",
  HINTERLAND: "Hinterland",
};

export default function MapView({ sites, players, highlightedSites, cardHighlights }: Props) {
  return (
    <div className="space-y-4">
      {REGIONS.map((region) => {
        const regionSites = sites.filter((s) => s.region === region);
        if (regionSites.length === 0) return null;
        return (
          <div key={region}>
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              {REGION_LABELS[region]}
            </h3>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-2">
              {regionSites.map((site) => (
                <SiteCard
                  key={site.index}
                  site={site}
                  players={players}
                  isHighlighted={highlightedSites.has(site.index)}
                  highlightedSlots={cardHighlights.get(site.index) || null}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
