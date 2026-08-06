import { useMemo } from "react";
import Plotly from "plotly.js-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";
import { Spinner } from "../ui/ui";

const Plot = createPlotlyComponent(Plotly);

const DARK = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { color: "#cbd5e1", family: "Inter, system-ui, sans-serif" },
  margin: { l: 56, r: 24, t: 44, b: 48 },
  autosize: true,
};

interface Props {
  data: unknown[];
  layout?: Record<string, unknown>;
  height?: number;
  title?: string;
  loading?: boolean;
}

export default function PlotlyChart({ data, layout, height = 380, title, loading }: Props) {
  const mergedLayout = useMemo(
    () => ({ ...DARK, ...(layout || {}), title: title ? { text: title, font: { size: 14, color: "#e2e8f0" } } : layout?.title }),
    [layout, title]
  ) as Record<string, unknown>;
  if (loading) return <Spinner />;
  return (
    <Plot
      data={data as any}
      layout={mergedLayout as any}
      config={{ responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] }}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}
