<script lang="ts">
	import { Dialog, Portal, Progress, Tooltip, useDialog } from '@skeletonlabs/skeleton-svelte';
	import { Star, Trash2, RefreshCw } from 'lucide-svelte';
	import { apiClient } from '$lib/client/client';
	import { user } from '$lib/stores/user';
	import { toaster } from '$lib/stores/toaster';
	import { getCharacterPortrait } from '$lib/helpers/images';
	import { getScopeGroupInfo } from '$lib/helpers/scopeGroups';
	import ScopeSelectionDialog from './ScopeSelectionDialog.svelte';
	import type { components } from '$lib/client/schema';

	type CharacterInfo = components['schemas']['auth_service_CharacterInfo'];

	let characters = $state<CharacterInfo[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Delete confirmation state
	let characterToDelete = $state<CharacterInfo | null>(null);
	let deleting = $state(false);
	const deleteDialog = useDialog({ id: 'delete-character-dialog' });

	// Link character dialog state
	const linkDialog = useDialog({ id: 'link-character-dialog' });

	// Update permissions dialog state
	const updateScopesDialog = useDialog({ id: 'update-scopes-dialog' });
	let characterToUpdate = $state<CharacterInfo | null>(null);

	// Derive primary character ID from user store
	let primaryCharacterId = $derived($user?.primary_character_id ?? null);

	export async function loadCharacters() {
		loading = true;
		error = null;

		const { data, error: apiError } = await apiClient.GET('/auth/me');

		if (apiError) {
			error = 'Failed to load characters';
			loading = false;
			return;
		}

		characters = data?.characters ?? [];
		loading = false;
	}

	$effect(() => {
		if ($user) {
			loadCharacters();
		}
	});

	async function setPrimaryCharacter(characterId: number) {
		const { error: apiError } = await apiClient.PUT('/users/primary-character', {
			body: { character_id: characterId }
		});

		if (apiError) {
			toaster.create({
				title: 'Error',
				description: 'Failed to set primary character',
				type: 'error'
			});
			return;
		}

		// Update user store with new primary character
		user.update((u) => (u ? { ...u, primary_character_id: characterId } : u));

		toaster.create({
			title: 'Success',
			description: 'Primary character updated',
			type: 'success'
		});
	}

	function openDeleteDialog(character: CharacterInfo) {
		characterToDelete = character;
		deleteDialog().setOpen(true);
	}

	function openLinkDialog() {
		linkDialog().setOpen(true);
	}

	function openUpdateScopesDialog(character: CharacterInfo) {
		characterToUpdate = character;
		updateScopesDialog().setOpen(true);
	}

	async function confirmDelete() {
		if (!characterToDelete) return;

		deleting = true;

		const { error: apiError } = await apiClient.DELETE('/users/characters/{character_id}', {
			params: { path: { character_id: characterToDelete.id } }
		});

		if (apiError) {
			const message =
				'detail' in apiError ? (apiError.detail as string) : 'Failed to remove character';
			toaster.create({
				title: 'Error',
				description: message,
				type: 'error'
			});
			deleting = false;
			return;
		}

		toaster.create({
			title: 'Success',
			description: `${characterToDelete.name} has been removed`,
			type: 'success'
		});

		// Refresh character list and user info
		await loadCharacters();
		const { data } = await apiClient.GET('/auth/me');
		user.set(data ?? null);

		deleting = false;
		deleteDialog().setOpen(false);
		characterToDelete = null;
	}

	function formatDate(dateString: string): string {
		return new Date(dateString).toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}
</script>

<section class="relative flex h-full flex-col rounded-xl bg-surface-950/75 p-6 backdrop-blur-2xl">
	{#if loading}
		<div class="absolute top-0 right-0 left-0 z-10">
			<Progress value={null} class="h-0.5 w-full rounded-none">
				<Progress.Track class="h-0.5 rounded-none bg-transparent">
					<Progress.Range class="h-0.5 rounded-none bg-primary-300-700" />
				</Progress.Track>
			</Progress>
		</div>
	{/if}
	<div class="mb-4">
		<h2 class="text-xl font-semibold">Characters</h2>
		<p class="text-sm text-surface-400">Manage characters linked to your account</p>
	</div>

	<div class="flex-1">
		{#if loading}
			<div class="flex items-center justify-center py-8"></div>
		{:else if error}
			<div class="rounded-lg bg-error-500/20 p-4 text-error-500">
				{error}
			</div>
		{:else if characters.length === 0}
			<div class="py-8 text-center text-surface-400">
				No characters linked. Add a character to get started.
			</div>
		{:else}
			{#if primaryCharacterId === null}
				<div class="mb-4 rounded-lg bg-warning-500/20 p-3 text-sm text-warning-400">
					No primary character set. Click the star icon to set one.
				</div>
			{/if}
			<div class="grid gap-3">
				{#each characters as character (character.id)}
					{@const isPrimary = character.id === primaryCharacterId}
					{@const isOnlyCharacter = characters.length === 1}
					<div
						class="flex items-center gap-4 rounded-lg border-2 border-surface-900 bg-black/50 p-4"
					>
						<!-- Portrait -->
						<img
							src={getCharacterPortrait(character.id, 64)}
							alt={character.name}
							class="h-12 w-12 rounded-full"
						/>

						<!-- Character Info -->
						<div class="flex-1">
							<div class="flex flex-wrap items-center gap-2">
								<span class="font-medium">{character.name}</span>
								{#if isPrimary}
									<span
										class="rounded bg-primary-500/20 px-2 py-0.5 text-xs font-medium text-primary-400"
									>
										Primary
									</span>
								{/if}
								{#each character.scope_groups as scopeId (scopeId)}
									{@const scopeInfo = getScopeGroupInfo(scopeId)}
									{#if scopeInfo}
										<Tooltip positioning={{ placement: 'top' }}>
											<Tooltip.Trigger>
												<span
													class="rounded bg-tertiary-500/20 px-1.5 py-0.5 text-xs font-medium text-tertiary-400"
												>
													{scopeInfo.name}
												</span>
											</Tooltip.Trigger>
											<Portal>
												<Tooltip.Positioner>
													<Tooltip.Content
														class="z-10 max-w-xs rounded-lg border border-surface-600 bg-surface-800 px-2 py-1 text-xs shadow-xl"
													>
														<Tooltip.Arrow
															class="[--arrow-background:var(--color-surface-800)] [--arrow-size:--spacing(2)]"
														>
															<Tooltip.ArrowTip />
														</Tooltip.Arrow>
														<span class="text-white">{scopeInfo.description}</span>
													</Tooltip.Content>
												</Tooltip.Positioner>
											</Portal>
										</Tooltip>
									{/if}
								{/each}
							</div>
							<div class="text-sm text-surface-400">
								Added {formatDate(character.date_created)}
							</div>
						</div>

						<!-- Actions -->
						<div class="flex items-center gap-2">
							<!-- Update Permissions Button -->
							<Tooltip positioning={{ placement: 'top' }}>
								<Tooltip.Trigger>
									<button
										onclick={() => openUpdateScopesDialog(character)}
										class="btn preset-outlined-surface-500 btn-sm"
									>
										<RefreshCw size={16} />
									</button>
								</Tooltip.Trigger>
								<Portal>
									<Tooltip.Positioner>
										<Tooltip.Content
											class="z-10 rounded-lg border border-surface-600 bg-surface-800 px-2 py-1 text-xs shadow-xl"
										>
											<Tooltip.Arrow
												class="[--arrow-background:var(--color-surface-800)] [--arrow-size:--spacing(2)]"
											>
												<Tooltip.ArrowTip />
											</Tooltip.Arrow>
											<span class="text-white">Update permissions</span>
										</Tooltip.Content>
									</Tooltip.Positioner>
								</Portal>
							</Tooltip>

							<!-- Set Primary Button -->
							<button
								onclick={() => setPrimaryCharacter(character.id)}
								class="btn btn-sm {isPrimary
									? 'preset-filled-warning-500'
									: 'preset-outlined-surface-500'}"
								disabled={isPrimary}
								title={isPrimary ? 'This is your primary character' : 'Set as primary character'}
							>
								<Star size={16} class={isPrimary ? 'fill-current' : ''} />
							</button>

							<!-- Remove Button -->
							<button
								onclick={() => openDeleteDialog(character)}
								class="btn preset-outlined-error-500 btn-sm"
								disabled={isPrimary || isOnlyCharacter}
								title={isPrimary
									? 'Cannot remove primary character'
									: isOnlyCharacter
										? 'Cannot remove your only character'
										: 'Remove character'}
							>
								<Trash2 size={16} />
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Add Character Button (bottom right) -->
		<div class="mt-4 flex justify-end">
			<button onclick={openLinkDialog} class="btn preset-outlined-primary-500 btn-sm">
				Link Character
			</button>
		</div>
	</div>
</section>

<!-- Delete Confirmation Dialog -->
<Dialog.Provider value={deleteDialog}>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-4">
			<Dialog.Content class="w-full max-w-md rounded-lg bg-black/50 p-6 shadow-xl backdrop-blur-sm">
				<Dialog.Title class="mb-2 text-xl font-bold">Remove Character</Dialog.Title>
				<Dialog.Description class="mb-6 text-surface-300">
					Are you sure you want to remove <strong>{characterToDelete?.name}</strong> from your account?
					This action cannot be undone.
				</Dialog.Description>
				<div class="flex justify-end gap-3">
					<Dialog.CloseTrigger class="btn preset-outlined-surface-500">Cancel</Dialog.CloseTrigger>
					<button onclick={confirmDelete} class="btn preset-filled-error-500" disabled={deleting}>
						{deleting ? 'Removing...' : 'Remove'}
					</button>
				</div>
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog.Provider>

<!-- Link Character Dialog -->
<ScopeSelectionDialog
	dialog={linkDialog}
	authPath="/users/characters/link"
	title="Link Character"
	description="Select which permissions to grant for this character:"
/>

<!-- Update Permissions Dialog -->
<ScopeSelectionDialog
	dialog={updateScopesDialog}
	authPath="/users/characters/link"
	title="Update Permissions"
	description="Update permissions for {characterToUpdate?.name ??
		'this character'}. This will re-authenticate with EVE Online."
	initialScopes={characterToUpdate?.scope_groups ?? []}
/>
