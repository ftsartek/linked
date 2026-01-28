<script lang="ts">
	import { Dialog, Portal, Progress, useDialog } from '@skeletonlabs/skeleton-svelte';
	import { Trash2, Globe, Lock, Map } from 'lucide-svelte';
	import EntitySearch from '../search/EntitySearch.svelte';
	import { apiClient } from '$lib/client/client';
	import { toaster } from '$lib/stores/toaster';
	import { getEntityImageUrl } from '$lib/helpers/images';
	import type { components } from '$lib/client/schema';

	type CharacterACLEntry = components['schemas']['CharacterACLEntry'];
	type CorporationACLEntry = components['schemas']['CorporationACLEntry'];
	type AllianceACLEntry = components['schemas']['AllianceACLEntry'];

	// Loading states
	let loading = $state(true);
	let updating = $state(false);
	let updatingMapCreation = $state(false);

	// Instance settings
	let isOpen = $state(false);
	let allowMapCreation = $state(true);

	// ACL data
	let characters = $state<CharacterACLEntry[]>([]);
	let corporations = $state<CorporationACLEntry[]>([]);
	let alliances = $state<AllianceACLEntry[]>([]);

	// UI state
	let activeTab = $state<'characters' | 'corporations' | 'alliances'>('characters');

	// Public instance toggle dialog
	const publicDialog = useDialog({ id: 'public-instance-dialog' });

	async function loadData() {
		loading = true;

		// Load instance status and all ACL lists in parallel
		const [statusRes, charRes, corpRes, allyRes] = await Promise.all([
			apiClient.GET('/admin/instance'),
			apiClient.GET('/admin/acl/characters'),
			apiClient.GET('/admin/acl/corporations'),
			apiClient.GET('/admin/acl/alliances')
		]);

		if (statusRes.data) {
			isOpen = statusRes.data.is_open;
			allowMapCreation = statusRes.data.allow_map_creation;
		}

		characters = charRes.data?.entries ?? [];
		corporations = corpRes.data?.entries ?? [];
		alliances = allyRes.data?.entries ?? [];

		loading = false;
	}

	$effect(() => {
		loadData();
	});

	function openPublicDialog() {
		publicDialog().setOpen(true);
	}

	async function confirmTogglePublic() {
		updating = true;
		const newValue = !isOpen;

		const { data, error } = await apiClient.PATCH('/admin/instance', {
			body: { is_open: newValue }
		});

		if (error) {
			const message = 'detail' in error ? (error.detail as string) : 'Failed to update setting';
			toaster.create({ title: 'Error', description: message, type: 'error' });
		} else if (data) {
			isOpen = data.is_open;
			toaster.create({
				title: 'Success',
				description: `Instance is now ${isOpen ? 'public' : 'private'}`,
				type: 'success'
			});
		}

		updating = false;
		publicDialog().setOpen(false);
	}

	async function toggleMapCreation() {
		updatingMapCreation = true;
		const newValue = !allowMapCreation;

		const { data, error } = await apiClient.PATCH('/admin/instance', {
			body: { allow_map_creation: newValue }
		});

		if (error) {
			const message = 'detail' in error ? (error.detail as string) : 'Failed to update setting';
			toaster.create({ title: 'Error', description: message, type: 'error' });
		} else if (data) {
			allowMapCreation = data.allow_map_creation;
			toaster.create({
				title: 'Success',
				description: allowMapCreation
					? 'All users can now create maps'
					: 'Only admins can now create maps',
				type: 'success'
			});
		}

		updatingMapCreation = false;
	}

	async function handleAddEntity(entity: {
		id: number;
		name: string;
		category: 'character' | 'corporation' | 'alliance';
	}) {
		if (entity.category === 'character') {
			if (characters.some((c) => c.character_id === entity.id)) {
				toaster.create({
					title: 'Already Added',
					description: `${entity.name} is already in the ACL`,
					type: 'warning'
				});
				return;
			}

			const { error } = await apiClient.POST('/admin/acl/characters', {
				body: { character_id: entity.id, character_name: entity.name }
			});

			if (error) {
				const message = 'detail' in error ? (error.detail as string) : 'Failed to add character';
				toaster.create({ title: 'Error', description: message, type: 'error' });
				return;
			}

			characters = [
				...characters,
				{ character_id: entity.id, character_name: entity.name, added_by: null, date_created: null }
			];
			toaster.create({
				title: 'Success',
				description: `${entity.name} added to ACL`,
				type: 'success'
			});
		} else if (entity.category === 'corporation') {
			if (corporations.some((c) => c.corporation_id === entity.id)) {
				toaster.create({
					title: 'Already Added',
					description: `${entity.name} is already in the ACL`,
					type: 'warning'
				});
				return;
			}

			const { error } = await apiClient.POST('/admin/acl/corporations', {
				body: {
					corporation_id: entity.id,
					corporation_name: entity.name,
					corporation_ticker: ''
				}
			});

			if (error) {
				const message = 'detail' in error ? (error.detail as string) : 'Failed to add corporation';
				toaster.create({ title: 'Error', description: message, type: 'error' });
				return;
			}

			corporations = [
				...corporations,
				{
					corporation_id: entity.id,
					corporation_name: entity.name,
					corporation_ticker: '',
					added_by: null,
					date_created: null
				}
			];
			toaster.create({
				title: 'Success',
				description: `${entity.name} added to ACL`,
				type: 'success'
			});
		} else if (entity.category === 'alliance') {
			if (alliances.some((a) => a.alliance_id === entity.id)) {
				toaster.create({
					title: 'Already Added',
					description: `${entity.name} is already in the ACL`,
					type: 'warning'
				});
				return;
			}

			const { error } = await apiClient.POST('/admin/acl/alliances', {
				body: {
					alliance_id: entity.id,
					alliance_name: entity.name,
					alliance_ticker: ''
				}
			});

			if (error) {
				const message = 'detail' in error ? (error.detail as string) : 'Failed to add alliance';
				toaster.create({ title: 'Error', description: message, type: 'error' });
				return;
			}

			alliances = [
				...alliances,
				{
					alliance_id: entity.id,
					alliance_name: entity.name,
					alliance_ticker: '',
					added_by: null,
					date_created: null
				}
			];
			toaster.create({
				title: 'Success',
				description: `${entity.name} added to ACL`,
				type: 'success'
			});
		}
	}

	async function removeCharacter(characterId: number) {
		const { error } = await apiClient.DELETE('/admin/acl/characters/{character_id}', {
			params: { path: { character_id: characterId } }
		});

		if (error) {
			const message = 'detail' in error ? (error.detail as string) : 'Failed to remove character';
			toaster.create({ title: 'Error', description: message, type: 'error' });
			return;
		}

		characters = characters.filter((c) => c.character_id !== characterId);
	}

	async function removeCorporation(corporationId: number) {
		const { error } = await apiClient.DELETE('/admin/acl/corporations/{corporation_id}', {
			params: { path: { corporation_id: corporationId } }
		});

		if (error) {
			const message = 'detail' in error ? (error.detail as string) : 'Failed to remove corporation';
			toaster.create({ title: 'Error', description: message, type: 'error' });
			return;
		}

		corporations = corporations.filter((c) => c.corporation_id !== corporationId);
	}

	async function removeAlliance(allianceId: number) {
		const { error } = await apiClient.DELETE('/admin/acl/alliances/{alliance_id}', {
			params: { path: { alliance_id: allianceId } }
		});

		if (error) {
			const message = 'detail' in error ? (error.detail as string) : 'Failed to remove alliance';
			toaster.create({ title: 'Error', description: message, type: 'error' });
			return;
		}

		alliances = alliances.filter((a) => a.alliance_id !== allianceId);
	}
</script>

<section class="relative flex h-full flex-col rounded-xl bg-black/75 p-6 backdrop-blur-2xl">
	{#if loading}
		<div class="absolute top-0 right-0 left-0 z-10">
			<Progress value={null} class="h-0.5 w-full rounded-none">
				<Progress.Track class="h-0.5 rounded-none bg-transparent">
					<Progress.Range class="h-0.5 rounded-none bg-primary-300-700" />
				</Progress.Track>
			</Progress>
		</div>
	{/if}
	<!-- Header -->
	<div class="mb-4">
		<h2 class="text-xl font-semibold">Instance Access Control</h2>
		<p class="text-sm text-surface-400">Manage who can access this instance.</p>
	</div>

	<!-- Instance Settings -->
	<div class="mb-4 grid gap-3">
		<!-- Public Instance Status & Button -->
		<div
			class="flex items-center justify-between rounded-lg border-2 border-surface-900 bg-black/50 p-3"
		>
			<div class="flex items-center gap-3">
				{#if isOpen}
					<Globe size={20} class="text-success-400" />
					<div>
						<span class="font-medium text-success-400">Public Instance</span>
						<p class="text-xs text-surface-400">Anyone can access without ACL entry</p>
					</div>
				{:else}
					<Lock size={20} class="text-surface-400" />
					<div>
						<span class="font-medium">Private Instance</span>
						<p class="text-xs text-surface-400">Only ACL entries can access</p>
					</div>
				{/if}
			</div>
			<button
				onclick={openPublicDialog}
				class="btn btn-sm {isOpen ? 'preset-outlined-warning-500' : 'preset-outlined-success-500'}"
				disabled={loading}
			>
				{isOpen ? 'Make Private' : 'Make Public'}
			</button>
		</div>

		<!-- Map Creation Toggle -->
		<div
			class="flex items-center justify-between rounded-lg border-2 border-surface-900 bg-black/50 p-3"
		>
			<div class="flex items-center gap-3">
				<Map size={20} class={allowMapCreation ? 'text-success-400' : 'text-surface-400'} />
				<div>
					<span class="font-medium" class:text-success-400={allowMapCreation}>
						{allowMapCreation ? 'Open Map Creation' : 'Restricted Map Creation'}
					</span>
					<p class="text-xs text-surface-400">
						{allowMapCreation ? 'All users can create maps' : 'Only admins can create maps'}
					</p>
				</div>
			</div>
			<button
				onclick={toggleMapCreation}
				class="btn btn-sm {allowMapCreation
					? 'preset-outlined-warning-500'
					: 'preset-outlined-success-500'}"
				disabled={loading || updatingMapCreation}
			>
				{updatingMapCreation ? 'Updating...' : allowMapCreation ? 'Restrict' : 'Allow All'}
			</button>
		</div>
	</div>

	{#if !isOpen}
		<!-- Search to add -->
		<div class="mb-4">
			<EntitySearch
				placeholder="Search characters, corps, alliances to add..."
				onselect={handleAddEntity}
			/>
		</div>

		<!-- Tabs with counts -->
		<div class="mb-4 flex border-b border-surface-600">
			<button
				class="px-4 py-2 text-sm {activeTab === 'characters'
					? 'border-b-2 border-primary-500 text-white'
					: 'text-surface-400 hover:text-white'}"
				onclick={() => (activeTab = 'characters')}
			>
				Characters ({characters.length})
			</button>
			<button
				class="px-4 py-2 text-sm {activeTab === 'corporations'
					? 'border-b-2 border-primary-500 text-white'
					: 'text-surface-400 hover:text-white'}"
				onclick={() => (activeTab = 'corporations')}
			>
				Corporations ({corporations.length})
			</button>
			<button
				class="px-4 py-2 text-sm {activeTab === 'alliances'
					? 'border-b-2 border-primary-500 text-white'
					: 'text-surface-400 hover:text-white'}"
				onclick={() => (activeTab = 'alliances')}
			>
				Alliances ({alliances.length})
			</button>
		</div>

		<!-- Content based on active tab -->
		<div class="flex-1 overflow-auto">
			{#if loading}
				<div class="flex items-center justify-center py-8"></div>
			{:else if activeTab === 'characters'}
				<div class="grid gap-3">
					{#each characters as char (char.character_id)}
						<div
							class="flex items-center gap-3 rounded-lg border-2 border-surface-900 bg-black/50 p-3"
						>
							<img
								src={getEntityImageUrl('character', char.character_id, 64)}
								alt={char.character_name}
								class="h-8 w-8 rounded-full"
							/>
							<div class="flex-1">
								<span class="font-medium">{char.character_name}</span>
							</div>
							<button
								onclick={() => removeCharacter(char.character_id)}
								class="btn preset-outlined-error-500 btn-sm"
								title="Remove character"
							>
								<Trash2 size={16} />
							</button>
						</div>
					{:else}
						<p class="text-sm text-surface-400">No characters in ACL</p>
					{/each}
				</div>
			{:else if activeTab === 'corporations'}
				<div class="grid gap-3">
					{#each corporations as corp (corp.corporation_id)}
						<div
							class="flex items-center gap-3 rounded-lg border-2 border-surface-900 bg-black/50 p-3"
						>
							<img
								src={getEntityImageUrl('corporation', corp.corporation_id, 64)}
								alt={corp.corporation_name}
								class="h-8 w-8 rounded"
							/>
							<div class="flex-1">
								<span class="font-medium">{corp.corporation_name}</span>
								{#if corp.corporation_ticker}
									<span class="ml-2 text-surface-400">[{corp.corporation_ticker}]</span>
								{/if}
							</div>
							<button
								onclick={() => removeCorporation(corp.corporation_id)}
								class="btn preset-outlined-error-500 btn-sm"
								title="Remove corporation"
							>
								<Trash2 size={16} />
							</button>
						</div>
					{:else}
						<p class="text-sm text-surface-400">No corporations in ACL</p>
					{/each}
				</div>
			{:else if activeTab === 'alliances'}
				<div class="grid gap-3">
					{#each alliances as ally (ally.alliance_id)}
						<div
							class="flex items-center gap-3 rounded-lg border-2 border-surface-900 bg-black/50 p-3"
						>
							<img
								src={getEntityImageUrl('alliance', ally.alliance_id, 64)}
								alt={ally.alliance_name}
								class="h-8 w-8 rounded"
							/>
							<div class="flex-1">
								<span class="font-medium">{ally.alliance_name}</span>
								{#if ally.alliance_ticker}
									<span class="ml-2 text-surface-400">[{ally.alliance_ticker}]</span>
								{/if}
							</div>
							<button
								onclick={() => removeAlliance(ally.alliance_id)}
								class="btn preset-outlined-error-500 btn-sm"
								title="Remove alliance"
							>
								<Trash2 size={16} />
							</button>
						</div>
					{:else}
						<p class="text-sm text-surface-400">No alliances in ACL</p>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</section>

<!-- Public Instance Confirmation Dialog -->
<Dialog.Provider value={publicDialog}>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-4">
			<Dialog.Content class="w-full max-w-md rounded-lg bg-black/50 p-6 shadow-xl backdrop-blur-sm">
				{#if isOpen}
					<Dialog.Title class="mb-2 text-xl font-bold text-warning-400">
						Make Instance Private?
					</Dialog.Title>
					<p class="mb-4 text-sm text-surface-300">
						This will restrict access to only users, corporations, and alliances in the ACL. Users
						not in the ACL will no longer be able to access this instance.
					</p>
				{:else}
					<Dialog.Title class="mb-2 text-xl font-bold text-success-400">
						Make Instance Public?
					</Dialog.Title>
					<div class="mb-4 rounded-lg bg-warning-500/20 p-3 text-sm text-warning-300">
						<strong>Warning:</strong> This will allow anyone with an EVE Online account to access this
						instance without needing to be in the ACL.
					</div>
				{/if}
				<div class="flex justify-end gap-3">
					<Dialog.CloseTrigger class="btn preset-outlined-surface-500">Cancel</Dialog.CloseTrigger>
					<button
						onclick={confirmTogglePublic}
						class="btn {isOpen ? 'preset-filled-warning-500' : 'preset-filled-success-500'}"
						disabled={updating}
					>
						{updating ? 'Updating...' : isOpen ? 'Make Private' : 'Make Public'}
					</button>
				</div>
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog.Provider>
