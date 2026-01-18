<script lang="ts">
	import { Progress, Switch } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import { mapSelection } from '$lib/stores/mapSelection';
	import { classBgColour, secStatusBgColour } from '$lib/helpers/renderClass';
	import type { components } from '$lib/client/schema';

	type RouteResponse = components['schemas']['RouteResponse'];

	interface TradeHub {
		id: number;
		name: string;
	}

	const TRADE_HUBS: TradeHub[] = [
		{ id: 30000142, name: 'Jita' },
		{ id: 30002187, name: 'Amarr' },
		{ id: 30002510, name: 'Rens' },
		{ id: 30002053, name: 'Hek' },
		{ id: 30002659, name: 'Dodixie' }
	];

	interface RouteResult {
		hub: TradeHub;
		route: RouteResponse | null;
		error: boolean;
	}

	let routes = $state<RouteResult[]>([]);
	let loading = $state(false);
	let loaded = $state(false);
	let preferSafer = $state(false);

	// Track the last loaded node to reset when selection changes
	let lastLoadedNodeId: string | null = null;

	// Reset loaded state when node changes
	$effect(() => {
		const nodeId = $mapSelection.selectedNode?.id;
		if (nodeId !== lastLoadedNodeId) {
			loaded = false;
			routes = [];
			lastLoadedNodeId = nodeId ?? null;
		}
	});

	function handlePreferSaferChange(e: { checked: boolean }) {
		preferSafer = e.checked;
		if (loaded && !loading) {
			loadRoutes();
		}
	}

	async function loadRoutes() {
		const state = $mapSelection;
		const nodeId = state.selectedNode?.id;
		const mapId = state.mapId;

		if (!nodeId || !mapId) return;

		loading = true;

		const routeType = preferSafer ? 'secure' : 'shortest';

		const results = await Promise.all(
			TRADE_HUBS.map(async (hub) => {
				const { data, error: apiError } = await apiClient.GET('/routes/{map_id}', {
					params: {
						path: { map_id: mapId },
						query: {
							origin: nodeId,
							destination: hub.id,
							route_type: routeType
						}
					}
				});

				if (apiError) {
					// 404 means no route found, not an error
					if ('status_code' in apiError && apiError.status_code === 404) {
						return { hub, route: null, error: false };
					}
					return { hub, route: null, error: true };
				}

				return { hub, route: data ?? null, error: false };
			})
		);

		// Sort by jump count (routes with no path go to the end)
		routes = results.sort((a, b) => {
			if (!a.route && !b.route) return 0;
			if (!a.route) return 1;
			if (!b.route) return -1;
			return a.route.total_jumps - b.route.total_jumps;
		});

		loading = false;
		loaded = true;
	}

	function isWormholeSystem(className: string | null | undefined): boolean {
		if (!className) return false;
		return !['HS', 'LS', 'NS'].includes(className);
	}
</script>

<div class="flex h-full min-h-48 flex-col rounded-xl border-0 bg-black/75 backdrop-blur-2xl">
	<!-- Header -->
	<div class="flex w-full flex-col border-b-2 border-primary-950/50">
		<div class="flex flex-row items-center justify-between px-3 py-2">
			<h3 class="text-sm font-semibold text-white">Routes</h3>
			<div class="flex items-center gap-2">
				<span class="text-xs text-surface-400">Prefer Safer</span>
				<Switch
					name="prefer-safer"
					checked={preferSafer}
					onCheckedChange={(e) => handlePreferSaferChange(e)}
				>
					<Switch.Control>
						<Switch.Thumb />
					</Switch.Control>
					<Switch.HiddenInput />
				</Switch>
			</div>
		</div>
		{#if loading}
			<Progress value={null} class="h-1 w-full">
				<Progress.Track class="bg-surface-800">
					<Progress.Range class="bg-primary-500" />
				</Progress.Track>
			</Progress>
		{/if}
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-auto p-2">
		{#if !$mapSelection.selectedNode}
			<div class="flex h-full items-center justify-center">
				<p class="text-sm text-surface-400">Select a node to view routes</p>
			</div>
		{:else if !loaded && !loading}
			<div class="flex h-full items-center justify-center">
				<button
					type="button"
					onclick={loadRoutes}
					class="rounded-lg border border-primary-500 px-4 py-2 text-sm font-medium text-primary-500 hover:bg-primary-500/10"
				>
					Load Routes
				</button>
			</div>
		{:else if loading}
			<div class="flex h-full items-center justify-center">
				<p class="text-sm text-surface-400">Loading routes...</p>
			</div>
		{:else if loaded}
			<div class="flex flex-col gap-2">
				{#each routes as { hub, route, error } (hub.id)}
					{@const destination = route?.waypoints[route.waypoints.length - 1]}
					<div class="flex flex-col gap-1">
						<!-- Top row: destination info and jump count -->
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-1.5">
								<span class="text-xs font-medium text-surface-200">{hub.name}</span>
								{#if destination}
									<span class="text-xs text-surface-500">
										{destination.class_name}
										{#if destination.security_status != null}
											{destination.security_status.toFixed(1)}
										{/if}
									</span>
								{/if}
							</div>
							{#if error}
								<span class="text-xs text-error-500">Error</span>
							{:else if !route}
								<span class="text-xs text-surface-500">No route</span>
							{:else if route.total_jumps === 0}
								<span class="text-xs text-success-400">Here</span>
							{:else}
								<span class="text-xs font-medium text-surface-400">{route.total_jumps} Jumps</span>
							{/if}
						</div>
						<!-- Bottom row: route visualization -->
						{#if route && route.total_jumps > 0}
							<div class="flex flex-wrap items-center gap-0.5">
								{#each route.waypoints as waypoint, index (index)}
									{@const isWspace = isWormholeSystem(waypoint.class_name)}
									{@const prevWaypoint = index > 0 ? route.waypoints[index - 1] : null}
									{@const prevIsWspace = prevWaypoint
										? isWormholeSystem(prevWaypoint.class_name)
										: false}
									{@const isKspaceWormholeJump =
										waypoint.is_wormhole_jump && !isWspace && !prevIsWspace && prevWaypoint}
									<!-- Spiral icon only for k-space to k-space wormhole jumps (e.g. N944) -->
									{#if isKspaceWormholeJump}
										<img
											src="/spiral.svg"
											alt="wormhole"
											class="size-2.5 opacity-40 invert"
											title="Wormhole connection"
										/>
									{/if}
									{#if isWspace}
										<!-- Wormhole system: solid diamond -->
										<div
											class="size-2 rotate-45 {classBgColour(waypoint.class_name)}"
											title="{waypoint.system_name || 'Unknown'} ({waypoint.class_name || '?'})"
										></div>
									{:else}
										<!-- K-space system: square -->
										<div
											class="size-2.5 {secStatusBgColour(waypoint.security_status)}"
											title="{waypoint.system_name ||
												'Unknown'} ({waypoint.security_status?.toFixed(1) ?? '?'})"
										></div>
									{/if}
								{/each}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
