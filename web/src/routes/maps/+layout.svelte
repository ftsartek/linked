<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { Dialog, Portal, Progress, useDialog } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import { user } from '$lib/stores/user';
	import type { components } from '$lib/client/schema';
	import type { Snippet } from 'svelte';

	type MapInfo = components['schemas']['MapInfo'];

	interface Props {
		children: Snippet;
	}

	let { children }: Props = $props();

	let ownedMaps = $state<MapInfo[]>([]);
	let sharedMaps = $state<MapInfo[]>([]);
	let allianceMaps = $state<MapInfo[]>([]);
	let corporationMaps = $state<MapInfo[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// New map form state
	let newMapName = $state('');
	let newMapDescription = $state('');
	let newMapIsPublic = $state(false);
	let creating = $state(false);
	let createError = $state<string | null>(null);

	// Dialog control
	const createMapDialog = useDialog({ id: 'create-map-dialog' });

	let currentMapId = $derived(page.params.map_id);

	$effect(() => {
		if ($user === null) {
			goto(resolve('/'));
		}
	});

	async function loadMaps() {
		loading = true;
		error = null;

		const [owned, shared, alliance, corporation] = await Promise.all([
			apiClient.GET('/maps/owned'),
			apiClient.GET('/maps/shared'),
			apiClient.GET('/maps/alliance'),
			apiClient.GET('/maps/corporation')
		]);

		if (owned.error || shared.error || alliance.error || corporation.error) {
			error = 'Failed to load maps';
			loading = false;
			return;
		}

		ownedMaps = owned.data?.maps ?? [];
		sharedMaps = shared.data?.maps ?? [];
		allianceMaps = alliance.data?.maps ?? [];
		corporationMaps = corporation.data?.maps ?? [];
		loading = false;
	}

	$effect(() => {
		if ($user) {
			loadMaps();
		}
	});

	async function handleCreateMap() {
		if (!newMapName.trim()) {
			createError = 'Name is required';
			return;
		}

		creating = true;
		createError = null;

		const { data, error: apiError } = await apiClient.POST('/maps', {
			body: {
				name: newMapName.trim(),
				description: newMapDescription.trim() || null,
				is_public: newMapIsPublic
			}
		});

		if (apiError) {
			createError = 'detail' in apiError ? apiError.detail : 'Failed to create map';
			creating = false;
			return;
		}

		// Reset form
		newMapName = '';
		newMapDescription = '';
		newMapIsPublic = false;
		creating = false;

		// Close dialog and refresh maps
		createMapDialog().setOpen(false);
		await loadMaps();

		// Navigate to the new map
		if (data) {
			goto(resolve(`/maps/${data.id}`));
		}
	}
</script>

<div class="grid grid-cols-4 grid-rows-2 h-[calc(100vh-64px)] gap-2 p-2">
	<!-- Map Area: spans 2 rows, 3 columns -->
	<div class="col-span-3 row-span-2 flex flex-col">
		<!-- Tab Bar -->
		<div class="flex items-center gap-1 p-2 flex-wrap">
			{#if loading}
				<Progress value={null} class="items-center w-fit">
					<Progress.Circle>
						<Progress.CircleTrack />
						<Progress.CircleRange />
					</Progress.Circle>
				</Progress>
			{:else if error}
				<span class="text-error-500 text-xs">{error}</span>
			{:else}
				{#each ownedMaps as map (map.id)}
					<a
						href={resolve(`/maps/${map.id}`)}
						class="btn btn-sm {currentMapId === map.id ? 'preset-filled-primary-500' : 'preset-tonal-primary'}"
					>
						{map.name}
					</a>
				{/each}
				{#each sharedMaps as map (map.id)}
					<a
						href={resolve(`/maps/${map.id}`)}
						class="btn btn-sm {currentMapId === map.id ? 'preset-filled-secondary-500' : 'preset-tonal-secondary'}"
					>
						{map.name}
					</a>
				{/each}
				{#each corporationMaps as map (map.id)}
					<a
						href={resolve(`/maps/${map.id}`)}
						class="btn btn-sm {currentMapId === map.id ? 'preset-filled-tertiary-500' : 'preset-tonal-tertiary'}"
					>
						{map.name}
					</a>
				{/each}
				{#each allianceMaps as map (map.id)}
					<a
						href={resolve(`/maps/${map.id}`)}
						class="btn btn-sm {currentMapId === map.id ? 'preset-filled-surface-500' : 'preset-tonal-surface'}"
					>
						{map.name}
					</a>
				{/each}
			{/if}

			<!-- New Map Button -->
			<Dialog.Provider value={createMapDialog}>
				<Dialog.Trigger class="btn btn-sm preset-outlined-primary-500">
					+ New
				</Dialog.Trigger>
				<Portal>
					<Dialog.Backdrop class="fixed inset-0 z-50 bg-surface-950/80" />
					<Dialog.Positioner class="fixed inset-0 z-50 flex justify-center items-center p-4">
						<Dialog.Content class="bg-surface-800 rounded-lg w-full max-w-md p-6 shadow-xl">
							<Dialog.Title class="text-xl font-bold mb-4">Create New Map</Dialog.Title>
							<form
								onsubmit={async (e) => {
									e.preventDefault();
									await handleCreateMap();
								}}
								class="space-y-4"
							>
								<div>
									<label for="map-name" class="block text-sm font-medium text-surface-300 mb-1">
										Name
									</label>
									<input
										id="map-name"
										type="text"
										bind:value={newMapName}
										class="w-full px-3 py-2 bg-surface-700 border border-surface-600 rounded-lg text-white placeholder-surface-400 focus:outline-none focus:border-primary-500"
										placeholder="My Map"
										required
									/>
								</div>
								<div>
									<label for="map-description" class="block text-sm font-medium text-surface-300 mb-1">
										Description
									</label>
									<textarea
										id="map-description"
										bind:value={newMapDescription}
										class="w-full px-3 py-2 bg-surface-700 border border-surface-600 rounded-lg text-white placeholder-surface-400 focus:outline-none focus:border-primary-500 resize-none"
										placeholder="Optional description..."
										rows="3"
									></textarea>
								</div>
								<div class="flex items-center gap-2">
									<input
										id="map-public"
										type="checkbox"
										bind:checked={newMapIsPublic}
										class="w-4 h-4 rounded bg-surface-700 border-surface-600"
									/>
									<label for="map-public" class="text-sm text-surface-300">
										Public map
									</label>
								</div>
								{#if createError}
									<div class="p-3 rounded-lg bg-error-500/20 text-error-500 text-sm">
										{createError}
									</div>
								{/if}
								<div class="flex justify-end gap-3 pt-2">
									<Dialog.CloseTrigger class="btn preset-outlined-surface-500">
										Cancel
									</Dialog.CloseTrigger>
									<button type="submit" class="btn preset-filled-primary-500" disabled={creating}>
										{creating ? 'Creating...' : 'Create'}
									</button>
								</div>
							</form>
						</Dialog.Content>
					</Dialog.Positioner>
				</Portal>
			</Dialog.Provider>
		</div>

		<!-- Map Content -->
		<main class="flex-1 p-2">
			{@render children()}
		</main>
	</div>

	<!-- Column 4: Reserved for future use -->
	<div class="col-span-1 row-span-2"></div>
</div>
