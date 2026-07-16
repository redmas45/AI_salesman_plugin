import { tab } from '../shared';
import type { CrmVerticalDefinition } from '../types';

export const educationVertical: CrmVerticalDefinition = {
  key: 'education',
  label: 'Education',
  riskLevel: 'low',
  entityLabelSingular: 'course',
  entityLabelPlural: 'courses',
  defaultPlanLabel: 'Education plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Courses'),
    tab('leads', 'Leads'),
    tab('activity', 'Conversations'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['course', 'program', 'certificate', 'instructor', 'learning_path', 'cohort'],
  readinessChecks: ['courses', 'syllabus', 'pricing', 'enrollment', 'lead_capture', 'policies'],
};
