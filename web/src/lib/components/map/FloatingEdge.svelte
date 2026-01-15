<script lang="ts" module>
	export type EdgeType = components['schemas']['EdgeType'];
	export type LifetimeStatus = 'stable' | 'aging' | 'critical' | 'eol';
	export type MassStatus = 0 | 1 | 2; // 0=Fresh, 1=Reduced, 2=Critical

	const lifetimeColors: Record<LifetimeStatus, string> = {
		stable: 'rgba(59, 130, 246, 0.8)', // bright blue
		aging: 'rgba(51, 108, 212, 0.8)', // deeper slate
		critical: 'rgba(234, 179, 8, 0.8)', // yellow
		eol: 'rgba(239, 68, 68, 0.8)' // red
	};

	const massDashPatterns: Record<MassStatus, string> = {
		0: 'none', // Fresh - solid
		1: '40 8', // Reduced - long dashes
		2: '12 8' // Critical - short dashes
	};
</script>

<script lang="ts">
	import { getContext } from 'svelte';
	import {
		EdgeLabel,
		getBezierPath,
		getSmoothStepPath,
		getStraightPath,
		useInternalNode,
		useEdges,
		useNodes,
		type EdgeProps,
		type InternalNode
	} from '@xyflow/svelte';
	import { getDistributedEdgeParams } from '$lib/helpers/floatingEdge';
	import {
		getBezierLabelPosition,
		getStraightLabelPosition,
		getStepLabelPosition
	} from '$lib/helpers/edgeLabelPosition';
	import type { components } from '$lib/client/schema';

	let { id, source, target, markerEnd, markerStart, data, selected }: EdgeProps = $props();

	// Get internal nodes to access position and dimensions
	// useInternalNode returns { current: InternalNode | undefined }
	// These need to be reactive to source/target changes (e.g., when connection is flipped)
	const sourceNodeRef = $derived(useInternalNode(source));
	const targetNodeRef = $derived(useInternalNode(target));

	// Get all edges and nodes for distribution calculation
	// useEdges/useNodes return { current: T[] } objects
	const edges = useEdges();
	const nodes = useNodes();

	// Get edge type from context (set by Map.svelte), fallback to 'default'
	const getEdgeType = getContext<() => EdgeType>('edgeType');
	const edgeType: EdgeType = $derived(getEdgeType?.() ?? 'default');
	const lifetimeStatus: LifetimeStatus = $derived((data?.status as LifetimeStatus) ?? 'stable');
	const lifetimeStrokeColor = $derived(lifetimeColors[lifetimeStatus] ?? lifetimeColors.stable);
	const massStatus: MassStatus = $derived((data?.mass_remaining as MassStatus) ?? 0);
	const massDashArray = $derived(massDashPatterns[massStatus] ?? 'none');
	const wormholeCode: string = $derived((data?.wormhole_id as string) ?? 'K162');

	const floatingParams = $derived.by(() => {
		const sourceNode = sourceNodeRef.current;
		const targetNode = targetNodeRef.current;
		if (!sourceNode || !targetNode) {
			return null;
		}

		// Build a node lookup from the nodes ref
		// useNodes/useEdges return { current: T[] } objects, not stores
		// eslint-disable-next-line svelte/prefer-svelte-reactivity -- local variable in derived, not reactive state
		const nodeMap = new Map<string, InternalNode>();

		// Add our known internal nodes
		nodeMap.set(source, sourceNode);
		nodeMap.set(target, targetNode);

		// For other nodes connected to our source/target, we need their positions
		// The nodes.current contains Node objects which have position but not internals
		// We'll need to construct a minimal InternalNode-like structure
		for (const node of nodes.current) {
			if (!nodeMap.has(node.id)) {
				// Create a minimal internal node structure for position calculations
				nodeMap.set(node.id, {
					id: node.id,
					measured: node.measured,
					internals: {
						positionAbsolute: node.position,
						z: 0,
						handleBounds: undefined
					}
				} as InternalNode);
			}
		}

		const getNodeFn = (nodeId: string) => nodeMap.get(nodeId);

		return getDistributedEdgeParams(sourceNode, targetNode, edges.current, getNodeFn, id, 4, 12);
	});

	const edgeData = $derived.by(() => {
		if (!floatingParams) {
			return { path: '', labelX: 0, labelY: 0 };
		}

		const { sx, sy, tx, ty, sourcePos, targetPos } = floatingParams;

		// Get the path string and center point
		let path: string;
		let centerX: number;
		let centerY: number;
		switch (edgeType) {
			case 'default':
			case 'simplebezier':
				[path, centerX, centerY] = getBezierPath({
					sourceX: sx,
					sourceY: sy,
					targetX: tx,
					targetY: ty,
					sourcePosition: sourcePos,
					targetPosition: targetPos
				});
				break;
			case 'straight':
				[path, centerX, centerY] = getStraightPath({
					sourceX: sx,
					sourceY: sy,
					targetX: tx,
					targetY: ty
				});
				break;
			case 'step':
				[path, centerX, centerY] = getSmoothStepPath({
					sourceX: sx,
					sourceY: sy,
					targetX: tx,
					targetY: ty,
					sourcePosition: sourcePos,
					targetPosition: targetPos,
					borderRadius: 0
				});
				break;
			case 'smoothstep':
			default:
				[path, centerX, centerY] = getSmoothStepPath({
					sourceX: sx,
					sourceY: sy,
					targetX: tx,
					targetY: ty,
					sourcePosition: sourcePos,
					targetPosition: targetPos
				});
		}

		// Calculate label position based on edge type
		let labelPos: { x: number; y: number };
		if (edgeType === 'default' || edgeType === 'simplebezier') {
			labelPos = getBezierLabelPosition(path, sx, sy, tx, ty, centerX, centerY);
		} else if (edgeType === 'straight') {
			labelPos = getStraightLabelPosition(sx, sy, tx, ty);
		} else {
			labelPos = getStepLabelPosition(sx, sy, sourcePos);
		}

		return { path, labelX: labelPos.x, labelY: labelPos.y };
	});
</script>

{#if floatingParams}
	<!-- Outer line (changes color when selected) -->
	<path
		d={edgeData.path}
		style="stroke: {selected
			? 'rgba(120, 120, 120, 0.8)'
			: 'rgba(60, 60, 60, 0.8)'}; stroke-width: 8px; fill: none;"
		marker-end={markerEnd}
		marker-start={markerStart}
	/>
	<!-- Inner line (lifetime color with dash pattern based on mass status) -->
	<path
		d={edgeData.path}
		style="stroke: {lifetimeStrokeColor}; stroke-width: 4px; fill: none; stroke-dasharray: {massDashArray};"
	/>
	<!-- Wormhole type label near source -->
	<EdgeLabel x={edgeData.labelX} y={edgeData.labelY} class="nodrag nopan" transparent>
		<div
			class="rounded border-2 border-surface-700 bg-surface-900 px-1.5 py-0.5 text-xs font-semibold text-surface-300"
		>
			{wormholeCode}
		</div>
	</EdgeLabel>
{/if}
