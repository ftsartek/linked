<script lang="ts">
	import { Combobox, Portal } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import type { components } from '$lib/client/schema';
	import { classColour } from '$lib/helpers/renderClass';

	type WormholeSearchResult =
		components['schemas']['SearchWormholesWormholeSearchResultResponseBody'];

	interface Props {
		onselect?: (wormhole: WormholeSearchResult) => void;
		placeholder?: string;
		target_class?: number | null;
		source_class?: number | null;
		autoSearch?: boolean;
	}

	let {
		onselect,
		placeholder = 'Search wormholes...',
		target_class,
		source_class,
		autoSearch = false
	}: Props = $props();

	let items = $state<WormholeSearchResult[]>([]);
	let loading = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	let currentQuery = $state('');
	let comboboxOpen = $state(false);

	// Auto-search on mount if enabled
	$effect(() => {
		if (autoSearch) {
			searchWormholes(currentQuery);
			comboboxOpen = true;
		}
	});

	async function searchWormholes(query: string) {
		loading = true;
		const { data } = await apiClient.GET('/universe/wormholes', {
			params: {
				query: {
					q: query || undefined,
					target: target_class ?? undefined,
					source_class: source_class ?? undefined
				}
			}
		});
		items = data ?? [];
		loading = false;
	}

	function handleInputChange(details: { inputValue: string }) {
		currentQuery = details.inputValue;
		if (debounceTimer) {
			clearTimeout(debounceTimer);
		}
		debounceTimer = setTimeout(() => {
			searchWormholes(details.inputValue);
		}, 300);
	}

	function handleValueChange(details: { value: string[] }) {
		const selectedId = details.value[0];
		if (selectedId) {
			const selected = items.find((item) => String(item.id) === selectedId);
			if (selected && onselect) {
				onselect(selected);
			}
		}
	}

	function handleOpenChange(details: { open: boolean }) {
		comboboxOpen = details.open;
		if (details.open) {
			// Search immediately when opened (with current query, which may be empty)
			searchWormholes(currentQuery);
		}
	}
</script>

<Combobox
	{placeholder}
	open={comboboxOpen}
	onInputValueChange={handleInputChange}
	onValueChange={handleValueChange}
	onOpenChange={handleOpenChange}
>
	<Combobox.Control>
		<Combobox.Input
			class="w-full rounded-lg border-2 border-primary-950 bg-black px-3 py-2 text-white placeholder-surface-400 focus:border-primary-800 focus:outline-none"
		/>
		<Combobox.Trigger class="btn-icon preset-tonal-surface">
			{#if loading}
				<svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"
					></circle>
					<path
						class="opacity-75"
						fill="currentColor"
						d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
					></path>
				</svg>
			{:else}
				<svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
					<path
						fill-rule="evenodd"
						d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
						clip-rule="evenodd"
					/>
				</svg>
			{/if}
		</Combobox.Trigger>
	</Combobox.Control>
	<Portal>
		<Combobox.Positioner class="z-50">
			<Combobox.Content
				class="max-h-60 overflow-auto rounded-lg border border-surface-600 bg-surface-800 shadow-xl"
			>
				{#if items.length === 0}
					<div class="px-3 py-2 text-sm text-surface-400">
						{loading ? 'Searching...' : 'No wormholes found'}
					</div>
				{:else}
					{#each items as item (item.id)}
						<Combobox.Item
							item={{ value: String(item.id), label: item.code }}
							class="cursor-pointer px-3 py-2 text-white hover:bg-primary-950/60 data-highlighted:bg-primary-950/50"
						>
							<span>{item.code}</span>
							{#if item.target}
								<span class={classColour(item.target.class_name)}>{item.target.class_name}</span>
							{/if}
						</Combobox.Item>
					{/each}
				{/if}
			</Combobox.Content>
		</Combobox.Positioner>
	</Portal>
</Combobox>
