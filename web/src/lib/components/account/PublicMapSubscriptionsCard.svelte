<script lang="ts">
	import { resolve } from '$app/paths';
	import { Progress } from '@skeletonlabs/skeleton-svelte';
	import { Globe, X } from 'lucide-svelte';
	import { apiClient } from '$lib/client/client';
	import { user } from '$lib/stores/user';
	import type { components } from '$lib/client/schema';
	import BrowsePublicMapsDialog from './BrowsePublicMapsDialog.svelte';

	type MapInfo = components['schemas']['MapInfo'];

	let subscribedMaps = $state<MapInfo[]>([]);
	let loadingSubscriptions = $state(true);
	let browseDialog: BrowsePublicMapsDialog;

	export async function loadSubscribedMaps() {
		loadingSubscriptions = true;
		const { data } = await apiClient.GET('/maps/subscribed');
		subscribedMaps = data?.maps ?? [];
		loadingSubscriptions = false;
	}

	async function unsubscribe(mapId: string) {
		const { error: apiError } = await apiClient.DELETE('/maps/{map_id}/subscribe', {
			params: { path: { map_id: mapId } }
		});
		if (!apiError) {
			subscribedMaps = subscribedMaps.filter((m) => m.id !== mapId);
		}
	}

	$effect(() => {
		if ($user) {
			loadSubscribedMaps();
		}
	});
</script>

<section class="relative flex h-full flex-col rounded-xl bg-surface-950/75 p-6 backdrop-blur-2xl">
	{#if loadingSubscriptions}
		<div class="absolute top-0 right-0 left-0 z-10">
			<Progress value={null} class="h-0.5 w-full rounded-none">
				<Progress.Track class="h-0.5 rounded-none bg-transparent">
					<Progress.Range class="h-0.5 rounded-none bg-primary-300-700" />
				</Progress.Track>
			</Progress>
		</div>
	{/if}
	<div class="mb-4 flex items-start justify-between gap-4">
		<div>
			<h2 class="text-xl font-semibold">Public Map Subscriptions</h2>
			<p class="text-sm text-surface-400">Browse and manage public shared maps</p>
		</div>
		<button
			onclick={() => browseDialog.open()}
			class="btn-icon btn preset-outlined-surface-800-200 btn-sm py-2.5"
			title="Browse public maps"
		>
			<Globe size={20} />
		</button>
	</div>

	<div class="flex-1">
		{#if loadingSubscriptions}
			<div class="flex items-center justify-center py-8"></div>
		{:else if subscribedMaps.length === 0}
			<div class="py-8 text-center text-surface-400">
				No subscriptions yet. Browse public maps to find interesting wormhole chains.
			</div>
		{:else}
			<div class="grid gap-3">
				{#each subscribedMaps as map (map.id)}
					<div
						class="flex items-center gap-4 rounded-lg border-2 border-surface-900 bg-black/50 p-4"
					>
						<div class="flex-1">
							<div class="font-medium">{map.name}</div>
							{#if map.description}
								<div class="text-sm text-surface-400">{map.description}</div>
							{/if}
						</div>
						<div class="flex items-center gap-2">
							<a href={resolve(`/maps/${map.id}`)} class="btn preset-filled-primary-500 btn-sm">
								View
							</a>
							<button
								onclick={() => unsubscribe(map.id)}
								class="btn preset-outlined-error-500 btn-sm"
								title="Unsubscribe"
							>
								<X size={16} />
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</section>

<BrowsePublicMapsDialog bind:this={browseDialog} onSubscriptionChange={loadSubscribedMaps} />
