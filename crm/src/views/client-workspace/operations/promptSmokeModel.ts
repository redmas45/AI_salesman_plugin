export const SMOKE_TEST_OPERATION_STAGES: string[] = [
  'Preparing prompt set',
  'Running assistant responses',
  'Checking expected actions',
  'Comparing retrieved data',
  'Saving prompt evidence',
];

export interface SmokeTestFeedbackState {
  status: 'running' | 'complete' | 'failed';
  stageIndex: number;
  startedAt: number;
  message: string;
}

export function minimumSmokeTestDuration(): number {
  return Math.max(SMOKE_TEST_OPERATION_STAGES.length * 900 + 400, 6200);
}
