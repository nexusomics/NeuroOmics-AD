import PlotlyChart from "./PlotlyChart";
import type { Sankey } from "../../api/types";

export default function SankeyChart({ sankey, title = "Disease → Targets → Drugs" }: { sankey: Sankey; title?: string }) {
  if (!sankey?.nodes?.length || sankey.links.length === 0) {
    return <div className="py-8 text-center text-sm text-slate-500">No flow data</div>;
  }
  return (
    <PlotlyChart
      data={[
        {
          type: "sankey",
          node: { pad: 14, thickness: 18, line: { color: "#0f172a", width: 1 }, label: sankey.node_labels, color: "#14b8a6" },
          link: { source: sankey.links.map((l) => l.source), target: sankey.links.map((l) => l.target), value: sankey.links.map((l) => l.value), color: "rgba(20,184,166,0.25)" },
        },
      ]}
      layout={{ title, height: 480 }}
    />
  );
}
