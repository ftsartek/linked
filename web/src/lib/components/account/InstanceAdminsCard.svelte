<script lang="ts">
	import { Dialog, Portal, Progress } from '@skeletonlabs/skeleton-svelte';
	import { useDialog } from '@skeletonlabs/skeleton-svelte';
	import { Crown, Trash2, ArrowRightLeft } from 'lucide-svelte';
	import UserSearch from '../search/UserSearch.svelte';
	import { apiClient } from '$lib/client/client';
	import { toaster } from '$lib/stores/toaster';
	import { user } from '$lib/stores/user';
	import { getCharacterPortrait } from '$lib/helpers/images';
	import type { components } from '$lib/client/schema';

	type AdminInfo = components['schemas']['AdminInfo'];
	type InstanceStatusResponse = components['schemas']['InstanceStatusResponse'];
	type UserSearchResult = components['schemas']['UserSearchResult'];

	// Loading states
	let loading = $state(true);

	// Data
	let admins = $state<AdminInfo[]>([]);
	let instanceStatus = $state<InstanceStatusResponse | null>(null);

	// Transfer ownership state
	let transferTargetAdmin = $state<AdminInfo | null>(null);
	let transferring = $state(false);
	const transferDialog = useDialog({ id: 'transfer-ownership-dialog' });

	// Derived
	let isOwner = $derived($user?.is_owner ?? false);

	async function loadData() {
		loading = true;

		const [statusRes, adminsRes] = await Promise.all([
			apiClient.GET('/admin/instance'),
			apiClient.GET('/admin/admins')
		]);

		instanceStatus = statusRes.data ?? null;
		admins = adminsRes.data?.admins ?? [];

		loading = false;
	}

	$effect(() => {
		loadData();
	});

	async function handleAddAdmin(selectedUser: UserSearchResult) {
		if (admins.some((a) => a.user_id === selectedUser.user_id)) {
			toaster.create({
				title: 'Already Admin',
				description: `${selectedUser.character_name} is already an administrator`,
				type: 'warning'
			});
			return;
		}

		if (instanceStatus && selectedUser.user_id === instanceStatus.owner_id) {
			toaster.create({
				title: 'Cannot Add Owner',
				description: 'The instance owner cannot be added as an admin',
				type: 'warning'
			});
			return;
		}

		const { error } = await apiClient.POST('/admin/admins', {
			body: { user_id: selectedUser.user_id }
		});

		if (error) {
			const message = 'detail' in error ? (error.detail as string) : 'Failed to add admin';
			toaster.create({ title: 'Error', description: message, type: 'error' });
			return;
		}

		admins = [
			...admins,
			{
				user_id: selectedUser.user_id,
				character_name: selectedUser.character_name,
				granted_by: null,
				date_created: null
			}
		];
		toaster.create({
			title: 'Success',
			description: `${selectedUser.character_name} is now an administrator`,
			type: 'success'
		});
	}

	async function removeAdmin(userId: string, characterName: string | null) {
		const { error } = await apiClient.DELETE('/admin/admins/{user_id}', {
			params: { path: { user_id: userId } }
		});

		if (error) {
			const message = 'detail' in error ? (error.detail as string) : 'Failed to remove admin';
			toaster.create({ title: 'Error', description: message, type: 'error' });
			return;
		}

		admins = admins.filter((a) => a.user_id !== userId);
		toaster.create({
			title: 'Success',
			description: `${characterName ?? 'User'} is no longer an administrator`,
			type: 'success'
		});
	}

	function openTransferDialog(admin: AdminInfo) {
		transferTargetAdmin = admin;
		transferDialog().setOpen(true);
	}

	async function confirmTransferOwnership() {
		if (!transferTargetAdmin) return;

		transferring = true;

		const { error } = await apiClient.POST('/admin/instance/transfer', {
			body: { new_owner_id: transferTargetAdmin.user_id }
		});

		if (error) {
			const message = 'detail' in error ? (error.detail as string) : 'Failed to transfer ownership';
			toaster.create({ title: 'Error', description: message, type: 'error' });
			transferring = false;
			return;
		}

		toaster.create({
			title: 'Ownership Transferred',
			description: `${transferTargetAdmin.character_name} is now the instance owner`,
			type: 'success'
		});

		// Refresh user state to reflect loss of owner status
		const { data: userData } = await apiClient.GET('/auth/me');
		user.set(userData ?? null);

		// Reload data to reflect new state
		await loadData();

		transferring = false;
		transferDialog().setOpen(false);
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
		<h2 class="text-xl font-semibold">Instance Administrators</h2>
		<p class="text-sm text-surface-400">
			{#if isOwner}
				Manage users who can administer this instance.
			{:else}
				View instance administrators.
			{/if}
		</p>
	</div>

	{#if loading}
		<div class="flex flex-1 items-center justify-center py-8"></div>
	{:else}
		<!-- Owner Info Banner -->
		{#if instanceStatus}
			<div class="mb-4 rounded-lg border-2 border-warning-900/50 bg-warning-950/30 p-3">
				<div class="flex items-center gap-2">
					<Crown size={16} class="text-warning-400" />
					<span class="text-sm font-medium text-warning-300">Instance Owner</span>
				</div>
				<span class="text-sm text-white">{instanceStatus.owner_name ?? 'Unknown'}</span>
			</div>
		{/if}

		<!-- Add Admin (owner only) -->
		{#if isOwner}
			<div class="mb-4">
				<UserSearch placeholder="Search users to add as admin..." onselect={handleAddAdmin} />
			</div>
		{/if}

		<!-- Admin List -->
		<div class="flex-1 overflow-auto">
			<div class="grid gap-3">
				{#each admins as admin (admin.user_id)}
					<div
						class="flex items-center gap-3 rounded-lg border-2 border-surface-900 bg-black/50 p-3"
					>
						{#if admin.character_id}
							<img
								src={getCharacterPortrait(admin.character_id, 64)}
								alt={admin.character_name ?? 'Unknown'}
								class="h-8 w-8 rounded-full"
							/>
						{/if}
						<div class="flex-1">
							<span class="font-medium">{admin.character_name ?? 'Unknown User'}</span>
						</div>
						{#if isOwner}
							<div class="flex items-center gap-2">
								<button
									onclick={() => openTransferDialog(admin)}
									class="btn preset-outlined-warning-500 btn-sm"
									title="Transfer ownership to this admin"
								>
									<ArrowRightLeft size={16} />
								</button>
								<button
									onclick={() => removeAdmin(admin.user_id, admin.character_name ?? null)}
									class="btn preset-outlined-error-500 btn-sm"
									title="Remove admin"
								>
									<Trash2 size={16} />
								</button>
							</div>
						{/if}
					</div>
				{:else}
					<p class="text-sm text-surface-400">No administrators configured</p>
				{/each}
			</div>
		</div>
	{/if}
</section>

<!-- Transfer Ownership Confirmation Dialog -->
<Dialog.Provider value={transferDialog}>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-4">
			<Dialog.Content class="w-full max-w-md rounded-lg bg-black/50 p-6 shadow-xl backdrop-blur-sm">
				<Dialog.Title class="mb-2 text-xl font-bold text-warning-400">
					Transfer Ownership
				</Dialog.Title>
				<div class="mb-4 rounded-lg bg-error-500/20 p-3 text-sm text-error-300">
					<strong>Warning:</strong> This action cannot be undone. You will lose owner privileges and become
					an administrator.
				</div>
				{#if transferTargetAdmin}
					<p class="mb-4 text-sm text-surface-300">
						Transfer ownership to <strong class="text-white"
							>{transferTargetAdmin.character_name}</strong
						>?
					</p>
				{/if}
				<div class="flex justify-end gap-3">
					<Dialog.CloseTrigger class="btn preset-outlined-surface-500">Cancel</Dialog.CloseTrigger>
					<button
						onclick={confirmTransferOwnership}
						class="btn preset-filled-warning-500"
						disabled={!transferTargetAdmin || transferring}
					>
						{transferring ? 'Transferring...' : 'Confirm Transfer'}
					</button>
				</div>
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog.Provider>
