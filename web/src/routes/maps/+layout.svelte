<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { Dialog, Portal, Progress, useDialog } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import { user } from '$lib/stores/user';
	import SignatureCard from '$lib/components/system/SignatureCard.svelte';
	import RouteCard from '$lib/components/system/RouteCard.svelte';
	import NotesCard from '$lib/components/system/NotesCard.svelte';
	import SystemDetailsCard from '$lib/components/system/SystemDetailsCard.svelte';
	import CharacterLocationsCard from '$lib/components/system/CharacterLocationsCard.svelte';
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
				rank_sep: 60,
				location_tracking_enabled: false
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

<div class="flex min-h-[calc(100vh-64px)] w-full flex-col gap-2 p-2">
	<!-- Tab Bar (full width, fixed height to prevent jump) -->
	<div class="flex h-12 flex-col overflow-hidden rounded-xl bg-black/75 backdrop-blur-2xl">
		{#if loading}
			<Progress value={null} class="h-1 w-full shrink-0">
				<Progress.Track class="bg-transparent">
					<Progress.Range class="bg-primary-500" />
				</Progress.Track>
			</Progress>
		{/if}
		<div
			class="flex flex-1 flex-wrap items-center gap-1 px-2"
			class:pt-2={!loading}
			class:pb-2={true}
		>
			{#if error}
				<span class="text-xs text-error-500">{error}</span>
			{:else if !loading}
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

			<!-- New Map Button (only show if user can create maps) -->
			{#if $user?.can_create_maps}
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
			{/if}
		</div>
	</div>

	<!--
		Responsive Layout using CSS Grid with named areas

		5 Layouts based on screen size + aspect ratio:
		1. Mobile (<640px): stacked vertically
		2. Small/Tablet Portrait (640-1279px, portrait): map top, 2-col cards
		3. Small/Tablet Landscape (640-1279px, landscape): map+sigs top, 3-col cards below
		4. Large Desktop Portrait (>=1280px, portrait): map top, 2x2 card grid
		5. Large Desktop Landscape (>=1280px, landscape): map left, sidebar right, extras below
	-->
	<div class="responsive-layout gap-2">
		<!-- Map Area -->
		<main class="min-h-0 [grid-area:map]">
			{@render children()}
		</main>

		<!-- Signatures Card -->
		<div class="min-h-0 [grid-area:sigs]">
			<SignatureCard />
		</div>

		<!-- Notes Card -->
		<div class="min-h-0 [grid-area:notes]">
			<NotesCard />
		</div>

		<!-- System Details Card -->
		<div class="min-h-0 [grid-area:sys]">
			<SystemDetailsCard />
		</div>

		<!-- Routes Card -->
		<div class="min-h-0 [grid-area:routes]">
			<RouteCard />
		</div>

		<!-- Character Locations Card -->
		<div class="min-h-0 [grid-area:locs]">
			<CharacterLocationsCard />
		</div>
	</div>
</div>

<style>
	.responsive-layout {
		display: grid;
		width: 100%;
	}

	/* Card height for portrait modes - fixed height with internal scroll */
	:global(.card-fixed-height) {
		height: 280px;
	}

	/* 1. Mobile (<640px): stacked vertically */
	/* Map fills most of viewport, cards stack below with scroll */
	@media (max-width: 639px) {
		.responsive-layout {
			grid-template-areas:
				'map'
				'sigs'
				'notes'
				'sys'
				'routes'
				'locs';
			grid-template-columns: 1fr;
			grid-template-rows: 60vh repeat(5, auto);
		}
	}

	/* 2. Small/Tablet Portrait (640-1279px, portrait aspect) */
	/* Map on top, cards in rows, locs half-width at bottom */
	@media (min-width: 640px) and (max-width: 1279px) and (max-aspect-ratio: 4/3) {
		.responsive-layout {
			grid-template-areas:
				'map map'
				'sigs sys'
				'notes routes'
				'locs .';
			grid-template-columns: 1fr 1fr;
			grid-template-rows: 55vh 320px 320px 320px;
		}
	}

	/* 3. Small/Tablet Landscape (640-1279px, landscape aspect) */
	/* Map + Sigs/Notes on top, Sys + Routes + Locs bottom row */
	@media (min-width: 640px) and (max-width: 1279px) and (min-aspect-ratio: 4/3) {
		.responsive-layout {
			grid-template-areas:
				'map map map sigs'
				'map map map notes'
				'sys routes locs .';
			grid-template-columns: 1fr 1fr 1fr 1fr;
			grid-template-rows:
				calc((100vh - 120px) / 2)
				calc((100vh - 120px) / 2)
				auto;
		}
	}

	/* 4. Large Desktop Portrait (>=1280px, portrait aspect) */
	/* Map on top, cards in 2x2 grid, locs half-width at bottom */
	@media (min-width: 1280px) and (max-aspect-ratio: 4/3) {
		.responsive-layout {
			grid-template-areas:
				'map map'
				'sigs notes'
				'sys routes'
				'locs .';
			grid-template-columns: 1fr 1fr;
			grid-template-rows: 55vh 320px 320px 320px;
		}
	}

	/* 5. Large Desktop Landscape (>=1280px, landscape aspect) */
	/* Map + Sigs/Notes on right, Sys + Routes + Locs bottom row */
	@media (min-width: 1280px) and (min-aspect-ratio: 4/3) {
		.responsive-layout {
			grid-template-areas:
				'map map map sigs'
				'map map map notes'
				'sys routes locs .';
			grid-template-columns: 1fr 1fr 1fr 1fr;
			grid-template-rows:
				calc((100vh - 120px) / 2)
				calc((100vh - 120px) / 2)
				auto;
		}
	}
</style>
