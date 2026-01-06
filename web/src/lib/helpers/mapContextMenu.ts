import type { LifetimeStatus } from './mapTypes';

export type ContextMenuMode =
	| 'pane-menu'
	| 'node-menu'
	| 'edge-menu'
	| 'search'
	| 'unidentified'
	| 'mass-status'
	| 'lifetime-status';

export interface ContextMenuState {
	x: number;
	y: number;
	flowX: number;
	flowY: number;
	mode: ContextMenuMode;
	nodeId?: string;
	edgeId?: string;
	isNodeLocked?: boolean;
}

export const MASS_STATUS_OPTIONS = [
	{ value: 0, label: 'Fresh' },
	{ value: 1, label: 'Reduced' },
	{ value: 2, label: 'Critical' }
] as const;

export const LIFETIME_STATUS_OPTIONS: { value: LifetimeStatus; label: string }[] = [
	{ value: 'stable', label: 'Stable' },
	{ value: 'aging', label: 'Aging' },
	{ value: 'critical', label: 'Critical' },
	{ value: 'eol', label: 'End of Life' }
];
