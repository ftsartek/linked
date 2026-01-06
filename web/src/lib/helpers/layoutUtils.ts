import dagre from '@dagrejs/dagre';
import type { Node, Edge } from '@xyflow/svelte';
import type { Rankdir } from './mapTypes';

// Node dimensions (must match Node.svelte: h-20 w-40)
export const NODE_WIDTH = 160; // w-40 = 10rem = 160px
export const NODE_HEIGHT = 80; // h-20 = 5rem = 80px

// Dagre spacing constraints
export const SPACING_MIN = 20;
export const SPACING_MAX = 500;
export const SPACING_STEP = 20;

/**
 * Validates and normalizes a spacing value to be within allowed bounds
 * and a multiple of SPACING_STEP.
 */
export function validateSpacing(value: number): number {
	const clamped = Math.max(SPACING_MIN, Math.min(SPACING_MAX, value));
	return Math.round(clamped / SPACING_STEP) * SPACING_STEP;
}

export function getLayoutedElements(
	nodes: Node[],
	edges: Edge[],
	options: {
		rankdir: Rankdir;
		nodesep: number;
		ranksep: number;
	}
): { nodes: Node[]; edges: Edge[] } {
	const dagreGraph = new dagre.graphlib.Graph();
	dagreGraph.setDefaultEdgeLabel(() => ({}));
	dagreGraph.setGraph({
		rankdir: options.rankdir,
		nodesep: options.nodesep,
		ranksep: options.ranksep
	});

	nodes.forEach((node) => {
		dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
	});

	edges.forEach((edge) => {
		dagreGraph.setEdge(edge.source, edge.target);
	});

	dagre.layout(dagreGraph);

	const layoutedNodes = nodes.map((node) => {
		const nodeWithPosition = dagreGraph.node(node.id);
		// Dagre uses center coordinates, SvelteFlow uses top-left
		return {
			...node,
			position: {
				x: nodeWithPosition.x - NODE_WIDTH / 2,
				y: nodeWithPosition.y - NODE_HEIGHT / 2
			}
		};
	});

	return { nodes: layoutedNodes, edges };
}
