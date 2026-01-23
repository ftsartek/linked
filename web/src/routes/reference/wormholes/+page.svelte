<script lang="ts">
	import { onMount } from 'svelte';
	import { Progress, useDialog } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import WormholeTable from '$lib/components/reference/WormholeTable.svelte';
	import WormholeDetailDialog from '$lib/components/reference/WormholeDetailDialog.svelte';
	import type { WormholeSummary } from '$lib/components/reference/wormholeConstants';

	let loading = $state(true);
	let wormholes = $state<WormholeSummary[]>([]);

	// Detail dialog state
	let selectedWormholeId = $state<number | null>(null);
	const detailDialog = useDialog({ id: 'wormhole-detail-dialog' });

	onMount(async () => {
		const { data } = await apiClient.GET('/reference/wormholes');
		if (data) {
			wormholes = data;
		}
		loading = false;
	});

	function showDetail(wormhole: WormholeSummary) {
		selectedWormholeId = wormhole.id;
		detailDialog().setOpen(true);
	}
</script>

<main class="min-h-screen p-6">
	<div class="mx-auto max-w-[1600px]">
		<section class="rounded-xl bg-black/75 p-6 backdrop-blur-2xl">
			<h1 class="mb-2 text-2xl font-bold">Wormhole Types Reference</h1>
			<p class="mb-6 text-surface-400">
				A reference table of wormhole types organized by source and destination class. Click a
				wormhole code to see details.
			</p>

			{#if loading}
				<Progress value={null} />
			{:else}
				<WormholeTable {wormholes} onselect={showDetail} />

				<p class="mt-4 text-sm text-surface-500">
					Note: K162 is the exit signature and can appear in any system class. "Wandering" wormholes
					can spawn in any system class.
				</p>
			{/if}
		</section>
	</div>
</main>

<WormholeDetailDialog dialog={detailDialog} wormholeId={selectedWormholeId} />
