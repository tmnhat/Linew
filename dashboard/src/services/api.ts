const API_BASE = '/dashboard/api';
const DEFAULT_TIMEOUT = 15000; // 15 seconds timeout

// Distribution Types
export interface DistributionSettings {
  telegram_channel_enabled: boolean;
  telegram_channel_id: string;
  facebook_enabled: boolean;
  facebook_paused: boolean;
  twitter_enabled: boolean;
  twitter_paused: boolean;
  newsletter_enabled: boolean;
  medium_enabled: boolean;
  viblo_enabled: boolean;
}

export interface ChannelStatus {
  facebook_paused: boolean;
  twitter_paused: boolean;
}

export interface DistributionStats {
  stats: Record<string, { total: number; success: number; failed: number; pending: number }>;
  period_days: number;
  today_distributed: number;
}

export interface DistributionLog {
  id: string;
  article_id: string;
  channel: string;
  status: 'success' | 'failed' | 'pending' | 'skipped';
  external_id?: string;
  external_url?: string;
  error?: string;
  created_at: string;
}

// Newsletter Types
export interface NewsletterSettings {
  frequency: 'daily' | 'weekly';
  send_time: string;
}

export interface NewsletterStats {
  total: number;
  active: number;
  inactive: number;
  by_category: Record<string, number>;
}

export interface NewsletterSubscriber {
  id: string;
  email: string;
  name?: string;
  is_active: boolean;
  categories: string[];
  frequency: string;
  subscribed_at: string;
  total_sent: number;
  total_opened: number;
}

// SEO Types
export interface SEOSettings {
  ga_measurement_id: string;
  site_url: string;
  site_name: string;
}

// Social Media Credentials
export interface SocialMediaCredentials {
  telegram_bot_token: string;
  facebook_page_id: string;
  facebook_page_access_token: string;
  twitter_api_key: string;
  twitter_api_secret: string;
  twitter_access_token: string;
  twitter_access_secret: string;
}

// SMTP Settings
export interface SMTPSettings {
  smtp_host: string;
  smtp_port: number;
  smtp_username: string;
  smtp_password: string;
  newsletter_from_name: string;
  newsletter_from_email: string;
}

// Connection Test Results
export interface ConnectionTestResult {
  success: boolean;
  error?: string;
  message?: string;
  bot_username?: string;
  channel_title?: string;
  page_name?: string;
  fan_count?: number;
  username?: string;
  name?: string;
  url?: string;
}

export interface Source {
  id: string;
  name: string;
  feed_url: string;
  site_url?: string;
  category_hint?: string;
  language: string;
  is_active: boolean;
  crawl_difficulty: string;
  requires_flaresolverr: boolean;
  last_fetched_at?: string;
  last_error?: string;
}

export interface Article {
  id: string;
  original_title: string;
  original_url: string;
  original_summary?: string;
  category?: string;
  category_confidence?: number;
  trend_score?: number;
  state: string;
  mode: string;
  priority: number;
  word_count?: number;
  wp_url?: string;
  created_at: string;
  updated_at: string;
  body_html?: string;
  meta_title?: string;
  meta_description?: string;
  tags?: string[];
}

export interface Stats {
  today: {
    collected: number;
    written: number;
    published: number;
    failed: number;
  };
  by_state: Record<string, number>;
  by_category: Record<string, number>;
  total: number;
}

export interface Settings {
  scheduler: {
    rss_interval_minutes: number;
    pipeline_interval_minutes: number;
  };
  pipeline: {
    auto_publish: boolean;
    trend_scoring_enabled: boolean;
    governance_enabled: boolean;
    default_mode: string;
    active_categories: string[];
    signal_expiry_hours: number;
    trending_only_mode: boolean;
    min_trend_score: number;
    topic_cooldown_hours: number;
    max_articles_per_topic_per_cooldown: number;
  };
  ai: {
    gateway_url: string;
    api_key: string;
    writer_model: string;
    researcher_model: string;
    light_model: string;
    summarizer_model: string;
  };
  wordpress: {
    site_url: string;
    username: string;
    app_password: string;
  };
  prediction: {
    symbols: Array<{ symbol: string; name: string; type: string }>;
    horizon_days: number;
    update_frequency: string;
  };
  cleanup: {
    expired_days: number;
    skipped_days: number;
    price_history_years: number;
    predictions_days: number;
    publish_logs_days: number;
  };
  storage: {
    raw_signals_retention_days: number;
    articles_retention_days: number;
    predictions_retention_days: number;
    price_history_retention_days: number;
    publish_logs_retention_days: number;
    archive_base_dir: string;
    backup_base_dir: string;
  };
  distribution: DistributionSettings;
  newsletter: NewsletterSettings;
  seo: SEOSettings;
  social: SocialMediaCredentials;
  smtp: SMTPSettings;
}

// AI Test types
export interface AITestResult {
  success: boolean;
  message: string;
  status_code?: number;
}

export interface LoginResult {
  success: boolean;
  message: string;
  expires_in?: number;
}

async function fetchApi(endpoint: string, options: RequestInit = {}, timeout = DEFAULT_TIMEOUT) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Yêu cầu hết thời gian chờ (timeout). Vui lòng thử lại.');
    }
    throw error;
  }
}

// Sources API
export const sourcesApi = {
  list: () => fetchApi('/sources'),
  get: (id: string) => fetchApi(`/sources/${id}`),
  create: (data: Partial<Source>) => fetchApi('/sources', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Source>) => fetchApi(`/sources/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string) => fetchApi(`/sources/${id}`, { method: 'DELETE' }),
  fetch: (sourceId?: string) => fetchApi(`/sources/fetch${sourceId ? `?source_id=${sourceId}` : ''}`, { method: 'POST' }),
  test: (feedUrl: string) => fetchApi('/sources/test', { method: 'POST', body: JSON.stringify({ feed_url: feedUrl }) }),
  discover: (siteUrl: string) => fetchApi('/sources/discover', { method: 'POST', body: JSON.stringify({ site_url: siteUrl }) }),

  // Reset Signals API
  resetSignals: (params?: {
    unprocess_raw_signals?: boolean;
    reset_articles_to_signal_collected?: boolean;
    delete_duplicates?: boolean;
    categories?: string[];
  }) => fetchApi('/sources/reset', {
    method: 'POST',
    body: JSON.stringify(params || {
      unprocess_raw_signals: true,
      reset_articles_to_signal_collected: true,
      delete_duplicates: false,
    }),
  }),
  boostCategory: (categories: string[], limit?: number) =>
    fetchApi('/sources/reset/by-category', {
      method: 'POST',
      body: JSON.stringify({ categories, limit: limit || 50 }),
    }),
};

// Articles API
export const articlesApi = {
  list: (params: { state?: string; category?: string; page?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params.state) query.set('state', params.state);
    if (params.category) query.set('category', params.category);
    if (params.page) query.set('page', String(params.page));
    if (params.limit) query.set('limit', String(params.limit));
    return fetchApi(`/articles?${query}`);
  },
  get: (id: string) => fetchApi(`/articles/${id}`),
  approve: (id: string) => fetchApi(`/articles/${id}/approve`, { method: 'POST' }),
  reject: (id: string, reason: string) => fetchApi(`/articles/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }) }),
  unpublish: (id: string) => fetchApi(`/articles/${id}/unpublish`, { method: 'POST' }),
  republish: (id: string) => fetchApi(`/articles/${id}/republish`, { method: 'POST' }),
};

// Pipeline API
export const pipelineApi = {
  run: (params?: { category?: string; limit?: number }) => {
    return fetchApi('/pipeline/run', { 
      method: 'POST',
      body: JSON.stringify(params || {}),
    });
  },
  runAllin: (params?: { category?: string; limit?: number }) => {
    return fetchApi('/pipeline/allin', { 
      method: 'POST',
      body: JSON.stringify(params || {}),
    });
  },
  status: () => fetchApi('/pipeline/status'),
  retry: (articleId: string) => fetchApi(`/pipeline/retry/${articleId}`, { method: 'POST' }),
  cleanup: () => fetchApi('/pipeline/cleanup', { method: 'POST' }),
  cleanupFailed: (olderThanDays?: number) => 
    fetchApi(`/pipeline/cleanup/failed${olderThanDays !== undefined ? `?older_than_days=${olderThanDays}` : ''}`, { method: 'POST' }),
  
  // Pipeline Control API
  start: (params?: { mode?: string; limit?: number }) => {
    return fetchApi('/pipeline/start', { 
      method: 'POST',
      body: JSON.stringify(params || { mode: 'normal', limit: 10 }),
    });
  },
  stop: () => fetchApi('/pipeline/stop', { method: 'POST' }),
  info: () => fetchApi('/pipeline/info'),
  
  // Continuous mode
  startContinuous: (params?: { limit?: number }) => {
    return fetchApi('/pipeline/continuous/start', { 
      method: 'POST',
      body: JSON.stringify(params || { limit: 10 }),
    });
  },
  stopContinuous: () => fetchApi('/pipeline/continuous/stop', { method: 'POST' }),
  continuousStatus: () => fetchApi('/pipeline/continuous/status'),
};

// Stats API
export const statsApi = {
  get: () => fetchApi('/stats'),
};

// Settings API
export const settingsApi = {
  get: () => fetchApi('/settings'),
  update: (data: Partial<Settings>) => fetchApi('/settings', { method: 'PUT', body: JSON.stringify(data) }),
  testAI: (gatewayUrl: string, apiKey: string, model: string) =>
    fetchApi('/settings/test-ai', {
      method: 'POST',
      body: JSON.stringify({ gateway_url: gatewayUrl, api_key: apiKey, model }),
    }),
};

// Health API
export const healthApi = {
  get: () => fetchApi('/health'),
  getCircuitBreaker: () => fetchApi('/health/circuit-breaker'),
  resetCircuitBreaker: () => fetchApi('/health/circuit-breaker/reset', { method: 'POST' }),
};

// Prediction API
export const predictionApi = {
  getSymbols: () => fetchApi('/prediction/symbols'),
  get: (symbol: string) => fetchApi(`/prediction/${encodeURIComponent(symbol)}`),
  refresh: (symbol: string) => fetchApi(`/prediction/${encodeURIComponent(symbol)}/refresh`, { method: 'POST' }),
  refreshAll: () => fetchApi('/prediction/refresh-all', { method: 'POST' }),
};

// Distribution API
export const distributionApi = {
  getStats: (days?: number) => fetchApi(`/distribution/stats${days ? `?days=${days}` : ''}`),
  getLogs: (params?: { article_id?: string; channel?: string; status?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.article_id) query.set('article_id', params.article_id);
    if (params?.channel) query.set('channel', params.channel);
    if (params?.status) query.set('status', params.status);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    return fetchApi(`/distribution/logs?${query}`);
  },
  trigger: (articleId: string) => fetchApi(`/distribution/trigger/${articleId}`, { method: 'POST' }),
  testTelegram: () => fetchApi('/distribution/test/telegram'),
  testFacebook: () => fetchApi('/distribution/test/facebook'),
  testTwitter: () => fetchApi('/distribution/test/twitter'),
  testNewsletter: () => fetchApi('/distribution/test/newsletter'),
  pauseChannel: (channel: 'facebook' | 'twitter') => fetchApi(`/distribution/pause/${channel}`, { method: 'POST' }),
  resumeChannel: (channel: 'facebook' | 'twitter') => fetchApi(`/distribution/resume/${channel}`, { method: 'POST' }),
  getChannelStatus: () => fetchApi('/distribution/channel-status'),
};

// Newsletter API
export const newsletterApi = {
  getStats: () => fetchApi('/newsletter/stats'),
  getSubscribers: (params?: { limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    return fetchApi(`/newsletter/subscribers?${query}`);
  },
  subscribe: (email: string, name?: string, categories?: string[], frequency?: string) =>
    fetchApi('/newsletter/subscribe', {
      method: 'POST',
      body: JSON.stringify({ email, name, categories, frequency }),
    }),
  unsubscribe: (email: string) =>
    fetchApi('/newsletter/unsubscribe', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
};

// Worker Tier Types
export interface WorkerTierConfig {
  tier: string;
  workers: number;
  rate_limits: {
    research: string;
    write: string;
    govern: string;
    publish: string;
    categorize: string;
    score: string;
  };
  estimated_throughput: number;
  message: string;
}

export interface WorkerTiersInfo {
  current_tier: string;
  tiers: Record<string, Omit<WorkerTierConfig, 'tier' | 'message'>>;
}

export interface WorkerRestartResponse {
  success: boolean;
  message: string;
  workers_restarted: number;
}

// Worker Tier API
export const workerTierApi = {
  getCurrent: () => fetchApi('/pipeline/config/worker-tier'),
  getAll: () => fetchApi('/pipeline/config/worker-tiers'),
  setTier: (tier: string) =>
    fetchApi('/pipeline/config/worker-tier', {
      method: 'POST',
      body: JSON.stringify({ tier }),
    }),
  restartWorkers: () =>
    fetchApi('/pipeline/config/worker-tier/restart', {
      method: 'POST',
    }),
};

// SEO Types
export interface SEOLinkStats {
  total_articles: number;
  articles_with_internal_links: number;
  coverage_percent: number;
}

export interface SEOConnectionStatus {
  google: {
    status: string;
    message?: string;
    site_url?: string;
  };
  bing: {
    status: string;
    message?: string;
    api_key_prefix?: string;
  };
  overall: string;
}

export interface SEOLinkResult {
  article_id: string;
  links_added: number;
  success: boolean;
  error?: string;
}

// SEO API
export const seoApi = {
  // Connection test
  testConnections: () => fetchApi('/seo/test-connections'),

  // Health check
  health: () => fetchApi('/seo/health'),

  // Ping URL to search engines
  pingUrl: (url: string, action: 'publish' | 'update' | 'delete' = 'publish') =>
    fetchApi('/seo/ping', {
      method: 'POST',
      body: JSON.stringify({ url, action }),
    }),

  // Batch ping
  pingBatch: (urls: string[]) =>
    fetchApi('/seo/ping-batch', {
      method: 'POST',
      body: JSON.stringify({ urls, action: 'publish' }),
    }),

  // Index single URL
  indexUrl: (url: string) =>
    fetchApi(`/seo/index-url?url=${encodeURIComponent(url)}&action=publish`, {
      method: 'POST',
    }),

  // Remove from index
  deleteUrl: (url: string) =>
    fetchApi('/seo/delete-url', {
      method: 'POST',
      body: JSON.stringify({ url }),
    }),

  // Internal linking stats
  getLinkStats: () => fetchApi('/seo/link-stats'),

  // Refresh internal links
  refreshLinks: () =>
    fetchApi('/seo/link-refresh', { method: 'POST' }),

  // Link single article
  linkArticle: (articleId: string) =>
    fetchApi(`/seo/link-article/${articleId}`, { method: 'POST' }),
};

// Auth API
export const authApi = {
  login: (username: string, password: string): Promise<LoginResult> =>
    fetchApi('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  logout: (): Promise<{ success: boolean; message: string }> =>
    fetchApi('/auth/logout', { method: 'POST' }),

  verify: async (): Promise<boolean> => {
    try {
      const result = await fetchApi('/auth/verify');
      return result.valid === true;
    } catch {
      return false;
    }
  },

  checkStatus: async (): Promise<{ configured: boolean; message: string }> =>
    fetchApi('/auth/status'),
};
