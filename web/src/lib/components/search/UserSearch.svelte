<script lang="ts">
	import { Combobox } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import { getEntityImageUrl } from '$lib/helpers/images';
	import type { components } from '$lib/client/schema';

	type UserSearchResult = components['schemas']['UserSearchResult'];

	interface Props {
		onselect?: (user: UserSearchResult) => void;
		oncancel?: () => void;
		placeholder?: string;
		autofocus?: boolean;
	}

	let {
		onselect,
		oncancel,
		placeholder = 'Search users by character name...',
		autofocus = false
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

	let items = $state<UserSearchResult[]>([]);
	let loading = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	async function searchUsers(query: string) {
		if (query.length < 3) {
			items = [];
			return;
		}

		loading = true;
		const { data } = await apiClient.GET('/universe/search/users', {
			params: { query: { q: query } }
		});

		if (data) {
			items = data.results;
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
			searchUsers(details.inputValue);
		}, 500);
	}

	function handleValueChange(details: { value: string[] }) {
		const selectedValue = details.value[0];
		if (selectedValue) {
			const selected = items.find((item) => item.user_id === selectedValue);
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
				class="max-h-60 overflow-auto rounded-lg bg-black/50 shadow-xl backdrop-blur-sm"
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
					{#each items as item (item.user_id)}
						<Combobox.Item
							item={{ value: item.user_id, label: item.character_name }}
							class="flex cursor-pointer items-center gap-2 px-3 py-2 text-white hover:bg-primary-950/50 data-highlighted:bg-primary-800/20"
						>
							<img
								src={getEntityImageUrl('character', item.character_id, 32)}
								alt={item.character_name}
								class="h-8 w-8 rounded"
							/>
							<Combobox.ItemText>
								{item.character_name}
							</Combobox.ItemText>
						</Combobox.Item>
					{/each}
				{/if}
			</Combobox.Content>
		</Combobox.Positioner>
	</Combobox>
</div>
