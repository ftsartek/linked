<script lang="ts">
	import type { components } from '$lib/client/schema';
	import {
		classColour,
		renderSecStatus,
		secStatusColour,
		shouldShowSecStatus
	} from '$lib/helpers/renderClass';
	import { Handle, Position } from '@xyflow/svelte';
	import { Sparkles } from 'lucide-svelte';

	type NodeData =
		components['schemas']['routes.maps.controller.MapController.create_nodeEnrichedNodeInfoResponseBody'];

	interface Props {
		data: NodeData;
	}

	let { data }: Props = $props();

	let showEffects = $state(false);
</script>

<div
	class="relative rounded-lg border border-surface-600 bg-surface-700 px-2 py-1 text-sm shadow-lg"
>
	<Handle type="target" position={Position.Left} />

	<div class="flex items-start gap-2">
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

		{#if data.wh_effect_name}
			<button
				class="ml-auto text-tertiary-500 hover:text-tertiary-400"
				onmouseenter={() => (showEffects = true)}
				onmouseleave={() => (showEffects = false)}
			>
				<Sparkles size={16} />
			</button>

			{#if showEffects}
				<div
					class="absolute top-0 left-full z-10 ml-2 min-w-40 rounded-lg border border-surface-600 bg-surface-800 p-2 text-xs shadow-xl"
				>
					<div class="mb-1 font-semibold text-white">{data.wh_effect_name}</div>
					{#if data.wh_effect_buffs && data.wh_effect_buffs.length > 0}
						<div class="text-success-500">
							{#each data.wh_effect_buffs as buff}
								<div>{JSON.stringify(buff)}</div>
							{/each}
						</div>
					{/if}
					{#if data.wh_effect_debuffs && data.wh_effect_debuffs.length > 0}
						<div class="text-error-500">
							{#each data.wh_effect_debuffs as debuff}
								<div>{JSON.stringify(debuff)}</div>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
		{/if}
	</div>

	<Handle type="source" position={Position.Right} />
</div>
