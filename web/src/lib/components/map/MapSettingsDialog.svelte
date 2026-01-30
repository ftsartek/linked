<script lang="ts">
	import { Dialog, Portal } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import { toaster } from '$lib/stores/toaster';
	import type { MapInfo, MapSettingsForm } from '$lib/helpers/mapTypes';

	interface Props {
		dialog: ReturnType<typeof import('@skeletonlabs/skeleton-svelte').useDialog>;
		map_id: string;
		mapInfo: MapInfo | null;
		open?: boolean;
		onsaved?: () => void;
	}

	let { dialog, map_id, mapInfo, open = false, onsaved }: Props = $props();

	// Internal state
	let saving = $state(false);
	let hasInitialized = $state(false);
	let form = $state<MapSettingsForm>({
		name: '',
		description: '',
		is_public: false,
		edge_type: 'default',
		rankdir: 'TB',
		auto_layout: false,
		node_sep: 50,
		rank_sep: 50,
		location_tracking_enabled: true
	});

	// Form validation
	const isNameValid = $derived(form.name.trim().length >= 4);
	const canSave = $derived(isNameValid && !saving);

	// Initialize form from mapInfo when dialog opens
	$effect(() => {
		if (open && mapInfo && !hasInitialized) {
			hasInitialized = true;
			form = {
				name: mapInfo.name,
				description: mapInfo.description ?? '',
				is_public: mapInfo.is_public,
				edge_type: mapInfo.edge_type as MapSettingsForm['edge_type'],
				rankdir: mapInfo.rankdir ?? 'TB',
				auto_layout: mapInfo.auto_layout,
				node_sep: mapInfo.node_sep,
				rank_sep: mapInfo.rank_sep,
				location_tracking_enabled: mapInfo.location_tracking_enabled
			};
		}
		if (!open) {
			hasInitialized = false;
		}
	});

	async function handleSave() {
		if (!isNameValid) return;

		saving = true;

		const { data, error } = await apiClient.PATCH('/maps/{map_id}', {
			params: { path: { map_id } },
			body: {
				name: form.name.trim(),
				description: form.description || null,
				is_public: form.is_public,
				edge_type: form.edge_type,
				location_tracking_enabled: form.location_tracking_enabled
			}
		});

		saving = false;

		if (error) {
			toaster.create({
				title: 'Error',
				description: 'detail' in error ? error.detail : 'Failed to save settings',
				type: 'error'
			});
			return;
		}

		if (data) {
			toaster.create({
				title: 'Settings Saved',
				description: 'Map settings updated successfully',
				type: 'success'
			});
		}

		dialog().setOpen(false);
		onsaved?.();
	}
</script>

<Dialog.Provider value={dialog}>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-4">
			<Dialog.Content class="w-full max-w-md rounded-lg bg-black/50 p-6 shadow-xl backdrop-blur-sm">
				<Dialog.Title class="mb-4 text-xl font-bold text-white">Map Settings</Dialog.Title>
				<div class="space-y-4">
					<label class="block">
						<span class="text-sm text-surface-300">Name</span>
						<input
							type="text"
							bind:value={form.name}
							required
							minlength="4"
							class="mt-1 w-full rounded border-2 bg-black px-3 py-2 text-white focus:outline-none {isNameValid
								? 'border-secondary-950 focus:border-primary-800'
								: 'border-error-500 focus:border-error-400'}"
						/>
						{#if !isNameValid && form.name.length > 0}
							<span class="text-xs text-error-500">Name must be at least 4 characters</span>
						{/if}
					</label>
					<label class="block">
						<span class="text-sm text-surface-300">Description</span>
						<textarea
							bind:value={form.description}
							class="mt-1 w-full rounded border-2 border-secondary-950 bg-black px-3 py-2 text-white focus:border-primary-800 focus:outline-none"
							rows="3"
						></textarea>
					</label>
					<label class="flex items-center gap-2">
						<input type="checkbox" bind:checked={form.is_public} class="rounded" />
						<span class="text-sm text-surface-300">Public Map</span>
					</label>
					<label class="block">
						<span class="text-sm text-surface-300">Edge Type</span>
						<select
							bind:value={form.edge_type}
							class="mt-1 w-full rounded border-2 border-secondary-950 bg-black px-3 py-2 text-white focus:border-primary-800 focus:outline-none"
						>
							<option value="default">Default (Bezier)</option>
							<option value="straight">Straight</option>
							<option value="step">Step</option>
							<option value="smoothstep">Smooth Step</option>
							<option value="simplebezier">Simple Bezier</option>
						</select>
					</label>
					<label class="flex items-center gap-2">
						<input type="checkbox" bind:checked={form.location_tracking_enabled} class="rounded" />
						<span class="text-sm text-surface-300">Enable Location Tracking</span>
					</label>
					<div class="mt-6 flex justify-end gap-3">
						<Dialog.CloseTrigger
							class="rounded bg-surface-600 px-4 py-2 text-white hover:bg-surface-500"
						>
							Cancel
						</Dialog.CloseTrigger>
						<button
							class="rounded bg-primary-500 px-4 py-2 text-white hover:bg-primary-400 disabled:opacity-50"
							onclick={handleSave}
							disabled={!canSave}
						>
							{saving ? 'Saving...' : 'Save'}
						</button>
					</div>
				</div>
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog.Provider>
