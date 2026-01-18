<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { Dialog, Portal, Progress, useDialog } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import { user } from '$lib/stores/user';
	import SignatureCard from '$lib/components/system/SignatureCard.svelte';
	import RouteCard from '$lib/components/system/RouteCard.svelte';
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
	let subscribedMaps = $state<MapInfo[]>([]);
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

		const [owned, shared, alliance, corporation, subscribed, prefs] = await Promise.all([
			apiClient.GET('/maps/owned'),
			apiClient.GET('/maps/shared'),
			apiClient.GET('/maps/alliance'),
			apiClient.GET('/maps/corporation'),
			apiClient.GET('/maps/subscribed'),
			apiClient.GET('/users/preferences')
		]);

		if (owned.error || shared.error || alliance.error || corporation.error || subscribed.error) {
			error = 'Failed to load maps';
			loading = false;
			return;
		}

		ownedMaps = owned.data?.maps ?? [];
		sharedMaps = shared.data?.maps ?? [];
		allianceMaps = alliance.data?.maps ?? [];
		corporationMaps = corporation.data?.maps ?? [];
		subscribedMaps = subscribed.data?.maps ?? [];
		loading = false;

		// Auto-redirect to saved map if no map is currently selected
		if (!currentMapId && prefs.data?.selected_map_id) {
			const savedMapId = prefs.data.selected_map_id;
			// Verify the saved map is still accessible
			const allMaps = [
				...ownedMaps,
				...sharedMaps,
				...allianceMaps,
				...corporationMaps,
				...subscribedMaps
			];
			const mapExists = allMaps.some((m) => m.id === savedMapId);
			if (mapExists) {
				goto(resolve(`/maps/${savedMapId}`));
			}
		}
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
				is_public: newMapIsPublic,
				public_read_only: true,
				edge_type: 'default',
				rankdir: 'TB',
				auto_layout: false,
				node_sep: 100,
				rank_sep: 60
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

<div
	class="flex min-h-[calc(100vh-64px)] w-full flex-col p-2 xl:aspect-[4/3] xl:max-h-[calc(100vh-64px)] xl:min-h-0"
>
	<!-- Tab Bar (full width) -->
	<div class="flex flex-wrap items-center gap-1 p-2">
		{#if loading}
			<div class="size-8 pt-1">
				<Progress value={null} class="w-fit">
					<Progress.Circle class="[--size:--spacing(6)]">
						<Progress.CircleTrack />
						<Progress.CircleRange />
					</Progress.Circle>
				</Progress>
			</div>
		{:else if error}
			<span class="text-xs text-error-500">{error}</span>
		{:else}
			{#each ownedMaps as map (map.id)}
				<a
					href={resolve(`/maps/${map.id}`)}
					class="btn btn-sm {currentMapId === map.id
						? 'preset-filled-primary-500'
						: 'preset-tonal-primary'}"
				>
					{map.name}
				</a>
			{/each}
			{#each sharedMaps as map (map.id)}
				<a
					href={resolve(`/maps/${map.id}`)}
					class="btn btn-sm {currentMapId === map.id
						? 'preset-filled-secondary-500'
						: 'preset-tonal-secondary'}"
				>
					{map.name}
				</a>
			{/each}
			{#each corporationMaps as map (map.id)}
				<a
					href={resolve(`/maps/${map.id}`)}
					class="btn btn-sm {currentMapId === map.id
						? 'preset-filled-tertiary-500'
						: 'preset-tonal-tertiary'}"
				>
					{map.name}
				</a>
			{/each}
			{#each allianceMaps as map (map.id)}
				<a
					href={resolve(`/maps/${map.id}`)}
					class="btn btn-sm {currentMapId === map.id
						? 'preset-filled-surface-500'
						: 'preset-tonal-surface'}"
				>
					{map.name}
				</a>
			{/each}
			{#each subscribedMaps as map (map.id)}
				<a
					href={resolve(`/maps/${map.id}`)}
					class="btn btn-sm {currentMapId === map.id
						? 'preset-filled-success-500'
						: 'preset-tonal-success'}"
				>
					{map.name}
				</a>
			{/each}
		{/if}

		<!-- New Map Button -->
		<Dialog.Provider value={createMapDialog}>
			<Dialog.Trigger class="btn preset-outlined-primary-500 btn-sm">+ New</Dialog.Trigger>
			<Portal>
				<Dialog.Backdrop class="fixed inset-0 z-50 bg-surface-950/80" />
				<Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-4">
					<Dialog.Content class="w-full max-w-md rounded-lg bg-surface-800 p-6 shadow-xl">
						<Dialog.Title class="mb-4 text-xl font-bold">Create New Map</Dialog.Title>
						<form
							onsubmit={async (e) => {
								e.preventDefault();
								await handleCreateMap();
							}}
							class="space-y-4"
						>
							<div>
								<label for="map-name" class="mb-1 block text-sm font-medium text-surface-300">
									Name
								</label>
								<input
									id="map-name"
									type="text"
									bind:value={newMapName}
									class="w-full rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-white placeholder-surface-400 focus:border-primary-500 focus:outline-none"
									placeholder="My Map"
									required
								/>
							</div>
							<div>
								<label
									for="map-description"
									class="mb-1 block text-sm font-medium text-surface-300"
								>
									Description
								</label>
								<textarea
									id="map-description"
									bind:value={newMapDescription}
									class="w-full resize-none rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-white placeholder-surface-400 focus:border-primary-500 focus:outline-none"
									placeholder="Optional description..."
									rows="3"
								></textarea>
							</div>
							<div class="flex items-center gap-2">
								<input
									id="map-public"
									type="checkbox"
									bind:checked={newMapIsPublic}
									class="h-4 w-4 rounded border-surface-600 bg-surface-700"
								/>
								<label for="map-public" class="text-sm text-surface-300"> Public map </label>
							</div>
							{#if createError}
								<div class="rounded-lg bg-error-500/20 p-3 text-sm text-error-500">
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

	<!-- Main content area -->
	<div
		class="grid min-h-0 flex-1 grid-cols-1 gap-4 p-2 pt-0 md:grid-cols-2 xl:grid-cols-4 xl:grid-rows-2"
	>
		<!-- Map Area: full width on small/medium, 3/4 width on XL -->
		<main class="min-h-64 md:col-span-2 xl:col-span-3 xl:row-span-2">
			{@render children()}
		</main>

		<!-- Signature Card: full width on small, half width on medium, 1/4 width sidebar on XL -->
		<div class="md:col-span-1 xl:row-span-1">
			<SignatureCard />
		</div>

		<!-- Route Card: row 2, XL screens only -->
		<div class="hidden xl:col-span-1 xl:row-span-1 xl:block">
			<RouteCard />
		</div>
	</div>
</div>
