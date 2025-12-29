<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { Sparkles } from 'lucide-svelte';

	interface NodeData {
		system_name: string;
		system_id: number;
		wh_class?: number | null;
		security_class?: string | null;
		wh_effect_name?: string | null;
		wh_effect_buffs?: Record<string, never>[] | null;
		wh_effect_debuffs?: Record<string, never>[] | null;
	}

	interface Props {
		data: NodeData;
	}

	let { data }: Props = $props();

	let showEffects = $state(false);

	function getClassDisplay(): string {
		if (data.wh_class != null) {
			return `C${data.wh_class}`;
		}
		if (data.security_class != null) {
			return data.security_class;
		}
		return '';
	}
</script>

<div
	class="relative rounded-lg border border-surface-600 bg-surface-700 px-3 py-2 text-sm shadow-lg"
>
	<Handle type="target" position={Position.Left} />

	<div class="flex items-center gap-2">
		<div class="flex flex-col">
			<span class="font-semibold text-white">{data.system_name}</span>
			{#if getClassDisplay()}
				<span class="text-xs text-surface-400">{getClassDisplay()}</span>
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
