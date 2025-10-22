/**
 * API Services
 * 백엔드 API 호출 함수들
 */
import { apiClient } from './client';
import type {
  DashboardOverview,
  StudentListResponse,
  Student,
  StudentStats,
  StudentSearchResponse,
  SearchRequest,
  ProblemListResponse,
  Problem,
  ProblemSearchResponse,
} from '../types';

// ==================== Dashboard ====================

export const dashboardApi = {
  getOverview: async (): Promise<DashboardOverview> => {
    const response = await apiClient.get<DashboardOverview>('/api/dashboard/overview');
    return response.data;
  },

  healthCheck: async () => {
    const response = await apiClient.get('/api/dashboard/health');
    return response.data;
  },
};

// ==================== Students ====================

export const studentsApi = {
  getList: async (params: {
    skip?: number;
    limit?: number;
    grade_code?: string;
    cefr?: string;
  }): Promise<StudentListResponse> => {
    const response = await apiClient.get<StudentListResponse>('/api/students', { params });
    return response.data;
  },

  getById: async (studentId: string): Promise<Student> => {
    const response = await apiClient.get<Student>(`/api/students/${studentId}`);
    return response.data;
  },

  getStats: async (studentId: string): Promise<StudentStats> => {
    const response = await apiClient.get<StudentStats>(`/api/students/${studentId}/stats`);
    return response.data;
  },

  search: async (request: SearchRequest): Promise<StudentSearchResponse> => {
    const response = await apiClient.post<StudentSearchResponse>('/api/students/search', request);
    return response.data;
  },
};

// ==================== Problems ====================

export const problemsApi = {
  getList: async (params: {
    skip?: number;
    limit?: number;
    area?: string;
    difficulty?: number;
    cefr?: string;
  }): Promise<ProblemListResponse> => {
    const response = await apiClient.get<ProblemListResponse>('/api/problems', { params });
    return response.data;
  },

  getById: async (problemId: string): Promise<Problem> => {
    const response = await apiClient.get<Problem>(`/api/problems/${problemId}`);
    return response.data;
  },

  search: async (request: SearchRequest): Promise<ProblemSearchResponse> => {
    const response = await apiClient.post<ProblemSearchResponse>('/api/problems/search', request);
    return response.data;
  },
};

// ==================== Classes ====================

import type { ClassInfo } from '../types';

export const classesApi = {
  getList: async (): Promise<ClassInfo[]> => {
    const response = await apiClient.get<ClassInfo[]>('/api/classes');
    return response.data;
  },

  getById: async (classId: string): Promise<ClassInfo> => {
    const response = await apiClient.get<ClassInfo>(`/api/classes/${classId}`);
    return response.data;
  },
};

// Export all APIs
export const api = {
  dashboard: dashboardApi,
  students: studentsApi,
  problems: problemsApi,
  classes: classesApi,
};
