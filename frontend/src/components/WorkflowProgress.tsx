import { WorkflowStatus } from '../services/workflow';
import {
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/solid';

interface WorkflowProgressProps {
  workflow: WorkflowStatus;
}

const stageIcons = {
  completed: CheckCircleIcon,
  in_progress: ArrowPathIcon,
  failed: XCircleIcon,
  pending: ClockIcon,
};

const stageColors = {
  completed: 'text-success-500 bg-success-500/20',
  in_progress: 'text-tronas-400 bg-tronas-500/20',
  failed: 'text-danger-400 bg-danger-500/20',
  pending: 'text-navy-500 bg-navy-500/20',
};

const stageBorderColors = {
  completed: 'border-success-500',
  in_progress: 'border-tronas-500',
  failed: 'border-danger-500',
  pending: 'border-navy-700',
};

export default function WorkflowProgress({ workflow }: WorkflowProgressProps) {
  return (
    <div className="space-y-6">
      {/* Progress Header */}
      <div>
        <div className="flex justify-between items-center mb-3">
          <span className="text-sm text-navy-400">
            {workflow.tasks_completed} of {workflow.tasks_total} tasks completed
          </span>
          <span className="text-sm font-semibold text-tronas-400">
            {workflow.progress_percentage}%
          </span>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-navy-800 rounded-full h-2 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-tronas-500 to-tronas-400 rounded-full transition-all duration-500"
            style={{ width: `${workflow.progress_percentage}%` }}
          />
        </div>
      </div>

      {/* Stages */}
      <div className="space-y-3">
        {workflow.stages.map((stage, index) => {
          const Icon = stageIcons[stage.status];
          const colorClass = stageColors[stage.status];
          const borderClass = stageBorderColors[stage.status];
          const isLast = index === workflow.stages.length - 1;

          return (
            <div key={index} className="relative flex items-start gap-4">
              {/* Connector Line */}
              {!isLast && (
                <div
                  className={`absolute left-[19px] top-10 w-0.5 h-8 ${
                    stage.status === 'completed' ? 'bg-success-500/50' : 'bg-navy-700'
                  }`}
                />
              )}

              {/* Icon */}
              <div
                className={`relative z-10 p-2 rounded-xl border ${colorClass} ${borderClass}`}
              >
                <Icon
                  className={`h-5 w-5 ${stage.status === 'in_progress' ? 'animate-spin' : ''}`}
                />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className={`text-sm font-medium ${
                      stage.status === 'completed' ? 'text-white' :
                      stage.status === 'in_progress' ? 'text-tronas-400' :
                      'text-navy-400'
                    }`}>
                      {stage.name}
                    </h4>
                    <p className={`text-xs mt-0.5 capitalize ${
                      stage.status === 'in_progress' ? 'text-tronas-400' :
                      stage.status === 'failed' ? 'text-danger-400' :
                      'text-navy-500'
                    }`}>
                      {stage.status.replace('_', ' ')}
                    </p>
                  </div>
                  {stage.completed_at && (
                    <span className="text-xs text-navy-500">
                      {new Date(stage.completed_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Estimated Completion */}
      {workflow.estimated_completion && (
        <div className="pt-4 border-t border-navy-700">
          <div className="flex items-center gap-2 text-sm">
            <ClockIcon className="h-4 w-4 text-navy-500" />
            <span className="text-navy-400">Estimated completion:</span>
            <span className="text-white font-medium">
              {new Date(workflow.estimated_completion).toLocaleDateString()}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
