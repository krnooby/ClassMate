/**
 * API Client
 * Axios 기반 HTTP 클라이언트
 */
import axios from 'axios';

// Vite proxy를 사용하므로 baseURL을 빈 문자열로 설정 (상대 경로 사용)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 5000, // 5초 (빠른 실패)
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // 추후 JWT 토큰 추가
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // 서버 응답이 있지만 에러인 경우
      console.error('API Error:', error.response.status, error.response.data);
    } else if (error.request) {
      // 요청이 전송되었지만 응답이 없는 경우
      console.error('Network Error:', error.message);
    } else {
      // 요청 설정 중 에러 발생
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);
