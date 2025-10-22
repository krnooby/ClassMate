/**
 * 파일명 파싱 유틸리티
 * 시험지 파일명에서 시험 ID와 파일 유형을 자동으로 추출합니다.
 */

export interface ParsedFileInfo {
  examId: string;
  fileType: 'question' | 'answer' | 'solution' | 'unknown';
  originalName: string;
  confidence: 'high' | 'medium' | 'low';
}

export interface GroupedExamFiles {
  examId: string;
  question: File | null;
  answer: File | null;
  solution: File | null;
  unknownFiles: File[];
}

/**
 * 파일명에서 시험 ID와 파일 유형을 파싱합니다.
 *
 * 지원하는 파일명 패턴:
 * - 2026_09_mock_question.pdf
 * - 2026_09_중간고사_문제지.pdf
 * - final_exam_answer.pdf
 * - 중간고사_해설.pdf
 *
 * @param fileName 파일명 (확장자 포함)
 * @returns 파싱된 정보
 */
export function parseFileName(fileName: string): ParsedFileInfo {
  // 확장자 제거
  const nameWithoutExt = fileName.replace(/\.(pdf|png|jpg|jpeg)$/i, '');

  // 파일 유형 키워드 매핑
  const typePatterns = {
    question: [
      '_문제지', '_문제', '_question', '_questions', '_q',
      '문제지', '문제', 'question', 'questions'
    ],
    answer: [
      '_정답지', '_정답', '_답지', '_answer', '_answers', '_ans', '_a',
      '정답지', '정답', '답지', 'answer', 'answers'
    ],
    solution: [
      '_해설지', '_해설', '_풀이', '_solution', '_solutions', '_sol', '_s',
      '해설지', '해설', '풀이', 'solution', 'solutions'
    ]
  };

  let fileType: ParsedFileInfo['fileType'] = 'unknown';
  let confidence: ParsedFileInfo['confidence'] = 'low';
  let examId = nameWithoutExt;

  // 각 유형별로 패턴 매칭
  for (const [type, patterns] of Object.entries(typePatterns)) {
    for (const pattern of patterns) {
      const lowerName = nameWithoutExt.toLowerCase();
      const lowerPattern = pattern.toLowerCase();

      // 패턴이 파일명에 포함되어 있는지 확인
      if (lowerName.includes(lowerPattern)) {
        fileType = type as 'question' | 'answer' | 'solution';

        // confidence 결정
        if (pattern.startsWith('_')) {
          // 언더스코어로 구분된 경우 (high confidence)
          confidence = 'high';
          const index = lowerName.lastIndexOf(lowerPattern);
          examId = nameWithoutExt.substring(0, index);
        } else {
          // 단순 포함 (medium confidence)
          confidence = 'medium';
          const index = lowerName.lastIndexOf(lowerPattern);
          examId = nameWithoutExt.substring(0, index);

          // 끝에 _ 가 있으면 제거
          examId = examId.replace(/_+$/, '');
        }

        break;
      }
    }

    if (fileType !== 'unknown') break;
  }

  // examId가 비어있으면 전체 파일명 사용
  if (!examId.trim()) {
    examId = nameWithoutExt;
    confidence = 'low';
  }

  // 앞뒤 공백/언더스코어 제거
  examId = examId.trim().replace(/^_+|_+$/g, '');

  return {
    examId,
    fileType,
    originalName: fileName,
    confidence
  };
}

/**
 * 여러 파일을 시험 ID별로 그룹화합니다.
 *
 * @param files 업로드할 파일 목록
 * @returns 시험 ID별로 그룹화된 파일 객체
 */
export function groupFilesByExam(files: File[]): GroupedExamFiles[] {
  const examGroups = new Map<string, GroupedExamFiles>();

  for (const file of files) {
    const parsed = parseFileName(file.name);
    const { examId, fileType } = parsed;

    // 기존 그룹이 없으면 생성
    if (!examGroups.has(examId)) {
      examGroups.set(examId, {
        examId,
        question: null,
        answer: null,
        solution: null,
        unknownFiles: []
      });
    }

    const group = examGroups.get(examId)!;

    // 파일 유형에 따라 분류
    if (fileType === 'question') {
      group.question = file;
    } else if (fileType === 'answer') {
      group.answer = file;
    } else if (fileType === 'solution') {
      group.solution = file;
    } else {
      group.unknownFiles.push(file);
    }
  }

  return Array.from(examGroups.values());
}

/**
 * 파일 유형의 한글 표시명을 반환합니다.
 */
export function getFileTypeLabel(fileType: string): string {
  const labels: Record<string, string> = {
    question: '문제지',
    answer: '정답지',
    solution: '해설지',
    unknown: '미분류'
  };
  return labels[fileType] || '알 수 없음';
}

/**
 * 파일 크기를 읽기 쉬운 형식으로 변환합니다.
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
