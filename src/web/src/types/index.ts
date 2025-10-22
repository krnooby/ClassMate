/**
 * TypeScript Types
 * API 응답 및 데이터 모델 타입 정의
 */

// ==================== Student Types ====================

export interface Student {
  student_id: string;
  name: string;
  class_id?: string;
  grade_code?: string;
  grade_label?: string;
  updated_at?: string;
  summary?: string;

  // 출석
  total_sessions?: number;
  absent?: number;
  perception?: string;
  attendance_rate?: number;

  // 숙제
  homework_assigned?: number;
  homework_missed?: number;
  homework_completion_rate?: number;

  // 평가
  attitude?: string;
  school_exam_level?: string;
  csat_level?: string;
  cefr?: string;
  percentile_rank?: number;

  // 점수
  grammar_score?: number;
  vocabulary_score?: number;
  reading_score?: number;
  listening_score?: number;
  writing_score?: number;

  peer_distribution?: string;
}

export interface StudentListResponse {
  total: number;
  skip: number;
  limit: number;
  students: Student[];
}

export interface StudentStats {
  student_id: string;
  name: string;
  attendance_rate?: number;
  total_sessions?: number;
  absent?: number;
  homework_completion_rate?: number;
  homework_assigned?: number;
  homework_missed?: number;
  average_score?: number;
  grammar_score?: number;
  vocabulary_score?: number;
  reading_score?: number;
  listening_score?: number;
  writing_score?: number;
  cefr?: string;
  percentile_rank?: number;
}

// ==================== Problem Types ====================

export interface Table {
  table_id: string;
  problem_id?: string;
  title?: string;
  columns?: string[];
  rows_json?: string;
  storage_key?: string;
  public_url?: string;
}

export interface Figure {
  asset_id: string;
  problem_id?: string;
  asset_type?: string;
  storage_key?: string;
  public_url?: string;
  mime?: string;
  page?: number;
  labels?: string[];
  caption?: string;
}

export interface Problem {
  problem_id: string;
  item_no?: number;
  area?: string;
  mid_code?: string;
  grade_band?: string;
  cefr?: string;
  difficulty?: number;
  type?: string;
  stem?: string;
  options?: string[];
  answer?: string;
  rationale?: string;
  figure_ref?: string;
  table_ref?: string;
  audio_transcript?: string;
  tags?: string[];

  tables?: Table[];
  figures?: Figure[];
}

export interface ProblemListResponse {
  total: number;
  skip: number;
  limit: number;
  problems: Problem[];
}

// ==================== Search Types ====================

export interface SearchRequest {
  query: string;
  limit?: number;
}

export interface StudentSearchResult {
  student: Student;
  score: number;
}

export interface StudentSearchResponse {
  query: string;
  results: StudentSearchResult[];
}

export interface ProblemSearchResult {
  problem: Problem;
  score: number;
}

export interface ProblemSearchResponse {
  query: string;
  results: ProblemSearchResult[];
}

// ==================== Dashboard Types ====================

export interface AreaDistribution {
  area: string;
  count: number;
}

export interface DifficultyDistribution {
  difficulty: number;
  count: number;
}

export interface CEFRDistribution {
  cefr: string;
  count: number;
}

export interface ProblemStats {
  total: number;
  tables: number;
  figures: number;
  area_distribution: AreaDistribution[];
  difficulty_distribution: DifficultyDistribution[];
}

export interface StudentStatsOverview {
  total: number;
  cefr_distribution: CEFRDistribution[];
}

export interface DashboardOverview {
  problems: ProblemStats;
  students: StudentStatsOverview;
}

// ==================== Class Types ====================

export interface ClassInfo {
  class_id: string;
  class_name: string;
  teacher_id: string;
  schedule: string;
  class_start_time: string;
  class_end_time: string;
  class_cefr: string;
  progress: string;
  homework: string;
  monthly_test: string;
  updated_at: string;
}
