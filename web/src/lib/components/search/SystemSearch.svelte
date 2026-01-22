<script lang="ts">
	import { Combobox } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import type { components } from '$lib/client/schema';
	import { classColour } from '$lib/helpers/renderClass';

	type SystemSearchResult =
		components['schemas']['SearchSystemsSystemSearchResponse_0SystemSearchResultResponseBody'];

	interface Props {
		onselect?: (system: SystemSearchResult) => void;
		oncancel?: () => void;
		placeholder?: string;
		autofocus?: boolean;
	}

	let {
		onselect,
		oncancel,
		placeholder = 'Search systems...',
		autofocus = false
	}: Props = $props();

	let wrapperElement: HTMLDivElement | null = $state(null);
	let highlightedValue = $state<string | null>(null);

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
		if (event.key === 'Enter' && highlightedValue) {
			event.preventDefault();
			const selected = items.find((item) => String(item.id) === highlightedValue);
			if (selected && onselect) {
				onselect(selected);
			}
		}
	}

	let items = $state<SystemSearchResult[]>([]);
	let loading = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	async function searchSystems(query: string) {
		if (query.length < 2) {
			items = [];
			highlightedValue = null;
			return;
		}

		loading = true;
		const { data } = await apiClient.GET('/universe/systems', {
			params: { query: { q: query } }
		});
		items = data?.systems ?? [];
		// Auto-highlight first item when results are loaded
		const firstItem = items[0];
		highlightedValue = firstItem ? String(firstItem.id) : null;
		loading = false;
	}

	function handleInputChange(details: { inputValue: string }) {
		if (debounceTimer) {
			clearTimeout(debounceTimer);
		}
		debounceTimer = setTimeout(() => {
			searchSystems(details.inputValue);
		}, 400);
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
		if (details.open) {
			items = [];
		}
	}
</script>

<div class="w-56" bind:this={wrapperElement}>
	<Combobox
		{placeholder}
		{highlightedValue}
		inputBehavior="autohighlight"
		onInputValueChange={handleInputChange}
		onValueChange={handleValueChange}
		onOpenChange={handleOpenChange}
	>
		<Combobox.Control>
			<Combobox.Input
				onkeydown={handleKeydown}
				class="w-full rounded-sm border-2 border-primary-950 bg-black px-2 py-1 text-sm text-surface-100 placeholder-surface-400 focus:border-primary-800 focus:outline-none"
			/>
		</Combobox.Control>
		<Combobox.Positioner class="z-60">
			<Combobox.Content
				class="max-h-60 overflow-auto rounded-lg bg-black/50 shadow-xl backdrop-blur-sm"
			>
				{#if items.length === 0}
					<div class="px-3 py-2 text-sm text-surface-400">
						{loading ? 'Searching...' : 'Type to search systems'}
					</div>
				{:else}
					{#each items as item (item.id)}
						<Combobox.Item
							item={{ value: String(item.id), label: item.name }}
							class="cursor-pointer px-3 py-2 text-white hover:bg-primary-950/50 data-highlighted:bg-primary-950/30"
						>
							<Combobox.ItemText>
								{item.name}
								{#if item.class_name}
									<span class={classColour(item.class_name)}>{item.class_name}</span>
								{/if}
							</Combobox.ItemText>
						</Combobox.Item>
					{/each}
				{/if}
			</Combobox.Content>
		</Combobox.Positioner>
	</Combobox>
</div>
