<script lang="ts">
	import { onMount } from 'svelte';
	import { Progress } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import SystemTree from '$lib/components/reference/SystemTree.svelte';
	import SystemFilter, { type SystemFilters } from '$lib/components/reference/SystemFilter.svelte';
	import type { WormholeSystemsGrouped } from '$lib/components/reference/wormholeConstants';

	let loading = $state(true);
	let data = $state<WormholeSystemsGrouped | null>(null);

	// Filter options extracted from data
	let effects = $state<{ id: number; name: string }[]>([]);

	// Current filter state
	let filters = $state<SystemFilters>({
		classes: [],
		effect: null,
		staticClass: null,
		shattered: null
	});

	async function fetchSystems() {
		loading = true;

		const queryParams: {
			class?: number[];
			effect?: number;
			static?: number;
			shattered?: boolean;
		} = {};

		if (filters.classes.length > 0) {
			queryParams.class = filters.classes;
		}
		if (filters.effect !== null) {
			queryParams.effect = filters.effect;
		}
		if (filters.staticClass !== null) {
			queryParams.static = filters.staticClass;
		}
		if (filters.shattered !== null) {
			queryParams.shattered = filters.shattered;
		}

		const response = await apiClient.GET('/reference/systems', {
			params: { query: queryParams }
		});

		if (response.data) {
			data = response.data;
		}
		loading = false;
	}

	function extractEffects(systemsData: WormholeSystemsGrouped): { id: number; name: string }[] {
		const effectMap: Record<number, string> = {};
		for (const region of systemsData.regions) {
			for (const constellation of region.constellations) {
				for (const system of constellation.systems) {
					if (system.effect_id != null && system.effect_name != null) {
						effectMap[system.effect_id] = system.effect_name;
					}
				}
			}
		}
		return Object.entries(effectMap)
			.map(([id, name]) => ({ id: parseInt(id, 10), name }))
			.sort((a, b) => a.name.localeCompare(b.name));
	}

	onMount(async () => {
		const response = await apiClient.GET('/reference/systems');

		if (response.data) {
			data = response.data;
			effects = extractEffects(response.data);
		}

		loading = false;
	});

	function handleFilter(newFilters: SystemFilters) {
		filters = newFilters;
		fetchSystems();
	}
</script>

<main class="min-h-screen p-6">
	<div class="mx-auto max-w-[1600px]">
		<section class="rounded-xl bg-black/75 p-6 backdrop-blur-2xl">
			<h1 class="mb-2 text-2xl font-bold">Wormhole Systems Reference</h1>
			<p class="mb-6 text-surface-400">
				A hierarchical view of all wormhole systems organized by region and constellation, showing
				statics and effects.
			</p>

			<SystemFilter {effects} onfilter={handleFilter} />

			{#if loading}
				<Progress value={null} />
			{:else if data}
				<p class="mb-4 text-sm text-surface-500">
					Showing {data.total_systems} wormhole systems
				</p>
				<SystemTree regions={data.regions} />
			{/if}
		</section>
	</div>
</main>
