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

	import { Handle, Position } from '@xyflow/svelte';
	import { Portal, Tooltip } from '@skeletonlabs/skeleton-svelte';
	import { Sparkles } from 'lucide-svelte';

	type NodeData =
		components['schemas']['routes.maps.controller.MapController.create_nodeEnrichedNodeInfoResponseBody'];

	interface Props {
		data: NodeData;
	}

	let { data }: Props = $props();

	const hasModifiers = $derived(
		data.wh_effect_name || (data.class_name && isShattered(data.class_name, data.system_name))
	);
</script>

<div class="relative text-sm">
	<Handle type="target" position={Position.Left} />

	<div class="flex w-full flex-row items-baseline justify-between">
		<span class="font-semibold text-slate-100">{data.system_name}</span>
		{#if data.class_name && shouldShowSecStatus(data.class_name)}
			<div class="flex items-start gap-1">
				<span class="font-bold {classColour(data.class_name)}">{data.class_name}</span>
				<span class="text-xs font-normal {secStatusColour(data.security_status)}"
					>{data.security_status ? renderSecStatus(data.security_status) : ''}</span
				>
			</div>
		{:else if data.class_name}
			<span class="font-bold {classColour(data.class_name)}">{data.class_name}</span>
		{/if}
	</div>

	{#if hasModifiers}
		<div class="mt-1 flex items-center gap-2">
			{#if data.wh_effect_name}
				<Tooltip positioning={{ placement: 'bottom' }}>
					<Tooltip.Trigger>
						<span class={effectColour(data.wh_effect_name)}>
							<Sparkles size={14} />
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
										{#each Object.entries(data.wh_effect_buffs) as [name, value]}
											<div>{name}: {value > 0 ? '+' : ''}{value}%</div>
										{/each}
									</div>
								{/if}
								{#if data.wh_effect_debuffs && Object.keys(data.wh_effect_debuffs).length > 0}
									<div class="text-error-500">
										{#each Object.entries(data.wh_effect_debuffs) as [name, value]}
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
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" class="h-4 w-4">
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
		</div>
	{/if}

	<Handle type="source" position={Position.Right} />
</div>
