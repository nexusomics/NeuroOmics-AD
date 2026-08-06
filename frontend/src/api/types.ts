/** Shared API types (mirrors backend Pydantic schemas). */

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "researcher" | "admin" | "reviewer";
  organization: string;
  is_active: boolean;
  is_verified: boolean;
  created_at?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  disease: string;
  species: string;
  owner_id: string;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface ProjectSummary {
  datasets: number;
  analyses: number;
  drug_candidates: number;
  analyses_by_type: Record<string, number>;
}

export interface Dataset {
  id: string;
  project_id: string;
  name: string;
  omics_type: string;
  platform: string;
  format: string;
  n_samples: number;
  n_features: number;
  metadata_json: Record<string, unknown>;
  status: string;
  created_at?: string;
}

export interface Analysis {
  id: string;
  project_id: string;
  name: string;
  analysis_type: string;
  config: Record<string, unknown>;
  status: string;
  progress: number;
  error_message: string;
  created_at?: string;
  finished_at?: string;
}

export interface Artifact {
  id: string;
  analysis_id: string;
  name: string;
  kind: string;
  format: string;
  file_path: string;
  size_bytes: number;
  metadata_json: Record<string, unknown>;
  created_at?: string;
}

export interface DrugCandidate {
  id?: string;
  drug_name: string;
  drugbank_id: string;
  mechanism: string;
  targets: string[];
  fda_status: string;
  indication: string;
  score_network: number;
  score_pathway_reversal: number;
  score_target_overlap: number;
  score_bbb: number;
  score_admet: number;
  score_clinical: number;
  composite_score: number;
  rank: number;
  evidence?: string[];
  details?: Record<string, unknown>;
}

export interface MLResult {
  key: string;
  algorithm: string;
  metrics: Record<string, number>;
  feature_importance: { feature: string; importance: number }[];
  artifact_path: string;
  top_prioritized_genes?: string[];
  note?: string;
}

export interface EnrichmentRow {
  pathway: string;
  description: string;
  pvalue: number;
  fdr: number;
  overlap_size: number;
  set_size: number;
  genes: string[];
}

export interface Sankey {
  nodes: string[];
  node_labels: string[];
  links: { source: number; target: number; value: number }[];
}
