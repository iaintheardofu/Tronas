import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workflowService } from '../services/workflow';
import toast from 'react-hot-toast';

export const useWorkflowTasks = (params?: {
  request_id?: string;
  status?: string;
  assigned_to?: string;
}) => {
  return useQuery({
    queryKey: ['workflow-tasks', params],
    queryFn: () => workflowService.getTasks(params),
  });
};

export const useWorkflowStatus = (requestId: string) => {
  return useQuery({
    queryKey: ['workflow-status', requestId],
    queryFn: () => workflowService.getWorkflowStatus(requestId),
    enabled: !!requestId,
  });
};

export const useUpdateTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      workflowService.updateTask(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-tasks'] });
      queryClient.invalidateQueries({ queryKey: ['workflow-status'] });
      toast.success('Task updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update task');
    },
  });
};

export const useCompleteTask = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => workflowService.completeTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-tasks'] });
      queryClient.invalidateQueries({ queryKey: ['workflow-status'] });
      toast.success('Task completed successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to complete task');
    },
  });
};
