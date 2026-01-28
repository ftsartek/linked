<script lang="ts">
	import { Dialog, Portal, Progress, useDialog } from '@skeletonlabs/skeleton-svelte';
	import { Trash2, Plus, ChevronLeft, ChevronRight } from 'lucide-svelte';
	import { apiClient } from '$lib/client/client';
	import { toaster } from '$lib/stores/toaster';
	import type { components } from '$lib/client/schema';

	type DefaultSubscriptionInfo = components['schemas']['DefaultSubscriptionInfo'];
	type PublicMapInfo = components['schemas']['PublicMapInfo'];

	// Loading states
	let loading = $state(true);
	let searchingPublic = $state(false);

	// Data
	let defaultSubscriptions = $state<DefaultSubscriptionInfo[]>([]);

	// Add map dialog state
	let publicMaps = $state<PublicMapInfo[]>([]);
	let totalPublicMaps = $state(0);
	let searchQuery = $state('');
	const addMapDialog = useDialog({ id: 'add-default-subscription-dialog' });

	const PAGE_SIZE = 10;
	let currentPage = $state(1);
	let totalPages = $derived(Math.ceil(totalPublicMaps / PAGE_SIZE));

	async function loadDefaultSubscriptions() {
		loading = true;

		const { data, error } = await apiClient.GET('/admin/default-subscriptions');

		if (error) {
			toaster.create({
				title: 'Error',
				description: 'Failed to load default subscriptions',
				type: 'error'
			});
		} else {
			defaultSubscriptions = data?.entries ?? [];
		}

		loading = false;
	}

	$effect(() => {
		loadDefaultSubscriptions();
	});

	async function removeDefaultSubscription(mapId: string, mapName: string) {
		const { error } = await apiClient.DELETE('/admin/default-subscriptions/{map_id}', {
			params: { path: { map_id: mapId } }
		});

		if (error) {
			const message = 'detail' in error ? (error.detail as string) : 'Failed to remove';
			toaster.create({ title: 'Error', description: message, type: 'error' });
			return;
		}

		defaultSubscriptions = defaultSubscriptions.filter((s) => s.map_id !== mapId);
		toaster.create({
			title: 'Removed',
			description: `${mapName} is no longer a default subscription`,
			type: 'success'
		});
	}

	function goToPage(page: number) {
		if (page >= 1 && page <= totalPages) {
			currentPage = page;
			loadPublicMaps(false);
		}
	}

	async function loadPublicMaps(reset = true) {
		searchingPublic = true;
		if (reset) {
			currentPage = 1;
		}

		const offset = (currentPage - 1) * PAGE_SIZE;

		if (searchQuery.length >= 2) {
			const { data } = await apiClient.GET('/admin/public-maps/search', {
				params: { query: { q: searchQuery, limit: PAGE_SIZE, offset } }
			});
			publicMaps = data?.maps ?? [];
			totalPublicMaps = data?.total ?? 0;
		} else {
			const { data } = await apiClient.GET('/admin/public-maps', {
				params: { query: { limit: PAGE_SIZE, offset } }
			});
			publicMaps = data?.maps ?? [];
			totalPublicMaps = data?.total ?? 0;
		}

		searchingPublic = false;
	}

	let searchDebounce: ReturnType<typeof setTimeout>;
	function handleSearch() {
		clearTimeout(searchDebounce);
		searchDebounce = setTimeout(() => loadPublicMaps(true), 300);
	}

	async function addDefaultSubscription(map: PublicMapInfo) {
		// Check if already a default
		if (defaultSubscriptions.some((s) => s.map_id === map.id)) {
			toaster.create({
				title: 'Already Added',
				description: `${map.name} is already a default subscription`,
				type: 'warning'
			});
			return;
		}

		const { error } = await apiClient.POST('/admin/default-subscriptions', {
			body: { map_id: map.id }
		});

		if (error) {
			const message = 'detail' in error ? (error.detail as string) : 'Failed to add';
			toaster.create({ title: 'Error', description: message, type: 'error' });
			return;
		}

		defaultSubscriptions = [
			...defaultSubscriptions,
			{
				map_id: map.id,
				map_name: map.name,
				added_by: null,
				date_created: new Date().toISOString()
			}
		];
		toaster.create({
			title: 'Added',
			description: `${map.name} is now a default subscription for new users`,
			type: 'success'
		});
		addMapDialog().setOpen(false);
	}

	function isAlreadyDefault(mapId: string): boolean {
		return defaultSubscriptions.some((s) => s.map_id === mapId);
	}

	$effect(() => {
		if (addMapDialog().open) {
			searchQuery = '';
			loadPublicMaps(true);
		}
	});
</script>

<section class="relative flex h-full flex-col rounded-xl bg-black/75 p-6 backdrop-blur-2xl">
	{#if loading}
		<div class="absolute top-0 right-0 left-0 z-10">
			<Progress value={null} class="h-0.5 w-full rounded-none">
				<Progress.Track class="h-0.5 rounded-none bg-transparent">
					<Progress.Range class="h-0.5 rounded-none bg-primary-300-700" />
				</Progress.Track>
			</Progress>
		</div>
	{/if}
	<!-- Header -->
	<div class="mb-4">
		<h2 class="text-xl font-semibold">Default Subscriptions</h2>
		<p class="text-sm text-surface-400">
			Public maps that new users are automatically subscribed to on signup.
		</p>
	</div>

	{#if loading}
		<div class="flex flex-1 items-center justify-center py-8"></div>
	{:else}
		<!-- Add Button -->
		<div class="mb-4">
			<button
				onclick={() => addMapDialog().setOpen(true)}
				class="btn preset-outlined-primary-500 btn-sm"
			>
				<Plus size={16} />
				Add Public Map
			</button>
		</div>

		<!-- Default Subscriptions List -->
		<div class="flex-1 overflow-auto">
			<div class="grid gap-3">
				{#each defaultSubscriptions as sub (sub.map_id)}
					<div
						class="flex items-center gap-3 rounded-lg border-2 border-surface-900 bg-black/50 p-3"
					>
						<div class="flex-1">
							<span class="font-medium">{sub.map_name}</span>
						</div>
						<button
							onclick={() => removeDefaultSubscription(sub.map_id, sub.map_name)}
							class="btn preset-outlined-error-500 btn-sm"
							title="Remove from defaults"
						>
							<Trash2 size={16} />
						</button>
					</div>
				{:else}
					<p class="text-sm text-surface-400">No default subscriptions configured</p>
				{/each}
			</div>
		</div>
	{/if}
</section>

<!-- Add Map Dialog -->
<Dialog.Provider value={addMapDialog}>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-4">
			<Dialog.Content
				class="flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-lg bg-black/50 p-6 shadow-xl backdrop-blur-sm"
			>
				<Dialog.Title class="mb-4 text-xl font-bold">Add Default Subscription</Dialog.Title>
				<p class="mb-4 text-sm text-surface-400">
					Select a public map to automatically subscribe new users to.
				</p>

				<!-- Search Input -->
				<div class="mb-4">
					<input
						type="text"
						bind:value={searchQuery}
						oninput={handleSearch}
						placeholder="Search public maps..."
						class="w-full rounded-lg border-2 border-primary-950 bg-black px-3 py-2 focus:border-primary-800 focus:outline-none"
					/>
				</div>

				<!-- Results -->
				<div class="relative flex-1 overflow-auto">
					{#if searchingPublic}
						<div class="absolute top-0 right-0 left-0 z-10">
							<Progress value={null} class="h-0.5 w-full rounded-none">
								<Progress.Track class="h-0.5 rounded-none bg-transparent">
									<Progress.Range class="h-0.5 rounded-none bg-primary-300-700" />
								</Progress.Track>
							</Progress>
						</div>
						<div class="flex justify-center py-8"></div>
					{:else if publicMaps.length === 0}
						<div class="py-8 text-center text-surface-400">
							{searchQuery.length >= 2
								? 'No maps found matching your search.'
								: 'No public maps available.'}
						</div>
					{:else}
						<div class="grid gap-3">
							{#each publicMaps as map (map.id)}
								<div
									class="flex items-center gap-4 rounded-lg border-2 border-surface-900 bg-black/50 p-4"
								>
									<div class="flex-1">
										<div class="flex items-center gap-2">
											<span class="font-medium">{map.name}</span>
											<span class="text-xs text-surface-400">
												{map.subscription_count}
												{map.subscription_count === 1 ? 'subscriber' : 'subscribers'}
											</span>
										</div>
										{#if map.description}
											<div class="text-sm text-surface-400">{map.description}</div>
										{/if}
									</div>
									{#if isAlreadyDefault(map.id)}
										<span class="text-sm text-success-400">Already default</span>
									{:else}
										<button
											onclick={() => addDefaultSubscription(map)}
											class="btn preset-filled-primary-500 btn-sm"
										>
											Add
										</button>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<!-- Pagination -->
				{#if totalPages > 1}
					<div class="mt-4 flex items-center justify-center gap-2">
						<button
							onclick={() => goToPage(currentPage - 1)}
							class="btn preset-outlined-surface-500 btn-sm"
							disabled={currentPage === 1}
						>
							<ChevronLeft size={16} />
							Prev
						</button>
						<span class="text-sm text-surface-400">
							Page {currentPage} of {totalPages}
						</span>
						<button
							onclick={() => goToPage(currentPage + 1)}
							class="btn preset-outlined-surface-500 btn-sm"
							disabled={currentPage === totalPages}
						>
							Next
							<ChevronRight size={16} />
						</button>
					</div>
				{/if}

				<div class="mt-4 flex justify-end">
					<Dialog.CloseTrigger class="btn preset-outlined-surface-500">Cancel</Dialog.CloseTrigger>
				</div>
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog.Provider>
