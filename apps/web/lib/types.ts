export type SessionStatus = "active" | "ended" | "cancelled" | "error";

export type CheckpointStatus =
  | "PENDING"
  | "APPROVED"
  | "REJECTED"
  | "CANCELLED"
  | "EXPIRED";

export type ClarificationStatus =
  | "PENDING"
  | "APPROVED"
  | "REJECTED"
  | "PROVIDED_INPUT"
  | "CANCELLED";

export type MultimodalDecision =
  | "PROCEED"
  | "REQUIRE_USER_CONFIRMATION"
  | "REQUIRE_SENSITIVE_CHECKPOINT"
  | "HALT_LOW_CONFIDENCE";

export interface SessionSummary {
  session_id: string;
  merchant: string;
  status: SessionStatus;
  created_at: string;
  owner_display_name?: string | null;
}

export interface UserProfile {
  user_id: string;
  email: string;
  display_name: string;
  preferred_locale?: string | null;
  created_at?: string | null;
}

export interface AuthSessionResponse {
  token: string;
  profile: UserProfile;
}

export interface AgentCommand {
  type: string;
  payload: Record<string, unknown>;
}

export interface AgentStepResponse {
  new_state: string;
  spoken_summary?: string | null;
  commands: AgentCommand[];
  debug_notes?: string | null;
}

export interface LiveSessionCreateResponse {
  session_id: string;
  websocket_path: string;
  locale?: string | null;
  created_at: string;
}

export interface SensitiveCheckpoint {
  checkpoint_id: string;
  kind: string;
  status: CheckpointStatus;
  reason: string;
  prompt_to_user: string;
  created_at?: string | null;
  resolved_at?: string | null;
  resolution_notes?: string | null;
}

export interface ClarificationRequest {
  clarification_id: string;
  kind: string;
  status: ClarificationStatus;
  reason: string;
  prompt_to_user: string;
  original_user_goal?: string | null;
  candidate_summary?: string | null;
  candidate_options?: Array<{
    label: string;
    title: string;
    price_text?: string | null;
    variant_text?: string | null;
    difference_summary?: string | null;
    candidate_url?: string | null;
  }>;
  expected_fields: string[];
  resume_state?: string | null;
  clarified_response?: string | null;
  resolution_notes?: string | null;
  created_at?: string | null;
  resolved_at?: string | null;
}

export interface SessionContextSnapshot {
  session_id: string;
  latest_intent?: Record<string, unknown> | null;
  latest_product_intent?: Record<string, unknown> | null;
  latest_page_understanding?: Record<string, unknown> | null;
  latest_verification?: Record<string, unknown> | null;
  latest_multimodal_assessment?: {
    decision: MultimodalDecision;
    confidence: number;
    confidence_band: string;
    needs_user_confirmation: boolean;
    needs_sensitive_checkpoint: boolean;
    should_halt_low_confidence: boolean;
    ambiguity_notes: string[];
    trust_notes: string[];
    review_notes: string[];
    reasoning_summary: string;
    recommended_next_step?: string | null;
    notes?: string | null;
  } | null;
  latest_sensitive_checkpoint?: SensitiveCheckpoint | null;
  latest_clarification_request?: ClarificationRequest | null;
  latest_low_confidence_status?: {
    active: boolean;
    reason?: string | null;
    confidence?: number | null;
    ambiguity_notes: string[];
    trust_notes: string[];
    review_notes: string[];
    recommended_next_step?: string | null;
  } | null;
  latest_recovery_status?: {
    active: boolean;
    recovery_kind?: string | null;
    reason?: string | null;
    last_attempt_summary?: string | null;
    last_updated_at?: string | null;
  } | null;
  latest_trust_assessment?: Record<string, unknown> | null;
  latest_review_assessment?: {
    conflict_level: string;
    review_summary_spoken: string;
    confidence: number;
    conflict_notes: string[];
    positive_signals: string[];
    negative_signals: string[];
    recurring_issues: string[];
    cited_snippets: string[];
  } | null;
  latest_final_purchase_confirmation?: {
    required: boolean;
    confirmed: boolean;
    prompt_to_user?: string | null;
    confirmation_phrase_expected?: string | null;
    notes?: string | null;
  } | null;
  latest_final_session_artifact?: {
    original_goal?: string | null;
    clarified_goal?: string | null;
    chosen_product?: string | null;
    chosen_variant?: string | null;
    quantity_text?: string | null;
    merchant?: string | null;
    trust_status?: string | null;
    warnings: string[];
    important_actions: Array<{
      state: string;
      summary: string;
      created_at?: string | null;
    }>;
    spoken_summary?: string | null;
    completed_at?: string | null;
  } | null;
  latest_final_self_diagnosis?: {
    ready_to_close: boolean;
    unresolved_items: string[];
    fallback_heavy_steps: string[];
    confidence_warnings: string[];
    summary: string;
  } | null;
  latest_cart_snapshot?: {
    cart_item_count?: number | null;
    checkout_ready?: boolean | null;
    currency_text?: string | null;
    notes?: string | null;
    items: Array<{
      item_id: string;
      title?: string | null;
      price_text?: string | null;
      quantity_text?: string | null;
      variant_text?: string | null;
      url?: string | null;
      merchant_item_ref?: string | null;
      notes?: string | null;
    }>;
  } | null;
  latest_interruption_marker?: {
    active: boolean;
    interrupted_at?: string | null;
    prior_state?: string | null;
    reason?: string | null;
    latest_user_utterance?: string | null;
    resume_summary?: string | null;
  } | null;
  latest_spoken_summary?: string | null;
  updated_at?: string | null;
}

export interface LiveGatewayEvent {
  event: string;
  data: Record<string, unknown>;
}

export interface RuntimeObservation {
  observed_url?: string | null;
  page_title?: string | null;
  detected_page_hints: string[];
  product_candidates: Record<string, unknown>[];
  primary_product?: Record<string, unknown> | null;
  cart_items?: Record<string, unknown>[];
  cart_item_count?: number | null;
  checkout_ready?: boolean | null;
  notes?: string | null;
}

export interface RuntimeScreenshot {
  image_base64?: string | null;
  mime_type: string;
  source: string;
  notes?: string | null;
}

export interface TranscriptItem {
  id: string;
  role: "user" | "assistant" | "system" | "warning";
  text: string;
  timestamp: string;
}
