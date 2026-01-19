<script lang="ts">
	import { mapSelection } from '$lib/stores/mapSelection';
	import {
		classColour,
		secStatusColour,
		effectColour,
		shouldShowSecStatus
	} from '$lib/helpers/renderClass';
	import { apiClient } from '$lib/client/client';
	import type { components } from '$lib/client/schema';

	type SystemDetails = components['schemas']['GetSystemDetailsSystemDetailsResponseBody'];

	let systemDetails: SystemDetails | null = $state(null);
	let loading = $state(false);

	// Fetch system details when selection changes
	$effect(() => {
		const node = $mapSelection.selectedNode;
		if (node && node.system_id > 0) {
			loading = true;
			apiClient
				.GET('/universe/systems/{system_id}/details', {
					params: { path: { system_id: node.system_id } }
				})
				.then((res) => {
					systemDetails = res.data ?? null;
					loading = false;
				})
				.catch(() => {
					systemDetails = null;
					loading = false;
				});
		} else {
			systemDetails = null;
		}
	});

	// Determine if a system is w-space (has statics, wormhole effects, etc.)
	function isWspace(className: string | null | undefined): boolean {
		if (!className) return false;
		return !['HS', 'LS', 'NS', 'Pochven'].includes(className);
	}

	// Convert radius from meters to AU (1 AU = 149,597,870,700 meters)
	function radiusToAU(radiusMeters: number | null | undefined): string {
		if (!radiusMeters) return '-';
		const au = radiusMeters / 149_597_870_700;
		return au.toFixed(2) + ' AU';
	}
</script>

<div class="flex min-h-48 w-72 flex-col rounded-xl border-0 bg-black/75 backdrop-blur-2xl">
	<!-- Header -->
	<div
		class="flex w-full flex-row items-center justify-between border-b-2 border-primary-950/50 px-3 py-2"
	>
		<h3 class="text-sm font-semibold text-white">System Details</h3>
		{#if $mapSelection.selectedNode}
			<p class="text-sm font-semibold text-surface-400">
				{$mapSelection.selectedNode.system_name}
			</p>
		{/if}
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-auto p-3">
		{#if !$mapSelection.selectedNode}
			<div class="flex h-full items-center justify-center">
				<p class="text-sm text-surface-400">Select a node to view details</p>
			</div>
		{:else}
			{@const node = $mapSelection.selectedNode}
			{@const wspace = isWspace(node.class_name)}
			<div class="flex flex-col gap-2 text-sm">
				<!-- Class -->
				<div class="flex items-center justify-between">
					<span class="text-surface-400">Class</span>
					<span class={classColour(node.class_name ?? 'Unknown')}>
						{node.class_name ?? 'Unknown'}
					</span>
				</div>

				<!-- Security Status (k-space only) -->
				{#if node.class_name && shouldShowSecStatus(node.class_name)}
					<div class="flex items-center justify-between">
						<span class="text-surface-400">Security</span>
						<span class={secStatusColour(node.security_status)}>
							{node.security_status?.toFixed(2) ?? '-'}
						</span>
					</div>
				{/if}

				<!-- Constellation -->
				{#if node.constellation_name}
					<div class="flex items-center justify-between">
						<span class="text-surface-400">Constellation</span>
						<span class="text-surface-200">{node.constellation_name}</span>
					</div>
				{/if}

				<!-- Region -->
				{#if node.region_name}
					<div class="flex items-center justify-between">
						<span class="text-surface-400">Region</span>
						<span class="text-surface-200">{node.region_name}</span>
					</div>
				{/if}

				<!-- Wormhole Effect (w-space only) -->
				{#if wspace && node.wh_effect_name}
					<div class="flex items-center justify-between">
						<span class="text-surface-400">Effect</span>
						<span class={effectColour(node.wh_effect_name)}>
							{node.wh_effect_name}
						</span>
					</div>
				{/if}

				<!-- Statics (w-space only) -->
				{#if wspace && node.statics && node.statics.length > 0}
					<div class="flex items-start justify-between">
						<span class="text-surface-400">Statics</span>
						<div class="flex flex-col items-end gap-1">
							{#each node.statics as static_info (static_info.code)}
								<span class="text-surface-200">
									<span class="font-mono text-purple-300">{static_info.code}</span>
									{#if static_info.target_class_name}
										<span class="text-surface-500">→</span>
										<span class={classColour(static_info.target_class_name)}>
											{static_info.target_class_name}
										</span>
									{/if}
								</span>
							{/each}
						</div>
					</div>
				{/if}

				<!-- System Details from API -->
				{#if loading}
					<div class="text-xs text-surface-500">Loading...</div>
				{:else if systemDetails}
					<!-- System Size -->
					<div class="flex items-center justify-between">
						<span class="text-surface-400">Size</span>
						<span class="text-surface-200">{radiusToAU(systemDetails.radius)}</span>
					</div>

					<!-- Planets & Moons -->
					<div class="flex items-center justify-between">
						<span class="text-surface-400">Planets</span>
						<span class="text-surface-200">
							{systemDetails.planet_count}
							{#if systemDetails.moon_count > 0}
								<span class="text-surface-500">
									({systemDetails.moon_count} moons)
								</span>
							{/if}
						</span>
					</div>

					<!-- Stations -->
					{#if systemDetails.station_count > 0}
						<div class="flex items-center justify-between">
							<span class="text-surface-400">Stations</span>
							<span class="text-surface-200">{systemDetails.station_count}</span>
						</div>
					{/if}

					<!-- Neighbours (k-space only, via stargates) -->
					{#if systemDetails.neighbours.length > 0}
						<div class="flex items-start justify-between">
							<span class="text-surface-400">Neighbours</span>
							<div class="flex flex-col items-end gap-0.5">
								{#each systemDetails.neighbours as neighbour (neighbour.id)}
									<span class="text-xs">
										<span class="text-surface-200">{neighbour.name}</span>
										{#if neighbour.security_status != null}
											<span class={secStatusColour(neighbour.security_status)}>
												{neighbour.security_status.toFixed(1)}
											</span>
										{/if}
									</span>
								{/each}
							</div>
						</div>
					{/if}
				{/if}
			</div>
		{/if}
	</div>
</div>
