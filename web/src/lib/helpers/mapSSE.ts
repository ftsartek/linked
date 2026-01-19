import type { Node, Edge } from '@xyflow/svelte';
import { getApiUrl } from '$lib/client/client';
import type { NodeInfo, LinkInfo } from './mapHelpers';
import type { MapInfo, EdgeType, Rankdir } from './mapTypes';

export interface MapSSECallbacks {
	onNodeCreated: (node: Node) => void;
	onNodeUpdated: (nodeData: NodeInfo) => void;
	onNodeDeleted: (nodeId: string) => void;
	onEdgeCreated: (edge: Edge) => void;
	onEdgeUpdated: (linkData: LinkInfo) => void;
	onEdgeDeleted: (edgeId: string) => void;
	onMapUpdated: (mapInfo: MapInfo, edgeType: EdgeType, rankdir: Rankdir) => void;
	onMapDeleted: () => void;
	onAccessRevoked: () => void;
	onSyncError: (message: string) => void;
	onSignatureChange: () => void;
	onNoteChange: () => void;
	onConnected: () => void;
	onError: () => void;
}

export interface MapSSEConfig {
	mapId: string;
	lastEventId: string | null;
	callbacks: MapSSECallbacks;
}

/**
 * Creates an SSE connection for map events.
 * Returns a cleanup function to close the connection.
 */
export function createMapSSE(config: MapSSEConfig): () => void {
	const { mapId, lastEventId, callbacks } = config;

	const sseUrl = lastEventId
		? getApiUrl(`/maps/${mapId}/events?last_event_id=${encodeURIComponent(lastEventId)}`)
		: getApiUrl(`/maps/${mapId}/events`);

	const eventSource = new EventSource(sseUrl, { withCredentials: true });

	eventSource.onopen = () => callbacks.onConnected();
	eventSource.onerror = () => callbacks.onError();

	// Node events
	eventSource.addEventListener('node_created', (event) => {
		try {
			const data = JSON.parse(event.data);
			const nodeData = data.data as NodeInfo;
			const newNode: Node = {
				id: nodeData.id,
				position: { x: nodeData.pos_x, y: nodeData.pos_y },
				data: nodeData,
				draggable: !nodeData.locked
			};
			callbacks.onNodeCreated(newNode);
		} catch {
			// Silently ignore parse errors for SSE events
		}
	});

	eventSource.addEventListener('node_updated', (event) => {
		try {
			const data = JSON.parse(event.data);
			const nodeData = data.data as NodeInfo;
			callbacks.onNodeUpdated(nodeData);
		} catch {
			// Silently ignore parse errors for SSE events
		}
	});

	eventSource.addEventListener('node_deleted', (event) => {
		try {
			const data = JSON.parse(event.data);
			const nodeId = data.data.node_id as string;
			callbacks.onNodeDeleted(nodeId);
		} catch {
			// Silently ignore parse errors for SSE events
		}
	});

	// Link/Edge events
	eventSource.addEventListener('link_created', (event) => {
		try {
			const data = JSON.parse(event.data);
			const linkData = data.data as LinkInfo;
			const newEdge: Edge = {
				id: linkData.id,
				source: linkData.source_node_id,
				target: linkData.target_node_id,
				data: {
					wormhole_id: linkData.wormhole_code,
					mass_remaining: linkData.mass_usage,
					status: linkData.lifetime_status
				}
			};
			callbacks.onEdgeCreated(newEdge);
		} catch {
			// Silently ignore parse errors for SSE events
		}
	});

	eventSource.addEventListener('link_updated', (event) => {
		try {
			const data = JSON.parse(event.data);
			const linkData = data.data as LinkInfo;
			callbacks.onEdgeUpdated(linkData);
		} catch {
			// Silently ignore parse errors for SSE events
		}
	});

	eventSource.addEventListener('link_deleted', (event) => {
		try {
			const data = JSON.parse(event.data);
			const linkId = data.data.link_id as string;
			callbacks.onEdgeDeleted(linkId);
		} catch {
			// Silently ignore parse errors for SSE events
		}
	});

	// Signature events - trigger refresh when signatures change
	eventSource.addEventListener('signature_created', () => {
		callbacks.onSignatureChange();
	});

	eventSource.addEventListener('signature_updated', () => {
		callbacks.onSignatureChange();
	});

	eventSource.addEventListener('signature_deleted', () => {
		callbacks.onSignatureChange();
	});

	eventSource.addEventListener('signatures_bulk_updated', () => {
		callbacks.onSignatureChange();
	});

	// Note events - trigger refresh when notes change
	eventSource.addEventListener('note_created', () => {
		callbacks.onNoteChange();
	});

	eventSource.addEventListener('note_updated', () => {
		callbacks.onNoteChange();
	});

	eventSource.addEventListener('note_deleted', () => {
		callbacks.onNoteChange();
	});

	// Map events
	eventSource.addEventListener('map_updated', (event) => {
		try {
			const data = JSON.parse(event.data);
			const changes = data.data.changes as MapInfo;
			const edgeType = (changes.edge_type as EdgeType) ?? 'default';
			const rankdir = (changes.rankdir as Rankdir) ?? 'LR';
			callbacks.onMapUpdated(changes, edgeType, rankdir);
		} catch {
			// Silently ignore parse errors for SSE events
		}
	});

	eventSource.addEventListener('map_deleted', () => {
		callbacks.onMapDeleted();
	});

	// Access revocation events
	eventSource.addEventListener('access_character_revoked', () => {
		callbacks.onAccessRevoked();
	});

	eventSource.addEventListener('access_corporation_revoked', () => {
		callbacks.onAccessRevoked();
	});

	eventSource.addEventListener('access_alliance_revoked', () => {
		callbacks.onAccessRevoked();
	});

	// Sync error event
	eventSource.addEventListener('sync_error', (event) => {
		try {
			const data = JSON.parse(event.data);
			const message = (data.message as string) || 'Please reload the map';
			callbacks.onSyncError(message);
		} catch {
			callbacks.onSyncError('Please reload the map');
		}
		eventSource.close();
	});

	return () => eventSource.close();
}
