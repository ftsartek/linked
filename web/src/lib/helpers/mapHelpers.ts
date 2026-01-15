import type { Node, Edge } from '@xyflow/svelte';
import type { components } from '$lib/client/schema';

export type NodeInfo = components['schemas']['EnrichedNodeInfo'];
export type LinkInfo = components['schemas']['EnrichedLinkInfo'];
export type SystemSearchResult =
	components['schemas']['SearchSystemsSystemSearchResponse_0SystemSearchResultResponseBody'];

export function transformNodes(apiNodes: NodeInfo[]): Node[] {
	return apiNodes.map((node) => ({
		id: node.id,
		position: { x: node.pos_x, y: node.pos_y },
		data: node,
		draggable: !node.locked
	}));
}

export function transformEdges(apiLinks: LinkInfo[]): Edge[] {
	return apiLinks.map((link) => ({
		id: link.id,
		source: link.source_node_id,
		target: link.target_node_id,
		data: {
			wormhole_id: link.wormhole_code,
			mass_remaining: link.mass_usage,
			status: link.lifetime_status
		}
	}));
}

export function formatSystemLabel(system: SystemSearchResult): string {
	return system.name + (system.class_name ? ': ' + system.class_name : '');
}

// Reverse mapping of api/src/utils/class_mapping.py SYSTEM_CLASS_MAPPING
const CLASS_NAME_TO_ID: Record<string, number> = {
	C1: 1,
	C2: 2,
	C3: 3,
	C4: 4,
	C5: 5,
	C6: 6,
	HS: 7,
	LS: 8,
	NS: 9,
	Thera: 12,
	C13: 13,
	Sentinel: 14,
	Barbican: 15,
	Vidette: 16,
	Redoubt: 17,
	Conflux: 18,
	Pochven: 25
};

/**
 * Convert a system class name (e.g., "C3", "HS") to its numeric ID.
 */
export function getSystemClassId(className: string | null | undefined): number | null {
	if (!className) return null;
	return CLASS_NAME_TO_ID[className] ?? null;
}
