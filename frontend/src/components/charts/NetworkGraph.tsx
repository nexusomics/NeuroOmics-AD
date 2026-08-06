import { useEffect, useRef } from "react";
import * as d3 from "d3";

interface Node {
  id: string;
  hub?: boolean;
  module?: number;
}
interface Edge {
  source: string;
  target: string;
  weight?: number;
}

export default function NetworkGraph({ nodes, edges, height = 440 }: { nodes: Node[]; edges: Edge[]; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || !nodes.length) return;
    el.innerHTML = "";

    const width = el.clientWidth || 600;
    const svg = d3.select(el).append("svg").attr("width", width).attr("height", height);

    const color = d3.scaleOrdinal(d3.schemeTableau10);
    const sim = d3
      .forceSimulation(nodes as d3.SimulationNodeDatum[])
      .force("link", d3.forceLink(edges as d3.SimulationLinkDatum<d3.SimulationNodeDatum>[]).id((d: any) => d.id).distance(70))
      .force("charge", d3.forceManyBody().strength(-220))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide(18));

    const link = svg
      .append("g")
      .selectAll("line")
      .data(edges as d3.SimulationLinkDatum<d3.SimulationNodeDatum>[])
      .join("line")
      .attr("stroke", "#33445f")
      .attr("stroke-opacity", 0.5)
      .attr("stroke-width", (d: any) => Math.max(0.4, (d.weight || 0.5) * 2.2));

    const node = svg
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", (d) => (d.hub ? 9 : 5.5))
      .attr("fill", (d) => (d.hub ? "#e74c3c" : color(String(d.module ?? 0))))
      .attr("stroke", "#0f172a")
      .attr("stroke-width", 1.2)
      .style("cursor", "pointer");

    node.append("title").text((d) => `${d.id}${d.hub ? " (hub)" : ""}`);

    const label = svg
      .append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d) => d.id)
      .attr("x", (d) => (d.hub ? 12 : 8))
      .attr("y", 4)
      .attr("font-size", (d) => (d.hub ? 11 : 8.5))
      .attr("fill", (d) => (d.hub ? "#fda4af" : "#94a3b8"))
      .attr("font-family", "Inter, sans-serif");

    sim.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);
      node.attr("cx", (d: any) => d.x).attr("cy", (d: any) => d.y);
      label.attr("x", (d: any) => d.x + (d.hub ? 12 : 8)).attr("y", (d: any) => d.y + 4);
    });

    const zoom = d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.3, 3]).on("zoom", (ev) => {
      svg.select("g").attr("transform", ev.transform.toString());
    });
    svg.call(zoom as any);

    return () => {
      sim.stop();
    };
  }, [nodes, edges, height]);

  if (!nodes.length) return <div className="py-10 text-center text-sm text-slate-500">No network data</div>;
  return <div ref={ref} className="w-full" />;
}
