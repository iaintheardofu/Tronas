import api from './api';

export interface Document {
  id: number;
  request_id: number;
  filename: string;
  original_path?: string;
  storage_path?: string;
  file_type?: string;
  mime_type?: string;
  file_size: number;
  page_count: number;
  classification: 'responsive' | 'non_responsive' | 'partially_responsive' | 'exempt' | 'unclassified';
  classification_confidence?: number;
  status: 'pending' | 'processing' | 'classified' | 'reviewed' | 'redacted' | 'approved' | 'released' | 'withheld';
  needs_redaction: boolean;
  is_duplicate: boolean;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

export const documentsService = {
  // Get all documents with optional filters
  getDocuments: async (params?: {
    request_id?: string;
    classification?: string;
    status?: string;
    page?: number;
    limit?: number;
  }) => {
    const response = await api.get('/documents', { params });
    return response.data;
  },

  // Get single document
  getDocument: async (id: string) => {
    const response = await api.get(`/documents/${id}`);
    return response.data;
  },

  // Upload document
  uploadDocument: async (formData: FormData) => {
    const response = await api.post('/documents', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Classify document
  classifyDocument: async (id: string) => {
    const response = await api.post(`/documents/${id}/classify`);
    return response.data;
  },

  // Update document metadata
  updateDocument: async (id: string, data: Partial<Document>) => {
    const response = await api.put(`/documents/${id}`, data);
    return response.data;
  },

  // Download document
  downloadDocument: async (id: string) => {
    const response = await api.get(`/documents/${id}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Delete document
  deleteDocument: async (id: string) => {
    const response = await api.delete(`/documents/${id}`);
    return response.data;
  },
};

export default documentsService;
