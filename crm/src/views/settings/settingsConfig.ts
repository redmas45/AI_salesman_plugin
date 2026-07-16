export type SettingsFocus = 'all' | 'runtime' | 'provider' | 'crawler' | 'deployment' | 'secrets';

export const NUMERIC_SETTING_LABELS: Record<string, string> = {
  ACTION_AUTO_APPROVE_CONFIDENCE: 'Action auto-approve confidence',
  LLM_MAX_TOKENS: 'LLM max tokens',
  LLM_MAX_TOKENS_HARD_CAP: 'LLM hard token cap',
  AZURE_OPENAI_TIMEOUT_SECONDS: 'Azure request timeout seconds',
  RAG_TOP_K: 'RAG top K',
  RAG_TOP_N: 'RAG top N',
  TTS_CHUNK_CHARS: 'TTS chunk characters',
  TTS_MAX_INPUT_CHARS: 'TTS max input characters',
  CRAWL_MAX_PAGES: 'Crawler max pages',
  CRAWL_MAX_DEPTH: 'Crawler max depth',
  PORT: 'Hub port',
  STOREFRONT_PORT: 'Storefront port',
  BACKEND_PORT: 'Backend port',
  HTTPS_PORT: 'HTTPS port',
};

export const FLOAT_SETTING_RANGES: Record<string, [number, number]> = {
  ACTION_AUTO_APPROVE_CONFIDENCE: [0, 1],
  AZURE_OPENAI_TIMEOUT_SECONDS: [1, 300],
};

export const INTEGER_SETTING_RANGES: Record<string, [number, number]> = {
  RAG_TOP_K: [1, 100],
  RAG_TOP_N: [1, 100],
  TTS_CHUNK_CHARS: [300, 4000],
  TTS_MAX_INPUT_CHARS: [2000, 50000],
  CRAWL_MAX_PAGES: [1, 10000],
  CRAWL_MAX_DEPTH: [0, 20],
};

export const SETTING_GROUPS = [
  {
    title: 'Speech-to-text',
    keys: ['AZURE_OPENAI_STT_DEPLOYMENT', 'STT_LANGUAGE'],
  },
  {
    title: 'Text-to-speech',
    keys: [
      'AZURE_OPENAI_TTS_DEPLOYMENT',
      'AZURE_OPENAI_TTS_VOICE',
      'TTS_CHUNK_CHARS',
      'TTS_MAX_INPUT_CHARS',
    ],
  },
  {
    title: 'LLM',
    keys: [
      'LLM_MAX_TOKENS',
      'LLM_MAX_TOKENS_HARD_CAP',
    ],
  },
  {
    title: 'Azure OpenAI',
    keys: [
      'AZURE_OPENAI_API_KEY',
      'AZURE_OPENAI_BASE_URL',
      'AZURE_OPENAI_CHAT_DEPLOYMENT',
      'AZURE_OPENAI_REASONING_EFFORT',
      'AZURE_OPENAI_TIMEOUT_SECONDS',
    ],
  },
  {
    title: 'RAG',
    keys: ['EMBEDDING_MODEL', 'RAG_TOP_K', 'RAG_TOP_N'],
  },
  {
    title: 'Runtime automation',
    keys: ['ACTION_AUTO_APPROVE_CONFIDENCE'],
  },
  {
    title: 'Deployment',
    keys: [
      'HUB_PUBLIC_URL',
      'CLIENT_STORE_URL',
      'CURRENT_URL',
      'CURRENT_SITE_ID',
      'DEFAULT_SITE_ID',
      'AI_DEFAULT_SITE_ID',
      'DATABASE_URL',
      'PUBLIC_API_URL',
      'PUBLIC_STOREFRONT_ORIGIN',
      'PUBLIC_WIDGET_SCRIPT_URL',
      'PUBLIC_HTTPS_ORIGIN',
      'VOICE_ORB_API_URL',
      'DEPLOYMENT_MODE',
      'HOST',
      'PORT',
      'STOREFRONT_PORT',
      'BACKEND_PORT',
      'HTTPS_PORT',
      'HUB_TLS_CERT_FILE',
      'HUB_TLS_KEY_FILE',
      'CORS_ORIGINS',
    ],
  },
  {
    title: 'Crawler',
    keys: ['CRAWL_MAX_PAGES', 'CRAWL_MAX_DEPTH', 'CRAWL_ON_STARTUP', 'CRAWL_PERIODIC_ENABLED'],
  },
  {
    title: 'Client panel and CRM',
    keys: ['CRM_ADMIN_TOKEN', 'CLIENT_PANEL_DEFAULT_PASSWORD', 'CLIENT_PANEL_TOKEN_SECRET'],
  },
];
