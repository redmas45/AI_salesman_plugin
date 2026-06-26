import { tab } from './shared';
import type { CrmVerticalDefinition } from './types';

export const jobsRecruitingVertical: CrmVerticalDefinition = {
  key: 'jobs_recruiting',
  label: 'Jobs & Recruiting',
  riskLevel: 'high',
  entityLabelSingular: 'job',
  entityLabelPlural: 'jobs',
  defaultPlanLabel: 'Recruiting plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Jobs'),
    tab('leads', 'Candidates'),
    tab('compliance', 'Compliance'),
    tab('activity', 'Conversations'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['job_posting', 'company', 'role_family', 'skill', 'application_flow', 'recruiter'],
  readinessChecks: ['jobs', 'application_flow', 'resume_upload', 'company_pages', 'privacy', 'decisioning_guard'],
};
