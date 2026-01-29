<script lang="ts">
	import type { components } from '$lib/client/schema';
	import {
		classColour,
		effectColour,
		isShattered,
		renderSecStatus,
		secStatusColour,
		shouldShowSecStatus
	} from '$lib/helpers/renderClass';

	import { Handle, Position, useConnection, useEdges } from '@xyflow/svelte';
	import { Portal, Tooltip } from '@skeletonlabs/skeleton-svelte';
	import { Sparkles, Lock } from 'lucide-svelte';
	import CharacterIndicator from './CharacterIndicator.svelte';

	type NodeData = components['schemas']['EnrichedNodeInfo'];

	interface Props {
		data: NodeData;
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();

	const connection = useConnection();
	const edges = useEdges();

	// Check if a connection already exists between the source node and this node
	const alreadyConnected = $derived.by(() => {
		const sourceId = connection.current.fromHandle?.nodeId;
		if (!sourceId) return false;
		return edges.current.some(
			(edge) =>
				(edge.source === sourceId && edge.target === data.id) ||
				(edge.source === data.id && edge.target === sourceId)
		);
	});

	let isTarget = $derived(
		connection.current.inProgress &&
			connection.current.fromHandle?.nodeId !== data.id &&
			!alreadyConnected
	);

	const hasStatics = $derived(data.statics && data.statics.length > 0);
	const hasCharacters = $derived(data.characters && data.characters.length > 0);
</script>

<div
	class="relative box-border flex h-20 w-40 flex-col overflow-hidden rounded-md border-2 bg-surface-900 p-2 text-sm {isTarget
		? 'border-dashed border-primary-500'
		: selected
			? 'border-primary-800'
			: 'border-surface-800'}"
>
	<!-- Target handles: conditionally rendered based on connection state -->
	{#if !isTarget}
		<Handle type="target" position={Position.Top} class="h-1! w-1! opacity-0!" />
	{:else}
		<!-- When connecting: full overlay handle - the entire node becomes a drop target -->
		<Handle
			type="target"
			position={Position.Top}
			class="h-20! w-40! translate-y-10! rounded-md! bg-transparent!"
		/>
	{/if}

	<!-- Top row: system name (left) and class (right) -->
	<div class="flex items-baseline justify-between">
		<span class="truncate text-[1.085rem] font-semibold text-slate-100">{data.system_name}</span>
		{#if data.class_name && shouldShowSecStatus(data.class_name)}
			<div class="flex shrink-0 items-baseline gap-0.5">
				<span class="text-[1.085rem] font-bold {classColour(data.class_name)}"
					>{data.class_name}</span
				>
				<span class="text-xs {secStatusColour(data.security_status)}"
					>{data.security_status ? renderSecStatus(data.security_status) : ''}</span
				>
			</div>
		{:else if data.class_name}
			<span class="shrink-0 text-[1.085rem] font-bold {classColour(data.class_name)}"
				>{data.class_name}</span
			>
		{/if}
	</div>

	<!-- Bottom row: statics (left) and modifiers (right) - pushed to bottom -->
	<div class="mt-auto flex items-center justify-between">
		<!-- Statics (bottom left) -->
		<div class="flex items-center gap-1">
			{#if hasStatics}
				{#each data.statics! as static_info (static_info.code)}
					<Tooltip positioning={{ placement: 'bottom' }}>
						<Tooltip.Trigger>
							<span class={classColour(static_info.target_class_name ?? '')}>
								{static_info.target_class_name}
							</span>
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
									<span class="text-white">{static_info.code}</span>
								</Tooltip.Content>
							</Tooltip.Positioner>
						</Portal>
					</Tooltip>
				{/each}
			{/if}
		</div>

		<!-- Modifiers (bottom right) -->
		<div class="flex items-center gap-1">
			{#if hasCharacters}
				<CharacterIndicator characters={data.characters!} />
			{/if}

			{#if data.wh_effect_name}
				<Tooltip positioning={{ placement: 'bottom' }}>
					<Tooltip.Trigger>
						<span class={effectColour(data.wh_effect_name)}>
							<Sparkles size={17} />
						</span>
					</Tooltip.Trigger>
					<Portal>
						<Tooltip.Positioner>
							<Tooltip.Content
								class="z-10 min-w-40 rounded-lg border border-surface-600 bg-surface-800 p-2 text-xs shadow-xl"
							>
								<Tooltip.Arrow
									class="[--arrow-background:var(--color-surface-800)] [--arrow-size:--spacing(2)]"
								>
									<Tooltip.ArrowTip />
								</Tooltip.Arrow>
								<div class="mb-1 font-semibold text-white">{data.wh_effect_name}</div>
								{#if data.wh_effect_buffs && Object.keys(data.wh_effect_buffs).length > 0}
									<div class="text-success-500">
										{#each Object.entries(data.wh_effect_buffs) as [name, value] (name)}
											<div>{name}: {value > 0 ? '+' : ''}{value}%</div>
										{/each}
									</div>
								{/if}
								{#if data.wh_effect_debuffs && Object.keys(data.wh_effect_debuffs).length > 0}
									<div class="text-error-500">
										{#each Object.entries(data.wh_effect_debuffs) as [name, value] (name)}
											<div>{name}: {value > 0 ? '+' : ''}{value}%</div>
										{/each}
									</div>
								{/if}
							</Tooltip.Content>
						</Tooltip.Positioner>
					</Portal>
				</Tooltip>
			{/if}

			{#if data.class_name && isShattered(data.class_name, data.system_name)}
				<Tooltip positioning={{ placement: 'bottom' }}>
					<Tooltip.Trigger>
						<span class="text-slate-400">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" class="h-[20px] w-[20px]">
								<path
									d="M32 4 A28 28 0 1 0 52 52 L44 42 L38 46 L32 32 L36 24 L32 4Z"
									fill="currentColor"
								/>
								<path d="M46 2 Q52 4, 54 10 L48 14 L44 8 Z" fill="currentColor" />
								<path d="M56 14 Q60 20, 58 26 L52 24 L54 18 Z" fill="currentColor" />
								<path d="M48 26 L52 30 L48 34 L44 30 Z" fill="currentColor" />
							</svg>
						</span>
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
								<span class="text-white">Shattered</span>
							</Tooltip.Content>
						</Tooltip.Positioner>
					</Portal>
				</Tooltip>
			{/if}

			{#if data.locked}
				<Tooltip positioning={{ placement: 'bottom' }}>
					<Tooltip.Trigger>
						<span class="text-slate-400">
							<Lock size={15} />
						</span>
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
								<span class="text-white">Locked</span>
							</Tooltip.Content>
						</Tooltip.Positioner>
					</Portal>
				</Tooltip>
			{/if}
		</div>
	</div>

	<!-- Visible source handle - 2x4px box at bottom for initiating connections -->
	<Handle
		type="source"
		position={Position.Bottom}
		class="h-4! w-10! rounded-xs! border! border-surface-700! bg-surface-900!"
	/>
</div>
