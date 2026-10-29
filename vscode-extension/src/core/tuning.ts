import type { TuningVariable } from '../shared/types';

export type { TuningVariable };

/** Tuning variables of the input-processor (see .env.example and settings.py). */

export const TUNING: TuningVariable[] = [
  {
    key: 'INPUT_PROCESSOR_LOG_LEVEL',
    label: 'Log level',
    group: 'Logging',
    type: 'select',
    default: 'INFO',
    options: ['DEBUG', 'INFO', 'WARNING', 'ERROR'],
    help: 'How much the container writes to its logs.',
  },
  {
    key: 'INPUT_PROCESSOR_VIDEO_SEGMENT_SECONDS',
    label: 'Segment length (seconds)',
    group: 'Video',
    type: 'number',
    default: '60',
    help: 'Long recordings are split into segments of this length before analysis.',
  },
  {
    key: 'INPUT_PROCESSOR_VIDEO_SPLIT_MIN_MB',
    label: 'Split videos larger than (MB)',
    group: 'Video',
    type: 'number',
    default: '12',
    help: 'Smaller videos are sent whole.',
  },
  {
    key: 'INPUT_PROCESSOR_VIDEO_FORCE_SPLIT',
    label: 'Always split videos',
    group: 'Video',
    type: 'boolean',
    default: 'false',
    help: 'Split every video, whatever its size.',
  },
  {
    key: 'INPUT_PROCESSOR_VIDEO_SPLIT_BY_DURATION',
    label: 'Split by duration',
    group: 'Video',
    type: 'boolean',
    default: 'true',
    help: 'Also split videos that are longer than one segment.',
  },
  {
    key: 'INPUT_PROCESSOR_VIDEO_REQUIRE_AUDIO',
    label: 'Require audio in segments',
    group: 'Video',
    type: 'boolean',
    default: 'true',
    help: 'Only keep segments that still have an audio track.',
  },
  {
    key: 'INPUT_PROCESSOR_VIDEO_CONSOLIDATE',
    label: 'Consolidate segment summaries',
    group: 'Video',
    type: 'boolean',
    default: 'true',
    help: 'Merge the segment summaries into one document with an extra model call.',
  },
  {
    key: 'INPUT_PROCESSOR_VIDEO_FRAME_SECONDS',
    label: 'Frame interval (seconds)',
    group: 'Video',
    type: 'number',
    default: '2',
    help: 'For models that cannot take video: one frame is sampled every N seconds.',
  },
  {
    key: 'INPUT_PROCESSOR_VIDEO_MAX_FRAMES',
    label: 'Maximum frames',
    group: 'Video',
    type: 'number',
    default: '20',
    help: 'Upper bound on the frames sent to the model.',
  },
];

/** Variables that are never shown as plain text. */
export const HF_TOKEN = 'HF_TOKEN';
