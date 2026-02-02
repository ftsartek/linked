<script lang="ts">
	import { Combobox } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import { getEntityImageUrl } from '$lib/helpers/images';
	import type { components } from '$lib/client/schema';

	type EntitySearchResult = components['schemas']['EntitySearchResult'];

	type EntityCategory = 'character' | 'corporation' | 'alliance';

	interface SearchResult extends EntitySearchResult {
		category: EntityCategory;
	}

	interface Props {
		onselect?: (entity: SearchResult) => void;
		oncancel?: () => void;
		placeholder?: string;
		autofocus?: boolean;
		categories?: EntityCategory[];
	}

	let {
		onselect,
		oncancel,
		placeholder = 'Search characters, corps, alliances...',
		autofocus = false,
		categories = ['character', 'corporation', 'alliance']
	}: Props = $props();

	let wrapperElement: HTMLDivElement | null = $state(null);

	$effect(() => {
		if (autofocus && wrapperElement) {
			const input = wrapperElement.querySelector('input');
			if (input) {
				setTimeout(() => input.focus(), 0);
			}
		}
	});

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && oncancel) {
			oncancel();
		}
	}

	let items = $state<SearchResult[]>([]);
	let loading = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	async function searchEntities(query: string) {
		if (query.length < 3) {
			items = [];
			return;
		}

		loading = true;
		const { data } = await apiClient.GET('/universe/search', {
			params: { query: { q: query, categories: categories.join(',') } }
		});

		if (data) {
			// Combine all results with their category
			const results: SearchResult[] = [
				...data.characters.map((e) => ({ ...e, category: 'character' as const })),
				...data.corporations.map((e) => ({ ...e, category: 'corporation' as const })),
				...data.alliances.map((e) => ({ ...e, category: 'alliance' as const }))
			];
			items = results;
		} else {
			items = [];
		}
		loading = false;
	}

	function handleInputChange(details: { inputValue: string }) {
		if (debounceTimer) {
			clearTimeout(debounceTimer);
		}
		debounceTimer = setTimeout(() => {
			searchEntities(details.inputValue);
		}, 500);
	}

	function handleValueChange(details: { value: string[] }) {
		const selectedValue = details.value[0];
		if (selectedValue) {
			// Value format: "category:id"
			const [category, id] = selectedValue.split(':');
			const selected = items.find((item) => item.category === category && String(item.id) === id);
			if (selected && onselect) {
				onselect(selected);
			}
		}
	}

	function handleOpenChange(details: { open: boolean }) {
		if (details.open) {
			items = [];
		}
	}

	function getCategoryLabel(category: EntityCategory): string {
		switch (category) {
			case 'character':
				return 'Character';
			case 'corporation':
				return 'Corp';
			case 'alliance':
				return 'Alliance';
		}
	}

	function getCategoryColor(category: EntityCategory): string {
		switch (category) {
			case 'character':
				return 'text-primary-400';
			case 'corporation':
				return 'text-success-400';
			case 'alliance':
				return 'text-warning-400';
		}
	}

	function getImageUrl(category: EntityCategory, id: number): string {
		return getEntityImageUrl(category, id, 32);
	}
</script>

<div class="w-72" bind:this={wrapperElement}>
	<Combobox
		{placeholder}
		onInputValueChange={handleInputChange}
		onValueChange={handleValueChange}
		onOpenChange={handleOpenChange}
	>
		<Combobox.Control>
			<Combobox.Input
				onkeydown={handleKeydown}
				class="w-full rounded-sm border-2 border-secondary-950 bg-black px-2 py-1 text-sm text-white placeholder-surface-400 focus:border-primary-800 focus:outline-none"
			/>
		</Combobox.Control>
		<Combobox.Positioner class="z-60">
			<Combobox.Content
				class="max-h-60 overflow-auto rounded-sm border border-surface-600 bg-surface-800 shadow-xl"
			>
				{#if items.length === 0}
					<div class="px-3 py-2 text-sm text-surface-400">
						{#if loading}
							Searching...
						{:else}
							Type at least 3 characters to search
						{/if}
					</div>
				{:else}
					{#each items as item (`${item.category}:${item.id}`)}
						<Combobox.Item
							item={{ value: `${item.category}:${item.id}`, label: item.name }}
							class="flex cursor-pointer items-center gap-2 px-3 py-2 text-white hover:bg-primary-950/60 data-highlighted:bg-primary-950/50"
						>
							<img
								src={getImageUrl(item.category, item.id)}
								alt={item.name}
								class="h-8 w-8 rounded"
							/>
							<Combobox.ItemText>
								{item.name}
								<span class={`ml-2 text-xs ${getCategoryColor(item.category)}`}>
									{getCategoryLabel(item.category)}
								</span>
							</Combobox.ItemText>
						</Combobox.Item>
					{/each}
				{/if}
			</Combobox.Content>
		</Combobox.Positioner>
	</Combobox>
</div>
