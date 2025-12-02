import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { requestsService, CreateRequestData } from '../services/requests';
import toast from 'react-hot-toast';

export const useRequests = (params?: {
  status?: string;
  priority?: string;
  page?: number;
  limit?: number;
}) => {
  return useQuery({
    queryKey: ['requests', params],
    queryFn: () => requestsService.getRequests(params),
  });
};

export const useRequest = (id: string) => {
  return useQuery({
    queryKey: ['requests', id],
    queryFn: () => requestsService.getRequest(id),
    enabled: !!id,
  });
};

export const useCreateRequest = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateRequestData) => requestsService.createRequest(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requests'] });
      toast.success('Request created successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create request');
    },
  });
};

export const useUpdateRequest = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      requestsService.updateRequest(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['requests'] });
      queryClient.invalidateQueries({ queryKey: ['requests', variables.id] });
      toast.success('Request updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update request');
    },
  });
};

export const useStartProcessing = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => requestsService.startProcessing(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['requests'] });
      queryClient.invalidateQueries({ queryKey: ['requests', id] });
      toast.success('Processing started successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to start processing');
    },
  });
};

export const useDeleteRequest = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => requestsService.deleteRequest(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requests'] });
      toast.success('Request deleted successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to delete request');
    },
  });
};
