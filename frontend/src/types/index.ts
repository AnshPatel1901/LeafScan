// ── Auth ──────────────────────────────────────────────────────────────────────

export interface UserProfile {
  id: string
  username: string
  created_at: string
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

// ── Prediction ────────────────────────────────────────────────────────────────

export interface PredictResponse {
  upload_id: string
  prediction_id: string
  is_plant: boolean
  plant_name: string | null
  disease_name: string | null
  confidence_score: number | null
  fallback_used: boolean
  precautions: string | null
  language: string
  audio_url: string | null
  rag_answer?: string | null
  rag_sources?: string[]
  rag_documents?: {
    source: string
    page?: number | null
    score?: number | null
    preview?: string | null
  }[]
}

// ── History ───────────────────────────────────────────────────────────────────

export interface HistoryItem {
  upload_id: string
  prediction_id: string | null
  image_url: string
  plant_name: string | null
  disease_name: string | null
  confidence_score: number | null
  is_plant: boolean
  fallback_used: boolean
  uploaded_at: string
  created_at: string | null
}

export interface HistoryResponse {
  items: HistoryItem[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

// ── AI Response ───────────────────────────────────────────────────────────────

export interface AIResponse {
  id: string
  prediction_id: string
  language: string
  precautions_text: string | null
  audio_url: string | null
  created_at: string
}

// ── API Envelope ──────────────────────────────────────────────────────────────

export interface APIResponse<T> {
  success: boolean
  data: T | null
  message: string
}

// ── Chatbot ───────────────────────────────────────────────────────────────────

export interface SourceCitation {
  source: string
  page: number | null
  preview: string | null
}

export interface ChatMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  sources: SourceCitation[] | null
  created_at: string
}

export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface ChatSessionDetail {
  id: string
  title: string
  created_at: string
  updated_at: string
  messages: ChatMessage[]
}

export interface SendMessageResponse {
  user_message: ChatMessage
  assistant_message: ChatMessage
  sources: SourceCitation[]
}

export interface ChatDocument {
  id: string
  name: string
  pages: number
  chunks: number
}

export interface ChatbotHealth {
  initialized: boolean
  documents_indexed: number
  vector_db_dir: string
  upload_dir: string
  embedding_model: string
  groq_model: string
  is_ready: boolean
}

// ── Language ──────────────────────────────────────────────────────────────────

export interface Language {
  code: string
  label: string
  native: string
}

export const SUPPORTED_LANGUAGES: Language[] = [
  { code: 'en', label: 'English',   native: 'English'  },
  { code: 'hi', label: 'Hindi',     native: 'हिंदी'     },
  { code: 'ta', label: 'Tamil',     native: 'தமிழ்'     },
  { code: 'te', label: 'Telugu',    native: 'తెలుగు'    },
  { code: 'mr', label: 'Marathi',   native: 'मराठी'     },
  { code: 'bn', label: 'Bengali',   native: 'বাংলা'     },
  { code: 'gu', label: 'Gujarati',  native: 'ગુજરાતી'  },
  { code: 'kn', label: 'Kannada',   native: 'ಕನ್ನಡ'     },
  { code: 'ml', label: 'Malayalam', native: 'മലയാളം'   },
  { code: 'pa', label: 'Punjabi',   native: 'ਪੰਜਾਬੀ'   },
  { code: 'fr', label: 'French',    native: 'Français' },
  { code: 'es', label: 'Spanish',   native: 'Español'  },
  { code: 'de', label: 'German',    native: 'Deutsch'  },
  { code: 'zh', label: 'Chinese',   native: '中文'      },
  { code: 'ar', label: 'Arabic',    native: 'العربية'  },
  { code: 'pt', label: 'Portuguese', native: 'Português' },
  { code: 'it', label: 'Italian',    native: 'Italiano'  },
  { code: 'ja', label: 'Japanese',   native: '日本語'      },
  { code: 'ko', label: 'Korean',     native: '한국어'      },
]
