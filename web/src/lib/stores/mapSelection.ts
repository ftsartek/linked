import { writable } from 'svelte/store';
import type { components } from '$lib/client/schema';

export type EnrichedNodeInfo = components['schemas']['EnrichedNodeInfo'];

export interface MapSelectionState {
	selectedNode: EnrichedNodeInfo | null;
	mapId: string | null;
	isReadOnly: boolean;
	signatureRefreshTrigger: number;
}

const initialState: MapSelectionState = {
	selectedNode: null,
	mapId: null,
	isReadOnly: true,
	signatureRefreshTrigger: 0
};

export const mapSelection = writable<MapSelectionState>(initialState);

export function selectNode(node: EnrichedNodeInfo | null) {
	mapSelection.update((state) => ({ ...state, selectedNode: node }));
}

export function setMapContext(mapId: string, isReadOnly: boolean) {
	mapSelection.update((state) => ({ ...state, mapId, isReadOnly, selectedNode: null }));
}

export function clearSelection() {
	mapSelection.update((state) => ({ ...state, selectedNode: null }));
}

export function triggerSignatureRefresh() {
	mapSelection.update((state) => ({
		...state,
		signatureRefreshTrigger: state.signatureRefreshTrigger + 1
	}));
}
