import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Login from './pages/Login';
import RoleLanding from './pages/RoleLanding';
import Profile from './pages/Profile';
import RequireAuth from './components/common/RequireAuth';

// Leave Pages (core, kept eager for a fast first paint)
import LeaveDashboard from './pages/leave/Dashboard';
import ApplyLeave from './pages/leave/ApplyLeave';
import MyApplications from './pages/leave/MyApplications';
import PendingApprovals from './pages/leave/PendingApprovals';
import TeamCalendar from './pages/leave/TeamCalendar';

// Phase 6 - Enterprise Leave Records pages
import MyLeaveHistory from './pages/leave/records/MyLeaveHistory';
import MyLeaveCalendar from './pages/leave/records/MyLeaveCalendar';
import TeamAttendance from './pages/leave/records/TeamAttendance';

// Phase 9 - Notifications
import NotificationsPage from './pages/NotificationsPage';

// Phase 2.5 - Auth / User Management
import FirstLoginPasswordChange from './pages/FirstLoginPasswordChange';
import Unauthorized from './pages/Unauthorized';

// L2: code-split the heavy/less-frequent route groups. recharts (reports +
// analytics), the admin consoles, and the TipTap-backed memo pages load on
// demand instead of bloating the initial bundle.
const WeeklyReport = lazy(() => import('./pages/leave/records/WeeklyReport'));
const MonthlyReport = lazy(() => import('./pages/leave/records/MonthlyReport'));

const EmployeeList = lazy(() => import('./pages/admin/leaves/EmployeeList'));
const EmployeeDetail = lazy(() => import('./pages/admin/leaves/EmployeeDetail'));
const PolicyManagement = lazy(() => import('./pages/admin/leaves/PolicyManagement'));
const HolidayManagement = lazy(() => import('./pages/admin/leaves/HolidayManagement'));
const DepartmentManagement = lazy(() => import('./pages/admin/leaves/DepartmentManagement'));
const LeaveTypeManagement = lazy(() => import('./pages/admin/leaves/LeaveTypeManagement'));
const BulkActions = lazy(() => import('./pages/admin/leaves/BulkActions'));
const AttendanceReports = lazy(() => import('./pages/attendance/AttendanceReports'));
const UserManagement = lazy(() => import('./pages/admin/users/UserManagement'));

const ReportsHub = lazy(() => import('./pages/reports/ReportsHub'));
const ReportBuilder = lazy(() => import('./pages/reports/ReportBuilder'));
const ReportHistory = lazy(() => import('./pages/reports/ReportHistory'));
const Analytics = lazy(() => import('./pages/admin/Analytics'));

const InventoryList = lazy(() => import('./pages/inventory/InventoryList'));
const InventoryItemDetail = lazy(() => import('./pages/inventory/InventoryItemDetail'));
const AssetAssignment = lazy(() => import('./pages/inventory/AssetAssignment'));
const MyAssignedAssets = lazy(() => import('./pages/inventory/MyAssignedAssets'));
const MyTakeOutRequests = lazy(() => import('./pages/inventory/MyTakeOutRequests'));
const TakeOutApprovals = lazy(() => import('./pages/inventory/TakeOutApprovals'));

const MemoList = lazy(() => import('./pages/memo/MemoList'));
const CreateMemo = lazy(() => import('./pages/memo/CreateMemo'));
const MyMemos = lazy(() => import('./pages/memo/MyMemos'));
const MemoDetail = lazy(() => import('./pages/memo/MemoDetail'));
const PendingMemoReviews = lazy(() => import('./pages/memo/PendingMemoReviews'));
const PendingMemoApprovals = lazy(() => import('./pages/memo/PendingMemoApprovals'));

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>Loading…</div>}>
      <Routes>
        <Route path="/login" element={<Login />} />
        {/* First-login password change: protected but standalone (no chrome). */}
        <Route path="/auth/first-login-change-password" element={<RequireAuth><FirstLoginPasswordChange /></RequireAuth>} />
        <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
          <Route index element={<RoleLanding />} />
          <Route path="unauthorized" element={<Unauthorized />} />
          <Route path="admin/users" element={<RequireAuth allowedRoles={['admin']}><UserManagement /></RequireAuth>} />
          <Route path="admin/attendance-reports" element={<RequireAuth allowedRoles={['approver', 'admin']}><AttendanceReports /></RequireAuth>} />
          <Route path="profile" element={<Profile />} />
          <Route path="leave" element={<LeaveDashboard />} />
          <Route path="leave/apply" element={<RequireAuth allowedRoles={['maker', 'checker', 'approver']}><ApplyLeave /></RequireAuth>} />
          <Route path="leave/my-applications" element={<MyApplications />} />
          <Route path="leave/pending" element={<PendingApprovals />} />
          <Route path="leave/calendar" element={<TeamCalendar />} />

          {/* Phase 6 - Enterprise Leave Records */}
          <Route path="leaves/my-history" element={<MyLeaveHistory />} />
          <Route path="leaves/my-calendar" element={<MyLeaveCalendar />} />
          <Route path="leaves/weekly-report" element={<WeeklyReport />} />
          <Route path="leaves/monthly-report" element={<MonthlyReport />} />
          <Route path="leaves/team-attendance" element={<TeamAttendance />} />

          {/* Phase 7 - HR/Admin */}
          <Route path="admin/leaves/employees" element={<EmployeeList />} />
          <Route path="admin/leaves/employees/:id" element={<EmployeeDetail />} />
          <Route path="admin/leaves/policies" element={<PolicyManagement />} />
          <Route path="admin/leaves/holidays" element={<HolidayManagement />} />
          <Route path="admin/leaves/departments" element={<DepartmentManagement />} />
          <Route path="admin/leaves/leave-types" element={<LeaveTypeManagement />} />
          <Route path="admin/leaves/bulk-actions" element={<BulkActions />} />

          {/* Phase 8 - Reports & Analytics */}
          <Route path="reports" element={<ReportsHub />} />
          <Route path="reports/build/:type" element={<ReportBuilder />} />
          <Route path="reports/history" element={<ReportHistory />} />
          <Route path="admin/analytics" element={<Analytics />} />

          {/* Phase 9 - Notifications */}
          <Route path="notifications" element={<NotificationsPage />} />

          {/* Inventory Management */}
          <Route path="inventory" element={<RequireAuth allowedRoles={['checker', 'approver', 'admin']}><InventoryList /></RequireAuth>} />
          <Route path="inventory/items/:id" element={<RequireAuth allowedRoles={['checker', 'approver', 'admin']}><InventoryItemDetail /></RequireAuth>} />
          <Route path="inventory/assignment" element={<RequireAuth allowedRoles={['checker', 'approver', 'admin']}><AssetAssignment /></RequireAuth>} />
          <Route path="inventory/my-assets" element={<MyAssignedAssets />} />
          <Route path="inventory/my-requests" element={<RequireAuth allowedRoles={['maker', 'checker', 'approver', 'admin']}><MyTakeOutRequests /></RequireAuth>} />
          <Route path="inventory/approvals" element={<RequireAuth allowedRoles={['checker', 'approver', 'admin']}><TakeOutApprovals /></RequireAuth>} />

          {/* Phase 3 - Memos (specific paths before /memos/:id) */}
          <Route path="memos" element={<MemoList />} />
          <Route path="memos/create" element={<CreateMemo />} />
          <Route path="memos/my" element={<MyMemos />} />
          <Route path="memos/pending-reviews" element={<RequireAuth allowedRoles={['checker', 'admin']}><PendingMemoReviews /></RequireAuth>} />
          <Route path="memos/pending-approvals" element={<RequireAuth allowedRoles={['approver', 'admin']}><PendingMemoApprovals /></RequireAuth>} />
          <Route path="memos/:id" element={<MemoDetail />} />
        </Route>
      </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
