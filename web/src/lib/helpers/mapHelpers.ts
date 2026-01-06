import type { Node, Edge } from '@xyflow/svelte';
import type { components } from '$lib/client/schema';

export type NodeInfo = components['schemas']['EnrichedNodeInfo'];
export type LinkInfo = components['schemas']['EnrichedLinkInfo'];
export type SystemSearchResult =
	components['schemas']['routes.universe.controller.UniverseController.search_systemsSystemSearchResponse_0SystemSearchResultResponseBody'];

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
