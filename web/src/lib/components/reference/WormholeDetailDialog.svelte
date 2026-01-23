<script lang="ts">
	import { Dialog, Portal, Progress } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import { classColour } from '$lib/helpers/renderClass';
	import {
		formatLifetime,
		formatMass,
		getShipClassLimit,
		type WormholeDetail
	} from './wormholeConstants';

	interface Props {
		dialog: ReturnType<typeof import('@skeletonlabs/skeleton-svelte').useDialog>;
		wormholeId: number | null;
	}

	let { dialog, wormholeId }: Props = $props();

	let loading = $state(false);
	let wormhole = $state<WormholeDetail | null>(null);
	let shipClassLimit = $derived(getShipClassLimit(wormhole?.mass_jump_max));

	$effect(() => {
		if (wormholeId !== null) {
			fetchWormhole(wormholeId);
		}
	});

	async function fetchWormhole(id: number) {
		loading = true;
		wormhole = null;
		const { data } = await apiClient.GET('/reference/wormholes/{wormhole_id}', {
			params: { path: { wormhole_id: id } }
		});
		if (data) {
			wormhole = data;
		}
		loading = false;
	}

	function closeDialog() {
		dialog().setOpen(false);
	}
</script>

<Dialog.Provider value={dialog}>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-4">
			<Dialog.Content class="w-full max-w-md rounded-xl bg-black/50 p-6 shadow-xl backdrop-blur-sm">
				{#if loading}
					<Progress value={null} />
				{:else if wormhole}
					<Dialog.Title class="mb-4 text-xl font-bold">
						<span class={classColour(wormhole.target_name)}>{wormhole.code}</span>
					</Dialog.Title>
					<div class="space-y-3">
						<div class="flex justify-between">
							<span class="text-surface-400">Leads to:</span>
							<span class={classColour(wormhole.target_name)}>
								{wormhole.target_name}
							</span>
						</div>
						<div class="flex justify-between">
							<span class="text-surface-400">Spawns in:</span>
							<span>
								{#if wormhole.source_names.length === 0}
									Anywhere
								{:else}
									{#each wormhole.source_names as sourceName, i (sourceName)}
										<span class={classColour(sourceName)}>{sourceName}</span>{i <
										wormhole.source_names.length - 1
											? ', '
											: ''}
									{/each}
								{/if}
							</span>
						</div>
						<hr class="border-surface-800" />
						<div class="flex justify-between">
							<span class="text-surface-400">Lifetime:</span>
							<span>{formatLifetime(wormhole.lifetime)}</span>
						</div>
						<div class="flex justify-between">
							<span class="text-surface-400">Total Mass:</span>
							<span>{formatMass(wormhole.mass_total)}</span>
						</div>
						<div class="flex justify-between" class:mb-0={shipClassLimit}>
							<span class="text-surface-400">Max Jump Mass:</span>
							<span>{formatMass(wormhole.mass_jump_max)}</span>
						</div>
						{#if shipClassLimit}
							<div class="flex justify-end">
								<span class="text-xs text-surface-500">{shipClassLimit}</span>
							</div>
						{/if}
						{#if wormhole.mass_regen}
							<div class="flex justify-between">
								<span class="text-surface-400">Mass Regen:</span>
								<span>{formatMass(wormhole.mass_regen)}</span>
							</div>
						{/if}
					</div>
					<div class="mt-6 flex justify-end">
						<button
							type="button"
							class="btn preset-filled-surface-500 btn-sm"
							onclick={closeDialog}
						>
							Close
						</button>
					</div>
				{/if}
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog.Provider>
