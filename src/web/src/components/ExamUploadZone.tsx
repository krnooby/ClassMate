import React, { useState, useRef } from 'react';
import { Upload, FileText, X, Edit2, Check, AlertCircle, FolderOpen } from 'lucide-react';
import {
  parseFileName,
  groupFilesByExam,
  getFileTypeLabel,
  formatFileSize,
  type GroupedExamFiles
} from '../utils/fileNameParser';

interface ExamUploadZoneProps {
  onFilesReady: (exams: GroupedExamFiles[]) => void;
}

interface FileWithMeta {
  file: File;
  examId: string;
  fileType: 'question' | 'answer' | 'solution' | 'unknown';
  confidence: 'high' | 'medium' | 'low';
}

const ExamUploadZone: React.FC<ExamUploadZoneProps> = ({ onFilesReady }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<FileWithMeta[]>([]);
  const [editingExamId, setEditingExamId] = useState<string | null>(null);
  const [tempExamId, setTempExamId] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    processFiles(files);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      processFiles(files);
    }
  };

  const processFiles = (files: File[]) => {
    const newFilesWithMeta: FileWithMeta[] = files
      .filter(file => {
        const ext = file.name.toLowerCase();
        return ext.endsWith('.pdf') || ext.endsWith('.png') || ext.endsWith('.jpg') || ext.endsWith('.jpeg');
      })
      .map(file => {
        const parsed = parseFileName(file.name);
        return {
          file,
          examId: parsed.examId,
          fileType: parsed.fileType,
          confidence: parsed.confidence
        };
      });

    setUploadedFiles(prev => [...prev, ...newFilesWithMeta]);
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const startEditExamId = (currentExamId: string) => {
    setEditingExamId(currentExamId);
    setTempExamId(currentExamId);
  };

  const confirmEditExamId = () => {
    if (!editingExamId || !tempExamId.trim()) return;

    setUploadedFiles(prev =>
      prev.map(f =>
        f.examId === editingExamId
          ? { ...f, examId: tempExamId.trim() }
          : f
      )
    );

    setEditingExamId(null);
    setTempExamId('');
  };

  const cancelEditExamId = () => {
    setEditingExamId(null);
    setTempExamId('');
  };

  // 시험별로 그룹화
  const groupedExams = uploadedFiles.reduce((acc, fileMeta) => {
    const { examId } = fileMeta;
    if (!acc[examId]) {
      acc[examId] = [];
    }
    acc[examId].push(fileMeta);
    return acc;
  }, {} as Record<string, FileWithMeta[]>);

  const handleConfirm = () => {
    const grouped = groupFilesByExam(uploadedFiles.map(f => f.file));

    // examId 수정 사항 반영
    const updatedGrouped = grouped.map(group => {
      const firstFile = uploadedFiles.find(f =>
        f.file.name === group.question?.name ||
        f.file.name === group.answer?.name ||
        f.file.name === group.solution?.name
      );

      return {
        ...group,
        examId: firstFile?.examId || group.examId
      };
    });

    onFilesReady(updatedGrouped);
  };

  return (
    <div className="space-y-4">
      {/* 드래그 앤 드롭 영역 */}
      <div
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
        }`}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={handleFileSelect}
          className="hidden"
        />

        <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <p className="text-lg font-medium text-gray-700 mb-2">
          파일을 드래그하거나 클릭하여 업로드
        </p>
        <p className="text-sm text-gray-500">
          PDF, PNG, JPG 형식 지원 · 여러 파일 동시 업로드 가능
        </p>
        <p className="text-xs text-gray-400 mt-2">
          파일명 예시: 2026_09_mock_question.pdf, 중간고사_정답지.pdf
        </p>
      </div>

      {/* 업로드된 파일 목록 */}
      {Object.keys(groupedExams).length > 0 && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">
              업로드 파일 ({uploadedFiles.length}개)
            </h3>
            <button
              onClick={handleConfirm}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <Check className="w-4 h-4" />
              <span>확인 및 업로드</span>
            </button>
          </div>

          {Object.entries(groupedExams).map(([examId, files]) => (
            <div key={examId} className="bg-white border rounded-lg p-4">
              {/* 시험 ID 헤더 */}
              <div className="flex items-center justify-between mb-3 pb-2 border-b">
                {editingExamId === examId ? (
                  <div className="flex items-center gap-2 flex-1">
                    <FolderOpen className="w-5 h-5 text-blue-600" />
                    <input
                      type="text"
                      value={tempExamId}
                      onChange={(e) => setTempExamId(e.target.value)}
                      className="flex-1 px-2 py-1 border rounded focus:ring-2 focus:ring-blue-500"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') confirmEditExamId();
                        if (e.key === 'Escape') cancelEditExamId();
                      }}
                    />
                    <button
                      onClick={confirmEditExamId}
                      className="p-1 text-green-600 hover:bg-green-50 rounded"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                    <button
                      onClick={cancelEditExamId}
                      className="p-1 text-gray-600 hover:bg-gray-100 rounded"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2">
                      <FolderOpen className="w-5 h-5 text-blue-600" />
                      <span className="font-semibold text-gray-800">{examId}</span>
                      <span className="text-sm text-gray-500">
                        ({files.length}개 파일)
                      </span>
                    </div>
                    <button
                      onClick={() => startEditExamId(examId)}
                      className="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                  </>
                )}
              </div>

              {/* 파일 목록 */}
              <div className="space-y-2">
                {files.map((fileMeta, idx) => {
                  const globalIndex = uploadedFiles.findIndex(
                    f => f.file === fileMeta.file
                  );
                  const confidenceColor =
                    fileMeta.confidence === 'high'
                      ? 'bg-green-100 text-green-700'
                      : fileMeta.confidence === 'medium'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700';

                  return (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 bg-gray-50 rounded hover:bg-gray-100"
                    >
                      <div className="flex items-center gap-3 flex-1">
                        <FileText className="w-5 h-5 text-gray-500" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-800 truncate">
                            {fileMeta.file.name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {formatFileSize(fileMeta.file.size)}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                            {getFileTypeLabel(fileMeta.fileType)}
                          </span>
                          {fileMeta.fileType === 'unknown' && (
                            <span className="flex items-center gap-1 text-xs text-amber-600">
                              <AlertCircle className="w-3 h-3" />
                              수동 분류 필요
                            </span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => removeFile(globalIndex)}
                        className="ml-3 p-1 text-red-500 hover:bg-red-50 rounded"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {uploadedFiles.length === 0 && (
        <div className="text-center text-gray-500 py-8">
          <p className="text-sm">아직 업로드된 파일이 없습니다</p>
        </div>
      )}
    </div>
  );
};

export default ExamUploadZone;
