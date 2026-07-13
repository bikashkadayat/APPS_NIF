// Business-facing role labels. Internal values stay maker/checker/approver/admin
// (the workflow engine + backend are unchanged); the UI shows clear names.
export const ROLES = ['maker', 'checker', 'approver', 'admin'];

export const ROLE_LABELS = {
  maker: 'Employee',
  checker: 'Department Head',
  approver: 'HR',
  admin: 'Admin',
};

export const roleLabel = (r) => ROLE_LABELS[r] || r || '—';

// Org-hierarchy label, independent of the permission role.
export const EMPLOYEE_TYPES = [
  { value: 'employee', label: 'Employee' },
  { value: 'supervisor', label: 'Supervisor' },
  { value: 'manager', label: 'Manager' },
  { value: 'department_head', label: 'Department Head' },
  { value: 'hr_officer', label: 'HR Officer' },
  { value: 'system_admin', label: 'System Admin' },
];

export const employeeTypeLabel = (t) =>
  EMPLOYEE_TYPES.find((x) => x.value === t)?.label || t || '—';

// Contract basis that drives the leave-category engine (distinct from role and
// from employee_type / org rank). Matches users.User.EmploymentType.
export const EMPLOYMENT_TYPES = [
  { value: 'permanent', label: 'Permanent' },
  { value: 'post_probation', label: 'Post-Probation' },
  { value: 'probation', label: 'Probation' },
  { value: 'intern', label: 'Intern' },
  { value: 'volunteer', label: 'Volunteer' },
];

export const employmentTypeLabel = (t) =>
  EMPLOYMENT_TYPES.find((x) => x.value === t)?.label || t || '—';

export const GENDERS = [
  { value: 'undisclosed', label: 'Prefer not to say' },
  { value: 'female', label: 'Female' },
  { value: 'male', label: 'Male' },
];

// ---------------------------------------------------------------------------
// Central role→capability config (drives sidebar + dashboard). Admin is an
// oversight/management role and has NO personal self-service actions.
// ---------------------------------------------------------------------------
const NON_ADMIN = ['maker', 'checker', 'approver']; // Employee, Dept Head, HR

export const PERMISSIONS = {
  applyLeave: NON_ADMIN,       // Employee, Dept Head, HR (NOT Admin)
  createMemo: NON_ADMIN,       // Employee, Dept Head, HR (NOT Admin)
  myApplications: NON_ADMIN,   // personal leave history (NOT Admin)
  myMemos: NON_ADMIN,          // personal memos (NOT Admin)
  reviewLeave: ['checker', 'approver', 'admin'],
  allMemos: ['maker', 'checker', 'approver', 'admin'],
  userManagement: ['admin'],
  reports: ['checker', 'approver', 'admin'],
};

/** Can `role` perform `action`? Central gate for role-based UI. */
export const can = (role, action) => (PERMISSIONS[action] || []).includes(role);
