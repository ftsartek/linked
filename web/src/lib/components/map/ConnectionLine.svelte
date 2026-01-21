<script lang="ts">
	import { getContext } from 'svelte';
	import {
		useConnection,
		getBezierPath,
		getSmoothStepPath,
		getStraightPath,
		Position
	} from '@xyflow/svelte';
	import type { EdgeType } from '$lib/helpers/mapTypes';

	const connection = useConnection();

	// Get edge type from context (set by Map.svelte)
	const getEdgeType = getContext<() => EdgeType>('edgeType');
	const edgeType = $derived(getEdgeType?.() ?? 'default');

	/**
	 * Determine which side of the source node the edge should exit toward the target.
	 */
	function getExitSide(
		sourceCenter: { x: number; y: number },
		targetCenter: { x: number; y: number },
		nodeWidth: number,
		nodeHeight: number
	): Position {
		const dx = targetCenter.x - sourceCenter.x;
		const dy = targetCenter.y - sourceCenter.y;

		const normalizedDx = nodeWidth > 0 ? dx / (nodeWidth / 2) : dx;
		const normalizedDy = nodeHeight > 0 ? dy / (nodeHeight / 2) : dy;

		if (Math.abs(normalizedDx) > Math.abs(normalizedDy)) {
			return dx > 0 ? Position.Right : Position.Left;
		} else {
			return dy > 0 ? Position.Bottom : Position.Top;
		}
	}

	/**
	 * Get the edge point on the border of a node toward a target point.
	 */
	function getEdgePoint(
		nodePos: { x: number; y: number },
		nodeWidth: number,
		nodeHeight: number,
		targetPoint: { x: number; y: number }
	): { x: number; y: number; position: Position } {
		const nodeCenter = {
			x: nodePos.x + nodeWidth / 2,
			y: nodePos.y + nodeHeight / 2
		};

		const side = getExitSide(nodeCenter, targetPoint, nodeWidth, nodeHeight);

		let x = nodeCenter.x;
		let y = nodeCenter.y;

		switch (side) {
			case Position.Top:
				y = nodePos.y;
				break;
			case Position.Bottom:
				y = nodePos.y + nodeHeight;
				break;
			case Position.Left:
				x = nodePos.x;
				break;
			case Position.Right:
				x = nodePos.x + nodeWidth;
				break;
		}

		return { x, y, position: side };
	}

	const pathData = $derived.by(() => {
		if (!connection.current.inProgress) return null;

		const { to, fromNode, toNode } = connection.current;

		// Source node dimensions
		const sourceWidth = fromNode.measured?.width ?? 160;
		const sourceHeight = fromNode.measured?.height ?? 80;
		const sourcePos = fromNode.internals?.positionAbsolute ?? fromNode.position;

		let sx: number, sy: number, sourcePosition: Position;
		let tx: number, ty: number, targetPosition: Position;

		// Calculate source point (from node center toward target)
		const sourceCenter = {
			x: sourcePos.x + sourceWidth / 2,
			y: sourcePos.y + sourceHeight / 2
		};

		if (toNode) {
			// Hovering over a target node - calculate edge points for both nodes
			const targetWidth = toNode.measured?.width ?? 160;
			const targetHeight = toNode.measured?.height ?? 80;
			const targetPos = toNode.internals?.positionAbsolute ?? toNode.position;
			const targetCenter = {
				x: targetPos.x + targetWidth / 2,
				y: targetPos.y + targetHeight / 2
			};

			// Get source edge point toward target center
			const sourcePoint = getEdgePoint(sourcePos, sourceWidth, sourceHeight, targetCenter);
			sx = sourcePoint.x;
			sy = sourcePoint.y;
			sourcePosition = sourcePoint.position;

			// Get target edge point toward source center
			const targetPoint = getEdgePoint(targetPos, targetWidth, targetHeight, sourceCenter);
			tx = targetPoint.x;
			ty = targetPoint.y;
			targetPosition = targetPoint.position;
		} else {
			// Not hovering over a node - draw from source edge to mouse position
			const sourcePoint = getEdgePoint(sourcePos, sourceWidth, sourceHeight, to);
			sx = sourcePoint.x;
			sy = sourcePoint.y;
			sourcePosition = sourcePoint.position;

			tx = to.x;
			ty = to.y;
			// Infer target position as opposite of source
			targetPosition =
				sourcePosition === Position.Left
					? Position.Right
					: sourcePosition === Position.Right
						? Position.Left
						: sourcePosition === Position.Top
							? Position.Bottom
							: Position.Top;
		}

		// Generate path based on edge type
		let path: string;
		switch (edgeType) {
			case 'straight':
				[path] = getStraightPath({ sourceX: sx, sourceY: sy, targetX: tx, targetY: ty });
				break;
			case 'step':
				[path] = getSmoothStepPath({
					sourceX: sx,
					sourceY: sy,
					targetX: tx,
					targetY: ty,
					sourcePosition,
					targetPosition,
					borderRadius: 0
				});
				break;
			case 'smoothstep':
				[path] = getSmoothStepPath({
					sourceX: sx,
					sourceY: sy,
					targetX: tx,
					targetY: ty,
					sourcePosition,
					targetPosition
				});
				break;
			case 'default':
			case 'simplebezier':
			default:
				[path] = getBezierPath({
					sourceX: sx,
					sourceY: sy,
					targetX: tx,
					targetY: ty,
					sourcePosition,
					targetPosition
				});
				break;
		}

		return path;
	});
</script>

{#if pathData}
	<path
		d={pathData}
		fill="none"
		stroke="rgba(59, 130, 246, 0.8)"
		stroke-width="2"
		stroke-dasharray="6 3"
		class="svelte-flow__connection-path"
	/>
{/if}
