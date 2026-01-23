<script lang="ts">
	import { classColour } from '$lib/helpers/renderClass';
	import type { components } from '$lib/client/schema';

	type WormholeSummary = components['schemas']['ListWormholesWormholeTypeSummaryResponseBody'];

	interface SystemClass {
		id: number;
		name: string;
	}

	// Class definitions for the matrix
	const CLASSES: SystemClass[] = [
		{ id: 1, name: 'C1' },
		{ id: 2, name: 'C2' },
		{ id: 3, name: 'C3' },
		{ id: 4, name: 'C4' },
		{ id: 5, name: 'C5' },
		{ id: 6, name: 'C6' },
		{ id: 7, name: 'HS' },
		{ id: 8, name: 'LS' },
		{ id: 9, name: 'NS' },
		{ id: 12, name: 'Thera' },
		{ id: 13, name: 'C13' },
		{ id: 25, name: 'Pochven' }
	];

	// Drifter wormhole destinations (grouped together)
	const DRIFTER_IDS = [14, 15, 16, 17, 18];
	const DRIFTER_NAMES: Record<number, string> = {
		14: 'Sentinel',
		15: 'Barbican',
		16: 'Vidette',
		17: 'Redoubt',
		18: 'Conflux'
	};

	// Special key for wandering wormholes (no specific source)
	const WANDERING_SOURCE = 'wandering';

	function getTargetName(targetClass: number | null | undefined): string {
		if (targetClass === null || targetClass === undefined) return '?';
		const cls = CLASSES.find((c) => c.id === targetClass);
		if (cls) return cls.name;
		const drifter = DRIFTER_NAMES[targetClass];
		if (drifter) return drifter;
		return '?';
	}

	interface Props {
		wormholes: WormholeSummary[];
		onselect: (wh: WormholeSummary) => void;
	}

	let { wormholes, onselect }: Props = $props();

	// Compute everything in a single derived to avoid reactivity issues
	const tableData = $derived.by(() => {
		const matrix: Record<string, WormholeSummary[]> = {};
		const wandering: Record<string, WormholeSummary[]> = {};

		// Build the matrix
		for (const wh of wormholes) {
			if (!wh.sources || wh.sources.length === 0) {
				const key = `${WANDERING_SOURCE}-${wh.target_class}`;
				if (!wandering[key]) wandering[key] = [];
				wandering[key].push(wh);
				continue;
			}

			for (const sourceId of wh.sources) {
				const key = `${sourceId}-${wh.target_class}`;
				if (!matrix[key]) matrix[key] = [];
				matrix[key].push(wh);
			}
		}

		// Sort wormholes within each cell
		for (const key of Object.keys(matrix)) {
			matrix[key]!.sort((a, b) => a.code.localeCompare(b.code));
		}
		for (const key of Object.keys(wandering)) {
			wandering[key]!.sort((a, b) => a.code.localeCompare(b.code));
		}

		// Helper to get cell data
		const getCell = (sourceId: number, targetId: number): WormholeSummary[] => {
			return matrix[`${sourceId}-${targetId}`] ?? [];
		};

		const getWanderingCell = (targetId: number): WormholeSummary[] => {
			return wandering[`${WANDERING_SOURCE}-${targetId}`] ?? [];
		};

		const getDrifterCell = (sourceId: number): WormholeSummary[] => {
			const result: WormholeSummary[] = [];
			for (const drifterId of DRIFTER_IDS) {
				const whs = matrix[`${sourceId}-${drifterId}`];
				if (whs) result.push(...whs);
			}
			return result.sort((a, b) => a.code.localeCompare(b.code));
		};

		const getWanderingDrifterCell = (): WormholeSummary[] => {
			const result: WormholeSummary[] = [];
			for (const drifterId of DRIFTER_IDS) {
				const whs = wandering[`${WANDERING_SOURCE}-${drifterId}`];
				if (whs) result.push(...whs);
			}
			return result.sort((a, b) => a.code.localeCompare(b.code));
		};

		// Determine visible columns (targets that have wormholes)
		const visibleTargets = CLASSES.filter((cls) => {
			for (const sourceClass of CLASSES) {
				if (getCell(sourceClass.id, cls.id).length > 0) return true;
			}
			if (getWanderingCell(cls.id).length > 0) return true;
			return false;
		});

		// Determine visible rows (sources that have wormholes)
		const visibleSources = CLASSES.filter((cls) => {
			for (const targetClass of CLASSES) {
				if (getCell(cls.id, targetClass.id).length > 0) return true;
			}
			if (getDrifterCell(cls.id).length > 0) return true;
			return false;
		});

		// Check if drifter column should show
		let showDrifter = false;
		for (const sourceClass of CLASSES) {
			if (getDrifterCell(sourceClass.id).length > 0) {
				showDrifter = true;
				break;
			}
		}
		if (!showDrifter && getWanderingDrifterCell().length > 0) {
			showDrifter = true;
		}

		// Check if wandering row should show
		let showWandering = false;
		for (const targetClass of CLASSES) {
			if (getWanderingCell(targetClass.id).length > 0) {
				showWandering = true;
				break;
			}
		}
		if (!showWandering && getWanderingDrifterCell().length > 0) {
			showWandering = true;
		}

		// Pre-compute all cell data for the template
		const rows = visibleSources.map((sourceClass) => ({
			sourceClass,
			cells: visibleTargets.map((targetClass) => ({
				targetClass,
				wormholes: getCell(sourceClass.id, targetClass.id)
			})),
			drifterCell: getDrifterCell(sourceClass.id)
		}));

		const wanderingRow = {
			cells: visibleTargets.map((targetClass) => ({
				targetClass,
				wormholes: getWanderingCell(targetClass.id)
			})),
			drifterCell: getWanderingDrifterCell()
		};

		return {
			visibleTargets,
			rows,
			wanderingRow,
			showDrifter,
			showWandering
		};
	});
</script>

{#snippet cell(cellWormholes: WormholeSummary[], isDrifter: boolean = false)}
	<td class="border border-surface-800 px-2 py-1 text-center align-middle">
		{#if cellWormholes.length > 0}
			<div class="flex flex-col items-center gap-0.5">
				{#each cellWormholes as wh (wh.id)}
					<button
						type="button"
						class="rounded px-1 text-left hover:bg-surface-800 {isDrifter
							? 'text-rose-400'
							: classColour(getTargetName(wh.target_class))}"
						onclick={() => onselect(wh)}
					>
						{wh.code}
					</button>
				{/each}
			</div>
		{/if}
	</td>
{/snippet}

<div class="overflow-x-auto">
	<table class="w-full border-collapse text-sm">
		<thead>
			<tr>
				<th class="border border-surface-800 bg-black/50 px-2 py-2 text-left text-surface-400">
					Source / Dest
				</th>
				{#each tableData.visibleTargets as cls (cls.id)}
					<th
						class="border border-surface-800 bg-black/50 px-2 py-2 text-center {classColour(
							cls.name
						)}"
					>
						{cls.name}
					</th>
				{/each}
				{#if tableData.showDrifter}
					<th class="border border-surface-800 bg-black/50 px-2 py-2 text-center text-rose-400">
						Drifter
					</th>
				{/if}
			</tr>
		</thead>
		<tbody>
			{#each tableData.rows as row (row.sourceClass.id)}
				<tr>
					<td
						class="border border-surface-800 bg-black/50 px-2 py-2 font-medium {classColour(
							row.sourceClass.name
						)}"
					>
						{row.sourceClass.name}
					</td>
					{#each row.cells as cellData (cellData.targetClass.id)}
						{@render cell(cellData.wormholes)}
					{/each}
					{#if tableData.showDrifter}
						{@render cell(row.drifterCell, true)}
					{/if}
				</tr>
			{/each}
			<!-- Wandering row -->
			{#if tableData.showWandering}
				<tr>
					<td class="border border-surface-800 bg-black/50 px-2 py-2 font-medium text-purple-400">
						Wandering
					</td>
					{#each tableData.wanderingRow.cells as cellData (cellData.targetClass.id)}
						{@render cell(cellData.wormholes)}
					{/each}
					{#if tableData.showDrifter}
						{@render cell(tableData.wanderingRow.drifterCell, true)}
					{/if}
				</tr>
			{/if}
		</tbody>
	</table>
</div>
