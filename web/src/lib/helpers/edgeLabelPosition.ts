import type { Position } from '@xyflow/svelte';

const LABEL_OFFSET = 40;

/**
 * Calculate a point on a cubic bezier curve at parameter t.
 */
function bezierPoint(t: number, p0: number, p1: number, p2: number, p3: number): number {
	const mt = 1 - t;
	const mt2 = mt * mt;
	const mt3 = mt2 * mt;
	const t2 = t * t;
	const t3 = t2 * t;
	return mt3 * p0 + 3 * mt2 * t * p1 + 3 * mt * t2 * p2 + t3 * p3;
}

/**
 * Calculate label position for a bezier curve at a fixed distance from the source.
 * Parses control points from the SVG path and walks along the curve.
 */
export function getBezierLabelPosition(
	path: string,
	sx: number,
	sy: number,
	tx: number,
	ty: number,
	fallbackX: number,
	fallbackY: number
): { x: number; y: number } {
	// Parse bezier control points from path: "M{sx},{sy} C{c1x},{c1y} {c2x},{c2y} {tx},{ty}"
	const match = path.match(
		/M([\d.-]+),([\d.-]+)\s*C([\d.-]+),([\d.-]+)\s+([\d.-]+),([\d.-]+)\s+([\d.-]+),([\d.-]+)/
	);

	if (!match) {
		return { x: fallbackX, y: fallbackY };
	}

	const [, , , c1xStr, c1yStr, c2xStr, c2yStr] = match;
	const c1x = Number(c1xStr);
	const c1y = Number(c1yStr);
	const c2x = Number(c2xStr);
	const c2y = Number(c2yStr);

	// Walk along the curve until we reach the target distance
	let prevX = sx;
	let prevY = sy;
	let accumulatedDist = 0;

	for (let t = 0.01; t <= 1; t += 0.01) {
		const x = bezierPoint(t, sx, c1x, c2x, tx);
		const y = bezierPoint(t, sy, c1y, c2y, ty);

		const segmentDist = Math.sqrt((x - prevX) ** 2 + (y - prevY) ** 2);
		accumulatedDist += segmentDist;

		if (accumulatedDist >= LABEL_OFFSET) {
			return { x, y };
		}

		prevX = x;
		prevY = y;
	}

	// Fallback if curve is shorter than offset
	return { x: fallbackX, y: fallbackY };
}

/**
 * Calculate label position for a straight edge at a fixed distance from the source.
 */
export function getStraightLabelPosition(
	sx: number,
	sy: number,
	tx: number,
	ty: number
): { x: number; y: number } {
	const dx = tx - sx;
	const dy = ty - sy;
	const dist = Math.sqrt(dx * dx + dy * dy) || 1;

	return {
		x: sx + (dx / dist) * LABEL_OFFSET,
		y: sy + (dy / dist) * LABEL_OFFSET
	};
}

/**
 * Calculate label position for step/smoothstep edges.
 * Offsets from source in the handle direction.
 */
export function getStepLabelPosition(
	sx: number,
	sy: number,
	sourcePos: Position
): { x: number; y: number } {
	return {
		x: sx + (sourcePos === 'left' ? -LABEL_OFFSET : sourcePos === 'right' ? LABEL_OFFSET : 0),
		y: sy + (sourcePos === 'top' ? -LABEL_OFFSET : sourcePos === 'bottom' ? LABEL_OFFSET : 0)
	};
}
