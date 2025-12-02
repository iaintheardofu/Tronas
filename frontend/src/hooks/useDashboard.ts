import { useQuery } from '@tanstack/react-query';
import { dashboardService } from '../services/dashboard';

export const useDashboardOverview = () => {
  return useQuery({
    queryKey: ['dashboard-overview'],
    queryFn: () => dashboardService.getOverview(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
};

export const useUrgentItems = () => {
  return useQuery({
    queryKey: ['urgent-items'],
    queryFn: () => dashboardService.getUrgentItems(),
    refetchInterval: 30000,
  });
};
