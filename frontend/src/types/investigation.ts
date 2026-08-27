export type AnalysisStatus = "pending" | "running" | "completed" | "failed";
export type AssistantMode = "disabled" | "mock" | "configured" | "unavailable";

export interface AssistantStatus {
  enabled: boolean;
  mode: AssistantMode;
  provider: string | null;
  provider_label: string;
  model: string | null;
  external: boolean;
  message: string;
}

export interface EvidenceReference {
  statement: string;
  evidence_refs: string[];
}

export interface InvestigationUncertainty extends EvidenceReference {
  reason: string;
}

export interface InvestigationAction {
  priority: "critical" | "high" | "medium" | "low";
  action: string;
  reason: string;
  evidence_refs: string[];
}

export interface InvestigationKeyAsset {
  asset_ref: string;
  reason: string;
}

export interface InvestigationOutput {
  executive_summary: string;
  observations: EvidenceReference[];
  correlation_explanation: EvidenceReference;
  key_assets: InvestigationKeyAsset[];
  uncertainties: InvestigationUncertainty[];
  recommended_actions: InvestigationAction[];
}

export interface InvestigationAnalysis {
  id: string;
  incident_id: string;
  status: AnalysisStatus;
  provider: string;
  provider_label: string;
  model: string;
  requested_at: string;
  started_at: string | null;
  completed_at: string | null;
  analysis_version: string;
  context_hash: string;
  is_stale: boolean;
  input_tokens: number | null;
  output_tokens: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  output: InvestigationOutput | null;
  evidence_catalog: Record<string, string>;
}

export interface InvestigationMessage {
  id: string;
  incident_id: string;
  analysis_id: string | null;
  reply_to_id: string | null;
  role: "user" | "assistant";
  content: string;
  evidence_refs: string[];
  context_hash: string;
  provider: string | null;
  model: string | null;
  created_at: string;
}

export interface InvestigationQuestionResponse {
  question: InvestigationMessage;
  answer: InvestigationMessage;
  evidence_catalog: Record<string, string>;
}
