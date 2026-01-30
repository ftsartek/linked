<script lang="ts">
	import { Dialog, Portal } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import { toaster } from '$lib/stores/toaster';

	interface Props {
		dialog: ReturnType<typeof import('@skeletonlabs/skeleton-svelte').useDialog>;
		oncreated?: (mapId: string) => void;
	}

	let { dialog, oncreated }: Props = $props();

	// Form state
	let name = $state('');
	let description = $state('');
	let is_public = $state(false);
	let edge_type = $state<'default' | 'straight' | 'step' | 'smoothstep' | 'simplebezier'>(
		'default'
	);
	let location_tracking_enabled = $state(true);
	let creating = $state(false);
	let error = $state<string | null>(null);

	// Form validation
	const isNameValid = $derived(name.trim().length >= 4);
	const canCreate = $derived(isNameValid && !creating);

	function resetForm() {
		name = '';
		description = '';
		is_public = false;
		edge_type = 'default';
		location_tracking_enabled = true;
		error = null;
	}

	async function handleCreate() {
		if (!isNameValid) {
			error = 'Name must be at least 4 characters';
			return;
		}

		creating = true;
		error = null;

		const { data, error: apiError } = await apiClient.POST('/maps', {
			body: {
				name: name.trim(),
				description: description.trim() || null,
				is_public,
				public_read_only: true,
				edge_type,
				rankdir: 'TB',
				auto_layout: false,
				node_sep: 100,
				rank_sep: 60,
				location_tracking_enabled
			}
		});

		creating = false;

		if (apiError) {
			error = 'detail' in apiError ? apiError.detail : 'Failed to create map';
			return;
		}

		if (data) {
			toaster.create({
				title: 'Map Created',
				description: `Map "${data.name}" created successfully`,
				type: 'success'
			});
			resetForm();
			dialog().setOpen(false);
			oncreated?.(data.id);
		}
	}
</script>

<Dialog.Provider value={dialog}>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-4">
			<Dialog.Content class="w-full max-w-md rounded-lg bg-black/50 p-6 shadow-xl backdrop-blur-sm">
				<Dialog.Title class="mb-4 text-xl font-bold text-white">Create New Map</Dialog.Title>
				<form
					onsubmit={async (e) => {
						e.preventDefault();
						await handleCreate();
					}}
					class="space-y-4"
				>
					<label class="block">
						<span class="text-sm text-surface-300">Name</span>
						<input
							type="text"
							bind:value={name}
							required
							minlength="4"
							class="mt-1 w-full rounded border-2 bg-black px-3 py-2 text-white focus:outline-none {isNameValid ||
							name.length === 0
								? 'border-primary-950 focus:border-primary-800'
								: 'border-error-500 focus:border-error-400'}"
							placeholder="My Map"
						/>
						{#if !isNameValid && name.length > 0}
							<span class="text-xs text-error-500">Name must be at least 4 characters</span>
						{/if}
					</label>
					<label class="block">
						<span class="text-sm text-surface-300">Description</span>
						<textarea
							bind:value={description}
							class="mt-1 w-full rounded border-2 border-primary-950 bg-black px-3 py-2 text-white focus:border-primary-800 focus:outline-none"
							placeholder="Optional description..."
							rows="3"
						></textarea>
					</label>
					<label class="flex items-center gap-2">
						<input type="checkbox" bind:checked={is_public} class="rounded" />
						<span class="text-sm text-surface-300">Public Map</span>
					</label>
					<label class="block">
						<span class="text-sm text-surface-300">Edge Type</span>
						<select
							bind:value={edge_type}
							class="mt-1 w-full rounded border-2 border-primary-950 bg-black px-3 py-2 text-white focus:border-primary-800 focus:outline-none"
						>
							<option value="default">Default (Bezier)</option>
							<option value="straight">Straight</option>
							<option value="step">Step</option>
							<option value="smoothstep">Smooth Step</option>
							<option value="simplebezier">Simple Bezier</option>
						</select>
					</label>
					<label class="flex items-center gap-2">
						<input type="checkbox" bind:checked={location_tracking_enabled} class="rounded" />
						<span class="text-sm text-surface-300">Enable Location Tracking</span>
					</label>
					{#if error}
						<div class="rounded-lg bg-error-500/20 p-3 text-sm text-error-500">
							{error}
						</div>
					{/if}
					<div class="mt-6 flex justify-end gap-3">
						<Dialog.CloseTrigger
							class="rounded bg-surface-600 px-4 py-2 text-white hover:bg-surface-500"
						>
							Cancel
						</Dialog.CloseTrigger>
						<button
							type="submit"
							class="rounded bg-primary-500 px-4 py-2 text-white hover:bg-primary-400 disabled:opacity-50"
							disabled={!canCreate}
						>
							{creating ? 'Creating...' : 'Create'}
						</button>
					</div>
				</form>
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog.Provider>
