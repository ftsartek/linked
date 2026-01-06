<script lang="ts">
	import { apiClient } from '$lib/client/client';
	import type { components } from '$lib/client/schema';
	import { classColour } from '$lib/helpers/renderClass';

	type SystemSearchResult =
		components['schemas']['routes.universe.controller.UniverseController.search_systemsSystemSearchResponse_0SystemSearchResultResponseBody'];

	interface Props {
		onselect?: (system: SystemSearchResult) => void;
		oncancel?: () => void;
	}

	let { onselect, oncancel }: Props = $props();

	let items = $state<SystemSearchResult[]>([]);
	let loading = $state(true);
	let gridElement: HTMLDivElement | null = $state(null);

	async function loadUnidentifiedSystems() {
		loading = true;
		try {
			const { data, error } = await apiClient.GET('/universe/systems/unidentified');
			if (error) {
				console.error('Failed to load unidentified systems:', error);
				items = [];
			} else {
				items = data?.systems ?? [];
			}
		} catch (e) {
			console.error('Failed to load unidentified systems:', e);
			items = [];
		}
		loading = false;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && oncancel) {
			event.preventDefault();
			oncancel();
		}
	}

	function handleSelect(item: SystemSearchResult) {
		if (onselect) {
			onselect(item);
		}
	}

	// Load on mount and focus
	$effect(() => {
		loadUnidentifiedSystems();
	});

	$effect(() => {
		if (!loading && gridElement) {
			gridElement.focus();
		}
	});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div bind:this={gridElement} onkeydown={handleKeydown} tabindex="-1" class="outline-none">
	{#if loading}
		<div class="px-3 py-2 text-sm text-surface-400">Loading...</div>
	{:else if items.length === 0}
		<div class="px-3 py-2 text-sm text-surface-400">No classes available</div>
	{:else}
		<div class="grid grid-cols-4 gap-1 p-1">
			{#each items as item (item.id)}
				<button
					type="button"
					class="cursor-pointer rounded px-2 py-1.5 text-center text-sm font-medium hover:bg-primary-950/60 {classColour(
						item.class_name ?? 'Unknown'
					)}"
					onclick={() => handleSelect(item)}
				>
					{item.class_name ?? '?'}
				</button>
			{/each}
		</div>
	{/if}
</div>
