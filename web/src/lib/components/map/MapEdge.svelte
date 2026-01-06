<script lang="ts" module>
	export type EdgeType = 'default' | 'straight' | 'step' | 'smoothstep' | 'simplebezier';
	export type LifetimeStatus = 'stable' | 'aging' | 'critical' | 'eol';

	const lifetimeColors: Record<LifetimeStatus, string> = {
		stable: 'rgb(59, 130, 246)', // bright blue
		aging: 'rgb(51, 65, 85)', // deeper slate
		critical: 'rgb(234, 179, 8)', // yellow
		eol: 'rgb(239, 68, 68)' // red
	};
</script>

<script lang="ts">
	import { getContext } from 'svelte';
	import {
		getBezierPath,
		getSmoothStepPath,
		getStraightPath,
		type EdgeProps
	} from '@xyflow/svelte';

	let {
		sourceX,
		sourceY,
		sourcePosition,
		targetX,
		targetY,
		targetPosition,
		markerEnd,
		markerStart,
		data
	}: EdgeProps = $props();

	// Get edge type from context (set by Map.svelte), fallback to 'default'
	const getEdgeType = getContext<() => EdgeType>('edgeType');
	const edgeType: EdgeType = $derived(getEdgeType?.() ?? 'default');
	const lifetimeStatus: LifetimeStatus = $derived((data?.status as LifetimeStatus) ?? 'stable');
	const innerStrokeColor = $derived(lifetimeColors[lifetimeStatus] ?? lifetimeColors.stable);

	const pathData = $derived.by(() => {
		const common = { sourceX, sourceY, targetX, targetY };
		const withPositions = { ...common, sourcePosition, targetPosition };

		switch (edgeType) {
			case 'default':
			case 'simplebezier':
				return getBezierPath(withPositions);
			case 'straight':
				return getStraightPath(common);
			case 'step':
				return getSmoothStepPath({ ...withPositions, borderRadius: 0 });
			case 'smoothstep':
			default:
				return getSmoothStepPath(withPositions);
		}
	});
</script>

<!-- Outer line (slate) -->
<path
	d={pathData[0]}
	style="stroke: rgb(100, 116, 139); stroke-width: 6px; fill: none;"
	marker-end={markerEnd}
	marker-start={markerStart}
/>
<!-- Inner line (color based on lifetime status) -->
<path d={pathData[0]} style="stroke: {innerStrokeColor}; stroke-width: 3px; fill: none;" />
