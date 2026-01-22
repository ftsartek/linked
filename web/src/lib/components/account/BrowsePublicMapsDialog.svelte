<script lang="ts">
	import { Dialog, Portal, Progress, useDialog } from '@skeletonlabs/skeleton-svelte';
	import { ChevronLeft, ChevronRight } from 'lucide-svelte';
	import { apiClient } from '$lib/client/client';
	import type { components } from '$lib/client/schema';

	type PublicMapInfo = components['schemas']['PublicMapInfo'];

	interface Props {
		onSubscriptionChange?: () => void;
	}

	let { onSubscriptionChange }: Props = $props();

	let publicMaps = $state<PublicMapInfo[]>([]);
	let totalPublicMaps = $state(0);
	let searchingPublic = $state(false);
	let searchQuery = $state('');

	const PAGE_SIZE = 10;
	let currentPage = $state(1);
	let totalPages = $derived(Math.ceil(totalPublicMaps / PAGE_SIZE));

	const dialog = useDialog({ id: 'browse-public-maps-dialog' });

	export function open() {
		dialog().setOpen(true);
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
			const { data } = await apiClient.GET('/maps/public/search', {
				params: { query: { q: searchQuery, limit: PAGE_SIZE, offset } }
			});
			publicMaps = data?.maps ?? [];
			totalPublicMaps = data?.total ?? 0;
		} else {
			const { data } = await apiClient.GET('/maps/public', {
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

	async function toggleSubscription(map: PublicMapInfo) {
		if (map.is_subscribed) {
			const { error: apiError } = await apiClient.DELETE('/maps/{map_id}/subscribe', {
				params: { path: { map_id: map.id } }
			});
			if (!apiError) {
				map.is_subscribed = false;
				map.subscription_count--;
				onSubscriptionChange?.();
			}
		} else {
			const { error: apiError } = await apiClient.POST('/maps/{map_id}/subscribe', {
				params: { path: { map_id: map.id } }
			});
			if (!apiError) {
				map.is_subscribed = true;
				map.subscription_count++;
				onSubscriptionChange?.();
			}
		}
	}

	$effect(() => {
		if (dialog().open) {
			searchQuery = '';
			loadPublicMaps(true);
		}
	});
</script>

<Dialog.Provider value={dialog}>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-4">
			<Dialog.Content
				class="flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-lg bg-black/50 p-6 shadow-xl backdrop-blur-sm"
			>
				<Dialog.Title class="mb-4 text-xl font-bold">Browse Public Maps</Dialog.Title>

				<!-- Search Input -->
				<div class="mb-4">
					<input
						type="text"
						bind:value={searchQuery}
						oninput={handleSearch}
						placeholder="Search maps by name or description..."
						class="w-full rounded-lg border-2 border-primary-950 bg-black px-3 py-2 focus:border-primary-800 focus:outline-none"
					/>
				</div>

				<!-- Results -->
				<div class="relative flex-1 overflow-auto">
					{#if searchingPublic}
						<div class="absolute top-0 right-0 left-0 z-10">
							<Progress value={null} class="h-1 w-full rounded-none">
								<Progress.Track class="h-1 rounded-none bg-transparent">
									<Progress.Range class="h-1 rounded-none bg-primary-500" />
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
									<button
										onclick={() => toggleSubscription(map)}
										class="btn btn-sm {map.is_subscribed
											? 'preset-outlined-error-500'
											: 'preset-filled-primary-500'}"
									>
										{map.is_subscribed ? 'Unsubscribe' : 'Subscribe'}
									</button>
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
					<Dialog.CloseTrigger class="btn preset-outlined-surface-500">Close</Dialog.CloseTrigger>
				</div>
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog.Provider>
