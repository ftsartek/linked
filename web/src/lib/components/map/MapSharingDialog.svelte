<script lang="ts">
	import { Dialog, Portal, Progress } from '@skeletonlabs/skeleton-svelte';
	import LocalEntitySearch from '../search/LocalEntitySearch.svelte';
	import { apiClient } from '$lib/client/client';
	import { toaster } from '$lib/stores/toaster';
	import { getEntityImageUrl } from '$lib/helpers/images';
	import type {
		CharacterAccessInfo,
		CorporationAccessInfo,
		AllianceAccessInfo
	} from '$lib/helpers/mapTypes';

	interface Props {
		dialog: ReturnType<typeof import('@skeletonlabs/skeleton-svelte').useDialog>;
		map_id: string;
		open?: boolean;
	}

	let { dialog, map_id, open = false }: Props = $props();

	// Internal state
	let loading = $state(false);
	let characters = $state<CharacterAccessInfo[]>([]);
	let corporations = $state<CorporationAccessInfo[]>([]);
	let alliances = $state<AllianceAccessInfo[]>([]);
	let hasLoaded = $state(false);

	// Local state for tabs and read-only toggle
	let sharingTab = $state<'characters' | 'corporations' | 'alliances'>('characters');
	let newEntityReadOnly = $state(true);

	// Load access data when dialog opens
	async function loadAccessData() {
		loading = true;

		const { data, error } = await apiClient.GET('/maps/{map_id}/access', {
			params: { path: { map_id } }
		});

		loading = false;

		if (error) {
			toaster.create({
				title: 'Error',
				description: 'Failed to load access list',
				type: 'error'
			});
			return;
		}

		if (data) {
			characters = data.characters;
			corporations = data.corporations;
			alliances = data.alliances;
		}
	}

	// Watch for dialog open state via prop
	$effect(() => {
		if (open && !hasLoaded) {
			hasLoaded = true;
			loadAccessData();
		}
		if (!open) {
			hasLoaded = false;
		}
	});

	async function handleEntitySelect(entity: {
		id: number;
		name: string;
		entity_type: string;
		ticker?: string | null;
	}) {
		const readOnly = newEntityReadOnly;

		if (entity.entity_type === 'character') {
			if (characters.some((c) => c.character_id === entity.id)) {
				toaster.create({
					title: 'Already Added',
					description: `${entity.name} already has access`,
					type: 'warning'
				});
				return;
			}

			const { error } = await apiClient.POST('/maps/{map_id}/characters', {
				params: { path: { map_id } },
				body: { character_id: entity.id, read_only: readOnly }
			});

			if (error) {
				toaster.create({
					title: 'Error',
					description: 'detail' in error ? error.detail : 'Failed to add character',
					type: 'error'
				});
				return;
			}

			characters = [
				...characters,
				{ character_id: entity.id, character_name: entity.name, read_only: readOnly }
			];
		} else if (entity.entity_type === 'corporation') {
			if (corporations.some((c) => c.corporation_id === entity.id)) {
				toaster.create({
					title: 'Already Added',
					description: `${entity.name} already has access`,
					type: 'warning'
				});
				return;
			}

			const { error } = await apiClient.POST('/maps/{map_id}/corporations', {
				params: { path: { map_id } },
				body: { corporation_id: entity.id, read_only: readOnly }
			});

			if (error) {
				toaster.create({
					title: 'Error',
					description: 'detail' in error ? error.detail : 'Failed to add corporation',
					type: 'error'
				});
				return;
			}

			corporations = [
				...corporations,
				{
					corporation_id: entity.id,
					corporation_name: entity.name,
					corporation_ticker: entity.ticker ?? '',
					read_only: readOnly
				}
			];
		} else if (entity.entity_type === 'alliance') {
			if (alliances.some((a) => a.alliance_id === entity.id)) {
				toaster.create({
					title: 'Already Added',
					description: `${entity.name} already has access`,
					type: 'warning'
				});
				return;
			}

			const { error } = await apiClient.POST('/maps/{map_id}/alliances', {
				params: { path: { map_id } },
				body: { alliance_id: entity.id, read_only: readOnly }
			});

			if (error) {
				toaster.create({
					title: 'Error',
					description: 'detail' in error ? error.detail : 'Failed to add alliance',
					type: 'error'
				});
				return;
			}

			alliances = [
				...alliances,
				{
					alliance_id: entity.id,
					alliance_name: entity.name,
					alliance_ticker: entity.ticker ?? '',
					read_only: readOnly
				}
			];
		}
	}

	async function handleRemoveCharacter(characterId: number) {
		const { error } = await apiClient.DELETE('/maps/{map_id}/characters/{character_id}', {
			params: { path: { map_id, character_id: characterId } }
		});

		if (error) {
			toaster.create({
				title: 'Error',
				description: 'Failed to remove character',
				type: 'error'
			});
			return;
		}

		characters = characters.filter((c) => c.character_id !== characterId);
	}

	async function handleRemoveCorporation(corporationId: number) {
		const { error } = await apiClient.DELETE('/maps/{map_id}/corporations/{corporation_id}', {
			params: { path: { map_id, corporation_id: corporationId } }
		});

		if (error) {
			toaster.create({
				title: 'Error',
				description: 'Failed to remove corporation',
				type: 'error'
			});
			return;
		}

		corporations = corporations.filter((c) => c.corporation_id !== corporationId);
	}

	async function handleRemoveAlliance(allianceId: number) {
		const { error } = await apiClient.DELETE('/maps/{map_id}/alliances/{alliance_id}', {
			params: { path: { map_id, alliance_id: allianceId } }
		});

		if (error) {
			toaster.create({
				title: 'Error',
				description: 'Failed to remove alliance',
				type: 'error'
			});
			return;
		}

		alliances = alliances.filter((a) => a.alliance_id !== allianceId);
	}
</script>

<Dialog.Provider value={dialog}>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-4">
			<Dialog.Content
				class="relative w-full max-w-lg rounded-lg bg-black/50 p-6 shadow-xl backdrop-blur-sm"
			>
				{#if loading}
					<div class="absolute top-0 right-0 left-0 z-10">
						<Progress value={null} class="h-1 w-full rounded-none">
							<Progress.Track class="h-1 rounded-none bg-transparent">
								<Progress.Range class="h-1 rounded-none bg-primary-500" />
							</Progress.Track>
						</Progress>
					</div>
				{/if}
				<Dialog.Title class="mb-4 text-xl font-bold text-white">Share Map</Dialog.Title>
				<div>
					<!-- Search to add new access -->
					<div class="mb-4">
						<div class="mb-2 flex items-center gap-3">
							<LocalEntitySearch
								placeholder="Search characters, corps, alliances..."
								onselect={handleEntitySelect}
							/>
							<label class="flex items-center gap-1 text-sm text-surface-300">
								<input type="checkbox" bind:checked={newEntityReadOnly} />
								Read Only
							</label>
						</div>
					</div>

					<!-- Tabs -->
					<div class="mb-4 flex border-b border-surface-600">
						<button
							class="px-4 py-2 text-sm {sharingTab === 'characters'
								? 'border-b-2 border-primary-500 text-white'
								: 'text-surface-400 hover:text-white'}"
							onclick={() => (sharingTab = 'characters')}
						>
							Characters
						</button>
						<button
							class="px-4 py-2 text-sm {sharingTab === 'corporations'
								? 'border-b-2 border-primary-500 text-white'
								: 'text-surface-400 hover:text-white'}"
							onclick={() => (sharingTab = 'corporations')}
						>
							Corporations
						</button>
						<button
							class="px-4 py-2 text-sm {sharingTab === 'alliances'
								? 'border-b-2 border-primary-500 text-white'
								: 'text-surface-400 hover:text-white'}"
							onclick={() => (sharingTab = 'alliances')}
						>
							Alliances
						</button>
					</div>

					{#if loading}
						<div class="flex justify-center py-8"></div>
					{:else if sharingTab === 'characters'}
						<!-- Characters Tab -->
						<div class="space-y-3">
							{#each characters as char (char.character_id)}
								<div class="flex items-center justify-between rounded bg-surface-700 px-3 py-2">
									<div class="flex items-center gap-2">
										<img
											src={getEntityImageUrl('character', char.character_id, 32)}
											alt={char.character_name}
											class="h-8 w-8 rounded"
										/>
										<span class="text-sm text-white">{char.character_name}</span>
									</div>
									<div class="flex items-center gap-2">
										<span class="text-xs text-surface-400"
											>{char.read_only ? 'Read Only' : 'Edit'}</span
										>
										<button
											class="text-error-400 hover:text-error-300"
											onclick={() => handleRemoveCharacter(char.character_id)}
											title="Remove character"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												width="16"
												height="16"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
											>
												<line x1="18" y1="6" x2="6" y2="18" />
												<line x1="6" y1="6" x2="18" y2="18" />
											</svg>
										</button>
									</div>
								</div>
							{:else}
								<p class="text-sm text-surface-400">No characters have access</p>
							{/each}
						</div>
					{:else if sharingTab === 'corporations'}
						<!-- Corporations Tab -->
						<div class="space-y-3">
							{#each corporations as corp (corp.corporation_id)}
								<div class="flex items-center justify-between rounded bg-surface-700 px-3 py-2">
									<div class="flex items-center gap-2">
										<img
											src={getEntityImageUrl('corporation', corp.corporation_id, 32)}
											alt={corp.corporation_name}
											class="h-8 w-8 rounded"
										/>
										<span class="text-sm text-white"
											>{corp.corporation_name}
											<span class="text-surface-400">[{corp.corporation_ticker}]</span></span
										>
									</div>
									<div class="flex items-center gap-2">
										<span class="text-xs text-surface-400"
											>{corp.read_only ? 'Read Only' : 'Edit'}</span
										>
										<button
											class="text-error-400 hover:text-error-300"
											onclick={() => handleRemoveCorporation(corp.corporation_id)}
											title="Remove corporation"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												width="16"
												height="16"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
											>
												<line x1="18" y1="6" x2="6" y2="18" />
												<line x1="6" y1="6" x2="18" y2="18" />
											</svg>
										</button>
									</div>
								</div>
							{:else}
								<p class="text-sm text-surface-400">No corporations have access</p>
							{/each}
						</div>
					{:else if sharingTab === 'alliances'}
						<!-- Alliances Tab -->
						<div class="space-y-3">
							{#each alliances as ally (ally.alliance_id)}
								<div class="flex items-center justify-between rounded bg-surface-700 px-3 py-2">
									<div class="flex items-center gap-2">
										<img
											src={getEntityImageUrl('alliance', ally.alliance_id, 32)}
											alt={ally.alliance_name}
											class="h-8 w-8 rounded"
										/>
										<span class="text-sm text-white"
											>{ally.alliance_name}
											<span class="text-surface-400">[{ally.alliance_ticker}]</span></span
										>
									</div>
									<div class="flex items-center gap-2">
										<span class="text-xs text-surface-400"
											>{ally.read_only ? 'Read Only' : 'Edit'}</span
										>
										<button
											class="text-error-400 hover:text-error-300"
											onclick={() => handleRemoveAlliance(ally.alliance_id)}
											title="Remove alliance"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												width="16"
												height="16"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
											>
												<line x1="18" y1="6" x2="6" y2="18" />
												<line x1="6" y1="6" x2="18" y2="18" />
											</svg>
										</button>
									</div>
								</div>
							{:else}
								<p class="text-sm text-surface-400">No alliances have access</p>
							{/each}
						</div>
					{/if}
				</div>
				<div class="mt-6 flex justify-end">
					<Dialog.CloseTrigger
						class="rounded bg-surface-600 px-4 py-2 text-white hover:bg-surface-500"
					>
						Close
					</Dialog.CloseTrigger>
				</div>
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog.Provider>
