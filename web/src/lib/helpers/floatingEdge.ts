import { Position, type InternalNode, type XYPosition, type Edge } from '@xyflow/svelte';

/**
 * Get the center position of a node.
 */
function getNodeCenter(node: InternalNode): XYPosition {
	const nodeWidth = node.measured?.width ?? 0;
	const nodeHeight = node.measured?.height ?? 0;
	const nodePos = node.internals.positionAbsolute;
	return {
		x: nodePos.x + nodeWidth / 2,
		y: nodePos.y + nodeHeight / 2
	};
}

/**
 * Determine which side of the source node an edge exits toward the target.
 */
function getExitSide(source: InternalNode, target: InternalNode): Position {
	const sourceCenter = getNodeCenter(source);
	const targetCenter = getNodeCenter(target);

	const dx = targetCenter.x - sourceCenter.x;
	const dy = targetCenter.y - sourceCenter.y;

	const nodeWidth = source.measured?.width ?? 0;
	const nodeHeight = source.measured?.height ?? 0;

	// Normalize by dimensions to handle rectangular nodes
	const normalizedDx = nodeWidth > 0 ? dx / (nodeWidth / 2) : dx;
	const normalizedDy = nodeHeight > 0 ? dy / (nodeHeight / 2) : dy;

	if (Math.abs(normalizedDx) > Math.abs(normalizedDy)) {
		return dx > 0 ? Position.Right : Position.Left;
	} else {
		return dy > 0 ? Position.Bottom : Position.Top;
	}
}

/**
 * Get the sort key for distributing edges along a side.
 * For top/bottom sides: sort by x position of target (left to right)
 * For left/right sides: sort by y position of target (top to bottom)
 */
function getEdgeSortKey(source: InternalNode, target: InternalNode, side: Position): number {
	const targetCenter = getNodeCenter(target);

	switch (side) {
		case Position.Top:
		case Position.Bottom:
			// Sort by x position (left to right)
			return targetCenter.x;
		case Position.Left:
		case Position.Right:
			// Sort by y position (top to bottom)
			return targetCenter.y;
	}
}

export interface FloatingEdgeParams {
	sx: number;
	sy: number;
	tx: number;
	ty: number;
	sourcePos: Position;
	targetPos: Position;
}

interface EdgeSideInfo {
	edgeId: string;
	targetNodeId: string;
	sortKey: number;
}

/**
 * Get distributed edge parameters with symmetric spacing around center.
 *
 * When multiple edges connect to the same side of a node, they are distributed
 * symmetrically around the center with 8px spacing:
 * - 1 edge: centered
 * - 2 edges: ±4px from center
 * - 3 edges: center + ±8px
 * - 4 edges: ±4px, ±12px
 */
export function getDistributedEdgeParams(
	source: InternalNode,
	target: InternalNode,
	allEdges: Edge[],
	getNode: (id: string) => InternalNode | undefined,
	currentEdgeId: string,
	cornerBuffer: number = 4,
	edgeSpacing: number = 8,
	lineExtension: number = 4
): FloatingEdgeParams {
	// Calculate positions for source side
	const sourceResult = calculateDistributedPosition(
		source,
		target,
		allEdges,
		getNode,
		currentEdgeId,
		cornerBuffer,
		edgeSpacing
	);

	// Calculate positions for target side
	const targetResult = calculateDistributedPosition(
		target,
		source,
		allEdges,
		getNode,
		currentEdgeId,
		cornerBuffer,
		edgeSpacing
	);

	let sx = sourceResult.x;
	let sy = sourceResult.y;
	let tx = targetResult.x;
	let ty = targetResult.y;

	// Extend line endpoints outward to ensure full coverage at node edges
	const dx = tx - sx;
	const dy = ty - sy;
	const length = Math.sqrt(dx * dx + dy * dy);
	if (length > 0 && lineExtension > 0) {
		const ux = dx / length;
		const uy = dy / length;
		// Extend source outward (opposite direction from target)
		sx -= ux * lineExtension;
		sy -= uy * lineExtension;
		// Extend target outward (away from source)
		tx += ux * lineExtension;
		ty += uy * lineExtension;
	}

	return {
		sx,
		sy,
		tx,
		ty,
		sourcePos: sourceResult.position,
		targetPos: targetResult.position
	};
}

interface DistributedPositionResult {
	x: number;
	y: number;
	position: Position;
}

/**
 * Calculate the distributed position for one end of an edge.
 */
function calculateDistributedPosition(
	node: InternalNode,
	otherNode: InternalNode,
	allEdges: Edge[],
	getNode: (id: string) => InternalNode | undefined,
	currentEdgeId: string,
	cornerBuffer: number,
	edgeSpacing: number
): DistributedPositionResult {
	const nodeWidth = node.measured?.width ?? 0;
	const nodeHeight = node.measured?.height ?? 0;
	const nodePos = node.internals.positionAbsolute;
	const nodeCenter = getNodeCenter(node);

	// Determine which side this edge exits from
	const exitSide = getExitSide(node, otherNode);

	// Find all edges that share this node and exit on the same side
	const siblingEdges: EdgeSideInfo[] = [];

	for (const edge of allEdges) {
		// Check if this edge involves our node
		const isSource = edge.source === node.id;
		const isTarget = edge.target === node.id;

		if (!isSource && !isTarget) continue;

		// Get the other node for this edge
		const otherNodeId = isSource ? edge.target : edge.source;
		const edgeOtherNode = getNode(otherNodeId);
		if (!edgeOtherNode) continue;

		// Skip self-loops
		if (edge.source === edge.target) continue;

		// Check if this edge exits on the same side
		const edgeExitSide = getExitSide(node, edgeOtherNode);
		if (edgeExitSide !== exitSide) continue;

		// This edge shares the same side
		siblingEdges.push({
			edgeId: edge.id,
			targetNodeId: otherNodeId,
			sortKey: getEdgeSortKey(node, edgeOtherNode, exitSide)
		});
	}

	// Sort siblings so they fan out logically (left-to-right for top/bottom, top-to-bottom for left/right)
	siblingEdges.sort((a, b) => a.sortKey - b.sortKey);

	// Find the index of the current edge
	const currentIndex = siblingEdges.findIndex((e) => e.edgeId === currentEdgeId);
	const count = siblingEdges.length;

	// Calculate offset from center: (index - (count-1)/2) * spacing
	const offset = count > 0 ? (currentIndex - (count - 1) / 2) * edgeSpacing : 0;

	// Calculate the center point on the exit side
	let centerX = nodeCenter.x;
	let centerY = nodeCenter.y;

	switch (exitSide) {
		case Position.Top:
			centerY = nodePos.y;
			break;
		case Position.Bottom:
			centerY = nodePos.y + nodeHeight;
			break;
		case Position.Left:
			centerX = nodePos.x;
			break;
		case Position.Right:
			centerX = nodePos.x + nodeWidth;
			break;
	}

	// Apply offset perpendicular to the side
	let finalX = centerX;
	let finalY = centerY;

	if (exitSide === Position.Top || exitSide === Position.Bottom) {
		// Horizontal offset for top/bottom sides
		finalX = centerX + offset;
		// Clamp to stay within corner buffer
		const minX = nodePos.x + cornerBuffer;
		const maxX = nodePos.x + nodeWidth - cornerBuffer;
		finalX = Math.max(minX, Math.min(maxX, finalX));
	} else {
		// Vertical offset for left/right sides
		finalY = centerY + offset;
		// Clamp to stay within corner buffer
		const minY = nodePos.y + cornerBuffer;
		const maxY = nodePos.y + nodeHeight - cornerBuffer;
		finalY = Math.max(minY, Math.min(maxY, finalY));
	}

	return {
		x: finalX,
		y: finalY,
		position: exitSide
	};
}

// Keep the old function for backwards compatibility or simpler use cases
export function getFloatingEdgeParams(
	source: InternalNode,
	target: InternalNode,
	buffer: number = 4
): FloatingEdgeParams {
	const sourceIntersection = getNodeIntersection(source, target, buffer);
	const targetIntersection = getNodeIntersection(target, source, buffer);

	const sourcePos = getEdgePosition(source, sourceIntersection);
	const targetPos = getEdgePosition(target, targetIntersection);

	return {
		sx: sourceIntersection.x,
		sy: sourceIntersection.y,
		tx: targetIntersection.x,
		ty: targetIntersection.y,
		sourcePos,
		targetPos
	};
}

/**
 * Calculate where a line from the target node's center intersects
 * the source node's border, with an inset buffer to avoid corners.
 */
function getNodeIntersection(
	intersectionNode: InternalNode,
	targetNode: InternalNode,
	buffer: number = 4
): XYPosition {
	const nodeWidth = intersectionNode.measured?.width ?? 0;
	const nodeHeight = intersectionNode.measured?.height ?? 0;
	const nodePos = intersectionNode.internals.positionAbsolute;

	const targetWidth = targetNode.measured?.width ?? 0;
	const targetHeight = targetNode.measured?.height ?? 0;
	const targetPos = targetNode.internals.positionAbsolute;

	// Calculate centers
	const nodeCenterX = nodePos.x + nodeWidth / 2;
	const nodeCenterY = nodePos.y + nodeHeight / 2;
	const targetCenterX = targetPos.x + targetWidth / 2;
	const targetCenterY = targetPos.y + targetHeight / 2;

	// Direction vector from node center to target center
	const dx = targetCenterX - nodeCenterX;
	const dy = targetCenterY - nodeCenterY;

	// Handle edge case where nodes are at same position
	if (dx === 0 && dy === 0) {
		return { x: nodeCenterX, y: nodePos.y + nodeHeight };
	}

	// Inset dimensions (smaller rectangle to avoid corners)
	const halfWidth = nodeWidth / 2 - buffer;
	const halfHeight = nodeHeight / 2 - buffer;

	// Find intersection with each edge and pick the closest valid one
	let t = Infinity;

	// Right edge (dx > 0)
	if (dx > 0) {
		const tRight = halfWidth / dx;
		if (tRight > 0 && tRight < t) {
			const yAtIntersect = dy * tRight;
			if (Math.abs(yAtIntersect) <= halfHeight) {
				t = tRight;
			}
		}
	}
	// Left edge (dx < 0)
	if (dx < 0) {
		const tLeft = -halfWidth / dx;
		if (tLeft > 0 && tLeft < t) {
			const yAtIntersect = dy * tLeft;
			if (Math.abs(yAtIntersect) <= halfHeight) {
				t = tLeft;
			}
		}
	}
	// Bottom edge (dy > 0)
	if (dy > 0) {
		const tBottom = halfHeight / dy;
		if (tBottom > 0 && tBottom < t) {
			const xAtIntersect = dx * tBottom;
			if (Math.abs(xAtIntersect) <= halfWidth) {
				t = tBottom;
			}
		}
	}
	// Top edge (dy < 0)
	if (dy < 0) {
		const tTop = -halfHeight / dy;
		if (tTop > 0 && tTop < t) {
			const xAtIntersect = dx * tTop;
			if (Math.abs(xAtIntersect) <= halfWidth) {
				t = tTop;
			}
		}
	}

	// If no valid intersection found (shouldn't happen), fallback to bottom center
	if (t === Infinity) {
		return { x: nodeCenterX, y: nodePos.y + nodeHeight - buffer };
	}

	// Calculate intersection point and offset back to actual node border
	const intersectX = nodeCenterX + dx * t;
	const intersectY = nodeCenterY + dy * t;

	// Adjust from inset rectangle to actual border
	let finalX = intersectX;
	let finalY = intersectY;

	// Determine which edge we hit and push out to actual border
	const relX = intersectX - nodeCenterX;
	const relY = intersectY - nodeCenterY;

	if (Math.abs(Math.abs(relX) - halfWidth) < 0.01) {
		// Hit left or right edge
		finalX = nodeCenterX + (relX > 0 ? nodeWidth / 2 : -nodeWidth / 2);
	}
	if (Math.abs(Math.abs(relY) - halfHeight) < 0.01) {
		// Hit top or bottom edge
		finalY = nodeCenterY + (relY > 0 ? nodeHeight / 2 : -nodeHeight / 2);
	}

	return { x: finalX, y: finalY };
}

/**
 * Determine which side of the node the intersection point is on.
 */
function getEdgePosition(node: InternalNode, intersectionPoint: XYPosition): Position {
	const nodeWidth = node.measured?.width ?? 0;
	const nodeHeight = node.measured?.height ?? 0;
	const nodePos = node.internals.positionAbsolute;

	const nodeCenterX = nodePos.x + nodeWidth / 2;
	const nodeCenterY = nodePos.y + nodeHeight / 2;

	const dx = intersectionPoint.x - nodeCenterX;
	const dy = intersectionPoint.y - nodeCenterY;

	// Normalize by dimensions to handle rectangular nodes
	const normalizedDx = dx / (nodeWidth / 2);
	const normalizedDy = dy / (nodeHeight / 2);

	if (Math.abs(normalizedDx) > Math.abs(normalizedDy)) {
		return dx > 0 ? Position.Right : Position.Left;
	} else {
		return dy > 0 ? Position.Bottom : Position.Top;
	}
}
