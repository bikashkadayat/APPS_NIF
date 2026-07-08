import { useQuery } from '@tanstack/react-query';
import { leaveRecordService } from '../services/leaveRecordService';

/**
 * React Query hooks for the enterprise leave records. Each returns the standard
 * { data, isLoading, isError, error, refetch } shape used by the record pages.
 */

export const useMyHistory = (year) =>
  useQuery({
    queryKey: ['leave-history', year],
    queryFn: () => leaveRecordService.getMyHistory(year),
  });

export const useMyBalances = (year) =>
  useQuery({
    queryKey: ['leave-balances', year],
    queryFn: () => leaveRecordService.getMyBalances(year),
  });

export const useCalendar = (startDate, endDate, userId) =>
  useQuery({
    queryKey: ['leave-calendar', startDate, endDate, userId ?? 'me'],
    queryFn: () => leaveRecordService.getCalendar(startDate, endDate, userId),
    enabled: Boolean(startDate && endDate),
  });

export const useWeeklySummaries = (year, userId) =>
  useQuery({
    queryKey: ['weekly-summaries', year, userId ?? 'me'],
    queryFn: () => leaveRecordService.getWeeklySummaries(year, userId),
  });

export const useMonthlySummaries = (year, userId) =>
  useQuery({
    queryKey: ['monthly-summaries', year, userId ?? 'me'],
    queryFn: () => leaveRecordService.getMonthlySummaries(year, userId),
  });

export const useLeaveTypes = () =>
  useQuery({
    queryKey: ['leave-types'],
    queryFn: () => leaveRecordService.getLeaveTypes(),
    staleTime: 5 * 60_000,
  });

export const useHolidays = (year) =>
  useQuery({
    queryKey: ['holidays', year],
    queryFn: () => leaveRecordService.getHolidays(year),
    staleTime: 5 * 60_000,
  });

export const useTeamAttendance = (dept, month) =>
  useQuery({
    queryKey: ['team-attendance', dept ?? 'all', month],
    queryFn: () => leaveRecordService.getTeamAttendance(dept, month),
    enabled: Boolean(month),
  });
