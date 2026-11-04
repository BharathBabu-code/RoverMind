import {
  HealthResponse,
  ConfigStatusResponse,
  ImageUploadResponse,
  FullAnalysisResponse,
  PathPlanResponse,
  MissionBriefing,
  ChatResponse,
  RouteComparisonResponse,
  RecomputePathRequest,
  RecomputePathResponse,
} from '../types/api';

const API_BASE = '/api';

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchConfig(): Promise<ConfigStatusResponse> {
  const res = await fetch(`${API_BASE}/config`);
  if (!res.ok) throw new Error(`Config fetch failed: ${res.statusText}`);
  return res.json();
}

export async function uploadRoverImage(file: File): Promise<ImageUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/images/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Failed to upload image.');
  }
  return res.json();
}

export async function loadSampleRoverImage(): Promise<ImageUploadResponse> {
  const res = await fetch(`${API_BASE}/images/load-sample`, {
    method: 'POST',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Failed to load sample image.');
  }
  return res.json();
}

export async function runFullAnalysis(
  imageId: string,
  options?: {
    concepts?: string[];
    gridDownsampleFactor?: number;
    terrainCosts?: Record<string, number | null>;
    start?: [number, number];
    goal?: [number, number];
    allowDiagonal?: boolean;
  }
): Promise<FullAnalysisResponse> {
  const payload = {
    image_id: imageId,
    concepts: options?.concepts || ['rock', 'sand', 'obstacle'],
    grid_downsample_factor: options?.gridDownsampleFactor ?? 24,
    terrain_costs: options?.terrainCosts,
    start: options?.start,
    goal: options?.goal,
    allow_diagonal: options?.allowDiagonal ?? true,
  };

  const res = await fetch(`${API_BASE}/analysis/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Analysis execution failed.');
  }
  return res.json();
}

export async function computeCustomPath(
  costGrid: (number | null)[][],
  start: [number, number],
  goal: [number, number],
  allowDiagonal: boolean = true
): Promise<PathPlanResponse> {
  const res = await fetch(`${API_BASE}/planning/find-path`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cost_grid: costGrid,
      start,
      goal,
      allow_diagonal: allowDiagonal,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Route calculation failed.');
  }
  return res.json();
}

export function getRawImageUrl(imageId: string): string {
  return `${API_BASE}/images/${imageId}/raw`;
}

export async function fetchMissionBriefing(
  imageId: string,
  forceDeterministic: boolean = false
): Promise<MissionBriefing> {
  const url = `${API_BASE}/mission/${imageId}/briefing?force_deterministic=${forceDeterministic}`;
  const res = await fetch(url);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Failed to fetch mission briefing.');
  }
  return res.json();
}

export async function sendChatMessage(
  imageId: string,
  message: string,
  conversationId?: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/mission/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_id: imageId,
      message,
      conversation_id: conversationId,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Chat query failed.');
  }
  return res.json();
}

export async function compareRoutes(
  imageId: string,
  alternativeCosts: Record<string, number | null>,
  allowDiagonal?: boolean
): Promise<RouteComparisonResponse> {
  const res = await fetch(`${API_BASE}/mission/compare-routes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_id: imageId,
      alternative_terrain_costs: alternativeCosts,
      allow_diagonal: allowDiagonal,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Route comparison failed.');
  }
  return res.json();
}

export async function recomputePath(
  request: RecomputePathRequest
): Promise<RecomputePathResponse> {
  const res = await fetch(`${API_BASE}/planning/recompute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Path recomputation failed.');
  }
  return res.json();
}

