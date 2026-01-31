export type AIScope =
  | "global"
  | `module:${string}`
  | `record:${string}:${string}`;

export interface AIChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface AIChatResponse {
  text: string;
  tool_calls?: Array<Record<string, unknown>>;
  usage_tokens?: number;
}
