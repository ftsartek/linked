<script lang="ts">
	import { Progress } from '@skeletonlabs/skeleton-svelte';
	import { Trash2, Plus, X, Check, Pen } from 'lucide-svelte';
	import { apiClient } from '$lib/client/client';
	import { mapSelection } from '$lib/stores/mapSelection';
	import type { components } from '$lib/client/schema';
	import { SvelteDate } from 'svelte/reactivity';

	type EnrichedNoteInfo = components['schemas']['EnrichedNoteInfo'];

	let notes = $state<EnrichedNoteInfo[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);

	// Time unit options for expiry
	type TimeUnit = 'minutes' | 'hours' | 'days' | 'months' | 'years';
	const timeUnits: { value: TimeUnit; label: string }[] = [
		{ value: 'minutes', label: 'Minutes' },
		{ value: 'hours', label: 'Hours' },
		{ value: 'days', label: 'Days' },
		{ value: 'months', label: 'Months' },
		{ value: 'years', label: 'Years' }
	];

	// Editing state
	let editingNoteId = $state<string | null>(null);
	let editTitle = $state('');
	let editContent = $state('');
	let editExpiryAmount = $state<number | null>(null);
	let editExpiryUnit = $state<TimeUnit>('hours');

	// Creating state
	let creating = $state(false);
	let newTitle = $state('');
	let newContent = $state('');
	let newExpiryAmount = $state<number | null>(null);
	let newExpiryUnit = $state<TimeUnit>('hours');

	// Track loaded state to avoid duplicate fetches
	let lastLoadedSystemId: number | null = null;
	let lastRefreshTrigger: number = 0;

	// Reactive: fetch notes when selected node changes or refresh triggered
	$effect(() => {
		const state = $mapSelection;
		const systemId = state.selectedNode?.system_id;
		const mapId = state.mapId;
		const refreshTrigger = state.noteRefreshTrigger;

		if (systemId && mapId) {
			if (systemId !== lastLoadedSystemId || refreshTrigger !== lastRefreshTrigger) {
				lastLoadedSystemId = systemId;
				lastRefreshTrigger = refreshTrigger;
				loadNotes(mapId, systemId);
			}
		} else if (!systemId) {
			lastLoadedSystemId = null;
			notes = [];
			cancelEdit();
			cancelCreate();
		}
	});

	async function loadNotes(mapId: string, systemId: number) {
		loading = true;
		error = null;

		const { data, error: apiError } = await apiClient.GET(
			'/maps/{map_id}/systems/{system_id}/notes',
			{
				params: { path: { map_id: mapId, system_id: systemId } }
			}
		);

		if (apiError) {
			error = 'Failed to load notes';
			loading = false;
			return;
		}

		if (data) {
			notes = data.notes;
		}

		loading = false;
	}

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString(undefined, {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatExpiry(dateVal: string | Date | null | undefined): string | null {
		if (!dateVal) return null;
		const date = typeof dateVal === 'string' ? new Date(dateVal) : dateVal;
		const now = new Date();
		let diffMs = date.getTime() - now.getTime();

		if (diffMs < 0) return 'Expired';
		if (diffMs < 60 * 1000) return 'Expires soon';

		const years = Math.floor(diffMs / (1000 * 60 * 60 * 24 * 365));
		diffMs -= years * 1000 * 60 * 60 * 24 * 365;
		const months = Math.floor(diffMs / (1000 * 60 * 60 * 24 * 30));
		diffMs -= months * 1000 * 60 * 60 * 24 * 30;
		const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
		diffMs -= days * 1000 * 60 * 60 * 24;
		const hours = Math.floor(diffMs / (1000 * 60 * 60));
		diffMs -= hours * 1000 * 60 * 60;
		const minutes = Math.floor(diffMs / (1000 * 60));

		const parts: string[] = [];
		if (years > 0) parts.push(`${years}y`);
		if (months > 0) parts.push(`${months}mo`);
		if (days > 0) parts.push(`${days}d`);
		if (hours > 0) parts.push(`${hours}h`);
		if (minutes > 0) parts.push(`${minutes}m`);

		// Show up to two largest units
		const display = parts.slice(0, 2).join(' ');
		return `Expires in ${display}`;
	}

	function calculateExpiryDate(amount: number | null, unit: TimeUnit): string | null {
		if (amount === null || amount <= 0) return null;

		const now = new SvelteDate();
		switch (unit) {
			case 'minutes':
				now.setMinutes(now.getMinutes() + amount);
				break;
			case 'hours':
				now.setHours(now.getHours() + amount);
				break;
			case 'days':
				now.setDate(now.getDate() + amount);
				break;
			case 'months':
				now.setMonth(now.getMonth() + amount);
				break;
			case 'years':
				now.setFullYear(now.getFullYear() + amount);
				break;
		}
		return now.toISOString();
	}

	function expiryToTimedelta(dateVal: string | Date | null | undefined): {
		amount: number | null;
		unit: TimeUnit;
	} {
		if (!dateVal) return { amount: null, unit: 'hours' };

		const date = typeof dateVal === 'string' ? new Date(dateVal) : dateVal;
		const now = new Date();
		const diffMs = date.getTime() - now.getTime();

		if (diffMs <= 0) return { amount: null, unit: 'hours' };

		const diffMinutes = Math.round(diffMs / (1000 * 60));
		const diffHours = Math.round(diffMs / (1000 * 60 * 60));
		const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
		const diffMonths = Math.round(diffDays / 30);
		const diffYears = Math.round(diffDays / 365);

		// Choose the most appropriate unit
		if (diffYears >= 1 && diffDays % 365 < 15) return { amount: diffYears, unit: 'years' };
		if (diffMonths >= 1 && diffDays % 30 < 5) return { amount: diffMonths, unit: 'months' };
		if (diffDays >= 1) return { amount: diffDays, unit: 'days' };
		if (diffHours >= 1) return { amount: diffHours, unit: 'hours' };
		return { amount: diffMinutes, unit: 'minutes' };
	}

	// Start editing a note
	function startEdit(note: EnrichedNoteInfo) {
		editingNoteId = note.id;
		editTitle = note.title || '';
		editContent = note.content;
		// Convert existing expiry to timedelta
		const timedelta = expiryToTimedelta(note.date_expires);
		editExpiryAmount = timedelta.amount;
		editExpiryUnit = timedelta.unit;
		cancelCreate();
	}

	function cancelEdit() {
		editingNoteId = null;
		editTitle = '';
		editContent = '';
		editExpiryAmount = null;
		editExpiryUnit = 'hours';
	}

	async function saveEdit() {
		const state = $mapSelection;
		if (!state.mapId || !editingNoteId) return;

		const expiresDate = calculateExpiryDate(editExpiryAmount, editExpiryUnit);

		await apiClient.PATCH('/maps/{map_id}/notes/{note_id}', {
			params: { path: { map_id: state.mapId, note_id: editingNoteId } },
			body: {
				title: editTitle || null,
				content: editContent,
				date_expires: expiresDate
			}
		});

		cancelEdit();
		// SSE will trigger refresh
	}

	// Start creating a new note
	function startCreate() {
		creating = true;
		newTitle = '';
		newContent = '';
		newExpiryAmount = null;
		newExpiryUnit = 'hours';
		cancelEdit();
	}

	function cancelCreate() {
		creating = false;
		newTitle = '';
		newContent = '';
		newExpiryAmount = null;
		newExpiryUnit = 'hours';
	}

	async function saveCreate() {
		const state = $mapSelection;
		if (!state.mapId || !state.selectedNode) return;

		const expiresDate = calculateExpiryDate(newExpiryAmount, newExpiryUnit);

		await apiClient.POST('/maps/{map_id}/notes', {
			params: { path: { map_id: state.mapId } },
			body: {
				solar_system_id: state.selectedNode.system_id,
				title: newTitle || null,
				content: newContent,
				date_expires: expiresDate
			}
		});

		cancelCreate();
		// SSE will trigger refresh
	}

	async function deleteNote(noteId: string) {
		const state = $mapSelection;
		if (!state.mapId) return;

		await apiClient.DELETE('/maps/{map_id}/notes/{note_id}', {
			params: { path: { map_id: state.mapId, note_id: noteId } }
		});
		// SSE will trigger refresh
	}
</script>

<div
	class="relative flex h-full min-h-80 flex-col rounded-xl border-0 bg-black/75 backdrop-blur-2xl"
>
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
	<div
		class="flex w-full flex-row items-center justify-between border-b-2 border-primary-950/50 px-3 py-2"
	>
		<h3 class="text-sm font-semibold text-white">Notes</h3>
		{#if $mapSelection.selectedNode}
			<p class="text-sm font-semibold text-surface-400">{$mapSelection.selectedNode.system_name}</p>
		{/if}
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-auto p-2">
		{#if !$mapSelection.selectedNode}
			<div class="flex h-full items-center justify-center">
				<p class="text-sm text-surface-400">Select a node to view notes</p>
			</div>
		{:else if loading}
			<div class="flex h-full items-center justify-center"></div>
		{:else if error}
			<div class="flex h-full items-center justify-center">
				<p class="text-sm text-error-500">{error}</p>
			</div>
		{:else}
			<div class="space-y-2">
				{#each notes as note (note.id)}
					{@const isEditing = editingNoteId === note.id}
					{@const expiryText = formatExpiry(note.date_expires)}

					<div class="rounded border border-none bg-primary-950/30 p-2">
						{#if isEditing}
							<!-- Editing mode -->
							<div class="space-y-2">
								<input
									type="text"
									class="w-full rounded border border-black bg-black px-2 py-1 text-xs text-white placeholder-surface-500"
									placeholder="Title (optional)"
									bind:value={editTitle}
								/>
								<textarea
									class="w-full resize-none rounded border border-black bg-black px-2 py-1 text-xs text-white placeholder-surface-500"
									placeholder="Note content..."
									rows="3"
									bind:value={editContent}
								></textarea>
								<div class="flex items-center gap-2">
									<span class="text-xs text-surface-400">Expires in:</span>
									<input
										type="number"
										min="1"
										class="w-16 rounded border border-black bg-black px-2 py-1 text-xs text-white"
										placeholder="--"
										bind:value={editExpiryAmount}
									/>
									<select
										class="flex-1 rounded border border-black bg-black px-2 py-1 text-xs text-white"
										bind:value={editExpiryUnit}
									>
										{#each timeUnits as unit (unit)}
											<option value={unit.value}>{unit.label}</option>
										{/each}
									</select>
								</div>
								<div class="flex justify-end gap-2">
									<button
										type="button"
										class="rounded p-1 text-surface-400 hover:bg-surface-800 hover:text-white"
										onclick={cancelEdit}
										title="Cancel"
									>
										<X size={14} />
									</button>
									<button
										type="button"
										class="rounded p-1 text-primary-400 hover:bg-primary-950 hover:text-primary-300"
										onclick={saveEdit}
										disabled={!editContent.trim()}
										title="Save"
									>
										<Check size={14} />
									</button>
								</div>
							</div>
						{:else}
							<!-- View mode -->
							<div class="space-y-1">
								{#if note.title}
									<div class="text-xs font-semibold text-white">{note.title}</div>
								{/if}
								<div class="text-xs whitespace-pre-wrap text-surface-300">{note.content}</div>
								<div class="flex items-center justify-between pt-1">
									<div class="text-[10px] text-surface-500">
										<span>
											<span class="text-secondary-300/60">{note.created_by_name}</span> - {formatDate(
												note.date_created
											)}
											{#if note.updated_by_name && note.updated_by !== note.created_by}
												- edited by {note.updated_by_name}
											{/if}
											{#if expiryText}
												- <span class="text-warning-300/60">{expiryText}</span>
											{/if}
										</span>
									</div>
									{#if !$mapSelection.isReadOnly}
										<div class="flex gap-1">
											<button
												type="button"
												class="rounded p-1 text-surface-500 hover:bg-surface-800 hover:text-white"
												onclick={() => startEdit(note)}
												title="Edit note"
											>
												<Pen size={12} />
											</button>
											<button
												type="button"
												class="rounded p-1 text-surface-500 hover:bg-error-950 hover:text-error-400"
												onclick={() => deleteNote(note.id)}
												title="Delete note"
											>
												<Trash2 size={12} />
											</button>
										</div>
									{/if}
								</div>
							</div>
						{/if}
					</div>
				{/each}

				{#if creating}
					<!-- Creating new note -->
					<div class="rounded border border-none bg-primary-950/30 p-2">
						<div class="space-y-2">
							<input
								type="text"
								class="w-full rounded border border-black bg-black px-2 py-1 text-xs text-white placeholder-surface-500"
								placeholder="Title (optional)"
								bind:value={newTitle}
							/>
							<textarea
								class="w-full resize-none rounded border border-black bg-black px-2 py-1 text-xs text-white placeholder-surface-500"
								placeholder="Note content..."
								rows="3"
								bind:value={newContent}
							></textarea>
							<div class="flex items-center gap-2">
								<span class="text-xs text-surface-400">Expires in:</span>
								<input
									type="number"
									min="1"
									class="w-16 rounded border border-black bg-black px-2 py-1 text-xs text-white"
									placeholder="--"
									bind:value={newExpiryAmount}
								/>
								<select
									class="flex-1 rounded border border-black bg-black px-2 py-1 text-xs text-white"
									bind:value={newExpiryUnit}
								>
									{#each timeUnits as unit (unit)}
										<option value={unit.value}>{unit.label}</option>
									{/each}
								</select>
							</div>
							<div class="flex justify-end gap-2">
								<button
									type="button"
									class="rounded p-1 text-surface-400 hover:bg-surface-800 hover:text-white"
									onclick={cancelCreate}
									title="Cancel"
								>
									<X size={14} />
								</button>
								<button
									type="button"
									class="rounded p-1 text-primary-400 hover:bg-primary-950 hover:text-primary-300"
									onclick={saveCreate}
									disabled={!newContent.trim()}
									title="Save"
								>
									<Check size={14} />
								</button>
							</div>
						</div>
					</div>
				{/if}

				{#if notes.length === 0 && !creating}
					<div class="flex h-full items-center justify-center py-4">
						<p class="text-sm text-surface-400">No notes found</p>
					</div>
				{/if}

				<!-- Add note button -->
				{#if !$mapSelection.isReadOnly && !creating}
					<button
						type="button"
						class="flex w-full items-center justify-center gap-1 rounded border border-dashed border-surface-700 py-2 text-xs text-surface-400 hover:border-primary-500 hover:text-primary-400"
						onclick={startCreate}
					>
						<Plus size={14} />
						<span>Add Note</span>
					</button>
				{/if}
			</div>
		{/if}
	</div>
</div>
