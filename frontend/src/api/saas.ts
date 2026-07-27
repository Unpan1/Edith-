import { api } from './client'
import type {
  AdminOverview,
  AnalyticsSnapshot,
  AutomationSettings,
  AutomationSettingsUpdate,
  CalendarMonth,
  ClipContent,
  ClipEditor,
  ClipEditorUpdate,
  CreditsBalance,
  DashboardStats,
  GrowthEnqueueResponse,
  GrowthPlanRequest,
  Job,
  LearningInsight,
  LibraryResponse,
  Plan,
  Project,
  ProjectCreate,
  RankingResponse,
  ScheduledPost,
  ScheduledPostCreate,
  SocialAccount,
  Thumbnail,
  TrendsResponse,
} from '../types/saas'

/* ── Dashboard ── */
export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>('/api/dashboard/stats')
  return data
}

/* ── Library ── */
export async function getLibrary(q?: string): Promise<LibraryResponse> {
  const { data } = await api.get<LibraryResponse>('/api/library', {
    params: q ? { q } : undefined,
  })
  return data
}

/* ── Content AI ── */
export async function getClipContent(clipId: number): Promise<ClipContent> {
  const { data } = await api.get<ClipContent>(`/api/content/clips/${clipId}`)
  return data
}

export async function generateClipContent(clipId: number): Promise<ClipContent> {
  const { data } = await api.post<ClipContent>('/api/content/generate', {
    clip_id: clipId,
  })
  return data
}

/* ── Thumbnails ── */
export async function listThumbnails(clipId: number): Promise<Thumbnail[]> {
  const { data } = await api.get<Thumbnail[]>(`/api/thumbnails/clips/${clipId}`)
  return data
}

export async function createThumbnail(
  clipId: number,
  opts?: { texto_overlay?: string; at_seconds?: number },
): Promise<Thumbnail> {
  const { data } = await api.post<Thumbnail>('/api/thumbnails', {
    clip_id: clipId,
    ...opts,
  })
  return data
}

/* ── Editor ── */
export async function getClipEditor(clipId: number): Promise<ClipEditor> {
  const { data } = await api.get<ClipEditor>(`/api/editor/clips/${clipId}`)
  return data
}

export async function updateClipEditor(
  clipId: number,
  body: ClipEditorUpdate,
): Promise<ClipEditor> {
  const { data } = await api.patch<ClipEditor>(`/api/editor/clips/${clipId}`, body)
  return data
}

/* ── Publishing ── */
export async function listPosts(status?: string): Promise<ScheduledPost[]> {
  const { data } = await api.get<ScheduledPost[]>('/api/publishing/posts', {
    params: status ? { status } : undefined,
  })
  return data
}

export async function createPost(body: ScheduledPostCreate): Promise<ScheduledPost> {
  const { data } = await api.post<ScheduledPost>('/api/publishing/posts', body)
  return data
}

export async function updatePost(
  postId: number,
  body: Partial<ScheduledPostCreate> & { status?: string },
): Promise<ScheduledPost> {
  const { data } = await api.patch<ScheduledPost>(
    `/api/publishing/posts/${postId}`,
    body,
  )
  return data
}

export async function deletePost(postId: number): Promise<void> {
  await api.delete(`/api/publishing/posts/${postId}`)
}

export async function listAccounts(): Promise<SocialAccount[]> {
  const { data } = await api.get<SocialAccount[]>('/api/publishing/accounts')
  return data
}

export async function connectAccount(
  platform: string,
  handle: string,
): Promise<SocialAccount> {
  const { data } = await api.post<SocialAccount>('/api/publishing/accounts/connect', {
    platform,
    handle,
  })
  return data
}

/* ── Calendar ── */
export async function getCalendarMonth(
  year: number,
  month: number,
): Promise<CalendarMonth> {
  const { data } = await api.get<CalendarMonth>('/api/calendar/month', {
    params: { year, month },
  })
  return data
}

/* ── Analytics ── */
export async function getAnalyticsRanking(limit = 10): Promise<RankingResponse> {
  const { data } = await api.get<RankingResponse>('/api/analytics/ranking', {
    params: { limit },
  })
  return data
}

export async function getAnalyticsSnapshots(
  limit = 50,
): Promise<AnalyticsSnapshot[]> {
  const { data } = await api.get<AnalyticsSnapshot[]>('/api/analytics/snapshots', {
    params: { limit },
  })
  return data
}

/* ── Learning ── */
export async function listInsights(): Promise<LearningInsight[]> {
  const { data } = await api.get<LearningInsight[]>('/api/learning/insights')
  return data
}

export async function generateInsights(): Promise<{ insights: LearningInsight[] }> {
  const { data } = await api.post<{ insights: LearningInsight[] }>(
    '/api/learning/generate',
  )
  return data
}

/* ── Automation ── */
export async function getAutomationSettings(): Promise<AutomationSettings> {
  const { data } = await api.get<AutomationSettings>('/api/automation/settings')
  return data
}

export async function updateAutomationSettings(
  body: AutomationSettingsUpdate,
): Promise<AutomationSettings> {
  const { data } = await api.patch<AutomationSettings>(
    '/api/automation/settings',
    body,
  )
  return data
}

/* ── Credits ── */
export async function getCreditsBalance(): Promise<CreditsBalance> {
  const { data } = await api.get<CreditsBalance>('/api/credits/balance')
  return data
}

export async function getCreditPlans(): Promise<Plan[]> {
  const { data } = await api.get<Plan[]>('/api/credits/plans')
  return data
}

/* ── Admin ── */
export async function getAdminOverview(): Promise<AdminOverview> {
  const { data } = await api.get<AdminOverview>('/api/admin/overview')
  return data
}

/* ── Trends ── */
export async function getTrends(params?: {
  category?: string
  country?: string
}): Promise<TrendsResponse> {
  const { data } = await api.get<TrendsResponse>('/api/trends', { params })
  return data
}

/* ── Jobs ── */
export async function listJobs(status?: string, limit = 50): Promise<Job[]> {
  const { data } = await api.get<Job[]>('/api/jobs', {
    params: { status, limit },
  })
  return data
}

export async function enqueueJob(
  tipo: string,
  payload: Record<string, unknown> = {},
): Promise<Job> {
  const { data } = await api.post<Job>('/api/jobs', { tipo, payload })
  return data
}

export async function getJob(jobId: number): Promise<Job> {
  const { data } = await api.get<Job>(`/api/jobs/${jobId}`)
  return data
}

/* ── Growth ── */
export async function runGrowthPlan(
  body: GrowthPlanRequest,
): Promise<GrowthEnqueueResponse> {
  const { data } = await api.post<GrowthEnqueueResponse>('/api/growth/plan', body)
  return data
}

/* ── Projects ── */
export async function listProjects(): Promise<Project[]> {
  const { data } = await api.get<Project[]>('/api/projects')
  return data
}

export async function createProject(body: ProjectCreate): Promise<Project> {
  const { data } = await api.post<Project>('/api/projects', body)
  return data
}

export async function getProject(id: number): Promise<Project> {
  const { data } = await api.get<Project>(`/api/projects/${id}`)
  return data
}

export async function updateProject(
  id: number,
  body: Partial<ProjectCreate>,
): Promise<Project> {
  const { data } = await api.patch<Project>(`/api/projects/${id}`, body)
  return data
}

export async function deleteProject(id: number): Promise<void> {
  await api.delete(`/api/projects/${id}`)
}
