import { apiClient } from '$lib/client/client';
import { toaster } from '$lib/stores/toaster';
import type { LifetimeStatus } from './mapTypes';

export interface ActionResult {
	success: boolean;
}

function showError(message: string) {
	toaster.create({
		title: 'Error',
		description: message,
		type: 'error'
	});
}

export async function removeNode(mapId: string, nodeId: string): Promise<ActionResult> {
	const { error } = await apiClient.DELETE('/maps/{map_id}/nodes/{node_id}', {
		params: { path: { map_id: mapId, node_id: nodeId } }
	});

	if (error) {
		showError('detail' in error ? error.detail : 'Failed to remove node');
		return { success: false };
	}
	return { success: true };
}

export async function toggleNodeLock(
	mapId: string,
	nodeId: string,
	newLockedState: boolean
): Promise<ActionResult> {
	const { error } = await apiClient.PATCH('/maps/{map_id}/nodes/{node_id}/locked', {
		params: { path: { map_id: mapId, node_id: nodeId } },
		body: { locked: newLockedState }
	});

	if (error) {
		showError('detail' in error ? error.detail : 'Failed to toggle node lock');
		return { success: false };
	}
	return { success: true };
}

export async function updateNodePosition(
	mapId: string,
	nodeId: string,
	posX: number,
	posY: number
): Promise<ActionResult> {
	const { error } = await apiClient.PATCH('/maps/{map_id}/nodes/{node_id}/position', {
		params: { path: { map_id: mapId, node_id: nodeId } },
		body: { pos_x: posX, pos_y: posY }
	});

	if (error) {
		showError('detail' in error ? error.detail : 'Failed to update node position');
		return { success: false };
	}
	return { success: true };
}

export async function updateNodeSystem(
	mapId: string,
	nodeId: string,
	systemId: number
): Promise<ActionResult> {
	const { error } = await apiClient.PATCH('/maps/{map_id}/nodes/{node_id}/system', {
		params: { path: { map_id: mapId, node_id: nodeId } },
		body: { system_id: systemId }
	});

	if (error) {
		showError('detail' in error ? error.detail : 'Failed to update system');
		return { success: false };
	}
	return { success: true };
}

export async function createNode(
	mapId: string,
	systemId: number,
	posX: number,
	posY: number
): Promise<ActionResult> {
	const { error } = await apiClient.POST('/maps/{map_id}/nodes', {
		params: { path: { map_id: mapId } },
		body: { system_id: systemId, pos_x: posX, pos_y: posY }
	});

	if (error) {
		showError('detail' in error ? error.detail : 'Failed to create node');
		return { success: false };
	}
	return { success: true };
}

export async function removeEdge(mapId: string, edgeId: string): Promise<ActionResult> {
	const { error } = await apiClient.DELETE('/maps/{map_id}/links/{link_id}', {
		params: { path: { map_id: mapId, link_id: edgeId } }
	});

	if (error) {
		showError('detail' in error ? error.detail : 'Failed to remove connection');
		return { success: false };
	}
	return { success: true };
}

export async function updateEdgeMassStatus(
	mapId: string,
	edgeId: string,
	massUsage: number
): Promise<ActionResult> {
	const { error } = await apiClient.PATCH('/maps/{map_id}/links/{link_id}', {
		params: { path: { map_id: mapId, link_id: edgeId } },
		body: { mass_usage: massUsage }
	});

	if (error) {
		showError('detail' in error ? error.detail : 'Failed to update mass status');
		return { success: false };
	}
	return { success: true };
}

export async function updateEdgeLifetimeStatus(
	mapId: string,
	edgeId: string,
	lifetimeStatus: LifetimeStatus
): Promise<ActionResult> {
	const { error } = await apiClient.PATCH('/maps/{map_id}/links/{link_id}', {
		params: { path: { map_id: mapId, link_id: edgeId } },
		body: { lifetime_status: lifetimeStatus }
	});

	if (error) {
		showError('detail' in error ? error.detail : 'Failed to update lifetime status');
		return { success: false };
	}
	return { success: true };
}

export async function reverseEdge(mapId: string, edgeId: string): Promise<ActionResult> {
	const { error } = await apiClient.PATCH('/maps/{map_id}/links/{link_id}', {
		params: { path: { map_id: mapId, link_id: edgeId } },
		body: { reverse: true }
	});

	if (error) {
		showError('detail' in error ? error.detail : 'Failed to reverse connection');
		return { success: false };
	}
	return { success: true };
}

export async function createEdge(
	mapId: string,
	sourceNodeId: string,
	targetNodeId: string
): Promise<ActionResult> {
	const { error } = await apiClient.POST('/maps/{map_id}/links', {
		params: { path: { map_id: mapId } },
		body: { source_node_id: sourceNodeId, target_node_id: targetNodeId }
	});

	if (error) {
		showError('detail' in error ? error.detail : 'Failed to create connection');
		return { success: false };
	}
	return { success: true };
}

export async function setEdgeWormholeType(
	mapId: string,
	edgeId: string,
	wormholeId: number
): Promise<ActionResult> {
	const { error } = await apiClient.PATCH('/maps/{map_id}/links/{link_id}', {
		params: { path: { map_id: mapId, link_id: edgeId } },
		body: { wormhole_id: wormholeId }
	});

	if (error) {
		showError('detail' in error ? error.detail : 'Failed to set wormhole type');
		return { success: false };
	}
	return { success: true };
}

/**
 * Create a new node and connect it to an existing node with a wormhole type.
 */
export async function createNodeWithConnection(
	mapId: string,
	sourceNodeId: string,
	systemId: number,
	posX: number,
	posY: number,
	wormholeId?: number
): Promise<ActionResult> {
	// 1. Create target node
	const { data: nodeData, error: nodeError } = await apiClient.POST('/maps/{map_id}/nodes', {
		params: { path: { map_id: mapId } },
		body: { system_id: systemId, pos_x: posX, pos_y: posY }
	});

	if (nodeError || !nodeData) {
		showError(
			'detail' in (nodeError ?? {})
				? (nodeError as { detail: string }).detail
				: 'Failed to create node'
		);
		return { success: false };
	}

	// 2. Create edge with wormhole type
	const { error: linkError } = await apiClient.POST('/maps/{map_id}/links', {
		params: { path: { map_id: mapId } },
		body: {
			source_node_id: sourceNodeId,
			target_node_id: nodeData.node_id,
			wormhole_id: wormholeId
		}
	});

	if (linkError) {
		showError('detail' in linkError ? linkError.detail : 'Failed to create connection');
		return { success: false };
	}

	return { success: true };
}
