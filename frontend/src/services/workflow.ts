import api from './api';

export interface WorkflowTask {
  id: string;
  request_id: string;
  task_type: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  assigned_to?: string;
  priority: string;
  due_date?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  metadata?: Record<string, any>;
}

export interface WorkflowStatus {
  request_id: string;
  current_stage: string;
  progress_percentage: number;
  tasks_completed: number;
  tasks_total: number;
  estimated_completion?: string;
  stages: Array<{
    name: string;
    status: 'pending' | 'in_progress' | 'completed' | 'failed';
    completed_at?: string;
  }>;
}

export const workflowService = {
  // Get all tasks
  getTasks: async (params?: {
    request_id?: string;
    status?: string;
    assigned_to?: string;
  }) => {
    const response = await api.get('/workflow/tasks', { params });
    return response.data;
  },

  // Get workflow status for a request
  getWorkflowStatus: async (requestId: string) => {
    const response = await api.get('/workflow/status', {
      params: { request_id: requestId },
    });
    return response.data;
  },

  // Update task status
  updateTask: async (id: string, data: Partial<WorkflowTask>) => {
    const response = await api.put(`/workflow/tasks/${id}`, data);
    return response.data;
  },

  // Assign task
  assignTask: async (id: string, userId: string) => {
    const response = await api.post(`/workflow/tasks/${id}/assign`, {
      user_id: userId,
    });
    return response.data;
  },

  // Complete task
  completeTask: async (id: string) => {
    const response = await api.post(`/workflow/tasks/${id}/complete`);
    return response.data;
  },
};

export default workflowService;
