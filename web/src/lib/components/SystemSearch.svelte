<script lang="ts">
	import { Combobox, Portal } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import type { components } from '$lib/client/schema';

	type SystemSearchResult = components['schemas']['SystemSearchResult'];

	interface Props {
		onselect?: (system: SystemSearchResult) => void;
		placeholder?: string;
	}

	let { onselect, placeholder = 'Search systems...' }: Props = $props();

	let items = $state<SystemSearchResult[]>([]);
	let loading = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	function formatSystemLabel(system: SystemSearchResult): string {
		if (system.wh_class !== null && system.wh_class !== undefined) {
			return `${system.name} [C${system.wh_class}]`;
		}
		return system.name;
	}

	async function searchSystems(query: string) {
		if (query.length < 2) {
			items = [];
			return;
		}

		loading = true;
		const { data } = await apiClient.GET('/universe/systems', {
			params: { query: { q: query } }
		});
		items = data?.systems ?? [];
		loading = false;
	}

	function handleInputChange(details: { inputValue: string }) {
		if (debounceTimer) {
			clearTimeout(debounceTimer);
		}
		debounceTimer = setTimeout(() => {
			searchSystems(details.inputValue);
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
		if (details.open) {
			items = [];
		}
	}
</script>

<Combobox
	{placeholder}
	onInputValueChange={handleInputChange}
	onValueChange={handleValueChange}
	onOpenChange={handleOpenChange}
>
	<Combobox.Control>
		<Combobox.Input
			class="w-full rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-white placeholder-surface-400 focus:border-primary-500 focus:outline-none"
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
		<Combobox.Positioner class="z-[60]">
			<Combobox.Content
				class="max-h-60 overflow-auto rounded-lg border border-surface-600 bg-surface-800 shadow-xl"
			>
				{#if items.length === 0}
					<div class="px-3 py-2 text-sm text-surface-400">
						{loading ? 'Searching...' : 'Type to search systems'}
					</div>
				{:else}
					{#each items as item (item.id)}
						<Combobox.Item
							item={{ value: String(item.id), label: formatSystemLabel(item) }}
							class="cursor-pointer px-3 py-2 text-white hover:bg-surface-700 data-[highlighted]:bg-surface-700"
						>
							<span>{formatSystemLabel(item)}</span>
						</Combobox.Item>
					{/each}
				{/if}
			</Combobox.Content>
		</Combobox.Positioner>
	</Portal>
</Combobox>
