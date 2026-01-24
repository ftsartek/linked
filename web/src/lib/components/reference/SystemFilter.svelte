<script lang="ts">
	import MultiSelect from './MultiSelect.svelte';

	interface EffectOption {
		id: number;
		name: string;
	}

	export interface SystemFilters {
		classes: number[];
		effect: number | null;
		staticClass: number | null;
		shattered: boolean | null;
	}

	interface Props {
		effects: EffectOption[];
		onfilter: (filters: SystemFilters) => void;
	}

	let { effects, onfilter }: Props = $props();

	// Wormhole class options (hardcoded EVE constants)
	const classOptions = [
		{ value: 1, label: 'C1' },
		{ value: 2, label: 'C2' },
		{ value: 3, label: 'C3' },
		{ value: 4, label: 'C4' },
		{ value: 5, label: 'C5' },
		{ value: 6, label: 'C6' },
		{ value: 12, label: 'Thera' },
		{ value: 13, label: 'C13' },
		{ value: 14, label: 'Sentinel' },
		{ value: 15, label: 'Barbican' },
		{ value: 16, label: 'Vidette' },
		{ value: 17, label: 'Redoubt' },
		{ value: 18, label: 'Conflux' }
	];

	// Static target class options (what the static leads to)
	const staticClassOptions = [
		{ value: 7, label: 'Highsec' },
		{ value: 8, label: 'Lowsec' },
		{ value: 9, label: 'Nullsec' },
		{ value: 1, label: 'C1' },
		{ value: 2, label: 'C2' },
		{ value: 3, label: 'C3' },
		{ value: 4, label: 'C4' },
		{ value: 5, label: 'C5' },
		{ value: 6, label: 'C6' }
	];

	let selectedClasses = $state<number[]>([]);
	let selectedEffect = $state<string>('');
	let selectedStaticClass = $state<string>('');
	let selectedShattered = $state<string>('');

	const hasFilters = $derived(
		selectedClasses.length > 0 ||
			selectedEffect !== '' ||
			selectedStaticClass !== '' ||
			selectedShattered !== ''
	);

	function emitFilters() {
		onfilter({
			classes: selectedClasses,
			effect: selectedEffect ? parseInt(selectedEffect, 10) : null,
			staticClass: selectedStaticClass ? parseInt(selectedStaticClass, 10) : null,
			shattered: selectedShattered === '' ? null : selectedShattered === 'true'
		});
	}

	function clearFilters() {
		selectedClasses = [];
		selectedEffect = '';
		selectedStaticClass = '';
		selectedShattered = '';
		emitFilters();
	}

	function handleClassChange(classes: number[]) {
		selectedClasses = classes;
		emitFilters();
	}
</script>

<div class="mb-4 flex flex-wrap items-center gap-3">
	<MultiSelect
		options={classOptions}
		selected={selectedClasses}
		placeholder="All Classes"
		onchange={handleClassChange}
	/>

	<select
		bind:value={selectedEffect}
		onchange={emitFilters}
		class="rounded border-2 border-primary-950 bg-black px-3 py-2 text-sm text-white focus:border-primary-800 focus:outline-none"
	>
		<option value="">All Effects</option>
		{#each effects as effect (effect.id)}
			<option value={effect.id}>{effect.name}</option>
		{/each}
	</select>

	<select
		bind:value={selectedStaticClass}
		onchange={emitFilters}
		class="rounded border-2 border-primary-950 bg-black px-3 py-2 text-sm text-white focus:border-primary-800 focus:outline-none"
	>
		<option value="">Static To: Any</option>
		{#each staticClassOptions as s (s.value)}
			<option value={s.value}>{s.label}</option>
		{/each}
	</select>

	<select
		bind:value={selectedShattered}
		onchange={emitFilters}
		class="rounded border-2 border-primary-950 bg-black px-3 py-2 text-sm text-white focus:border-primary-800 focus:outline-none"
	>
		<option value="">Shattered: Any</option>
		<option value="true">Shattered Only</option>
		<option value="false">Non-Shattered Only</option>
	</select>

	{#if hasFilters}
		<button
			type="button"
			onclick={clearFilters}
			class="rounded bg-surface-700 px-3 py-2 text-sm text-white hover:bg-surface-600"
		>
			Clear Filters
		</button>
	{/if}
</div>
