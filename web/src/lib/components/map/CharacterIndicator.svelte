<script lang="ts">
	import { Portal, Tooltip } from '@skeletonlabs/skeleton-svelte';
	import { Users } from 'lucide-svelte';
	import type { components } from '$lib/client/schema';
	import { formatTimeAgo } from '$lib/helpers/formatTime';

	type NodeCharacterLocation = components['schemas']['NodeCharacterLocation'];

	interface Props {
		characters: NodeCharacterLocation[];
	}

	let { characters }: Props = $props();

	const count = $derived(characters.length);
	const hasOnline = $derived(characters.some((c) => c.online === true));
</script>

<Tooltip positioning={{ placement: 'bottom' }}>
	<Tooltip.Trigger>
		<span
			class="flex items-center gap-0.5 text-[11px] font-medium {hasOnline
				? 'text-success-500/70'
				: 'text-surface-500'}"
		>
			<Users size={12} />
			{count}
		</span>
	</Tooltip.Trigger>
	<Portal>
		<Tooltip.Positioner>
			<Tooltip.Content class="z-10 rounded-lg bg-black p-2 text-xs shadow-xl">
				<Tooltip.Arrow class="[--arrow-background:var(--color-black)] [--arrow-size:--spacing(2)]">
					<Tooltip.ArrowTip />
				</Tooltip.Arrow>
				<div class="flex flex-col gap-1">
					{#each characters as char (char.character_name)}
						<div class="flex items-center gap-1.5">
							{#if char.online === true}
								<span class="size-1.5 shrink-0 rounded-full bg-success-500"></span>
							{:else if char.online === false}
								<span class="size-1.5 shrink-0 rounded-full bg-surface-600"></span>
							{/if}
							<span class="text-primary-400/80">{char.character_name}</span>
							{#if char.docked}
								<span class="text-primary-400/40">(docked)</span>
							{/if}
							{#if char.ship_type_name}
								<span class="text-primary-400/40">· {char.ship_type_name}</span>
							{/if}
							{#if char.last_updated}
								<span class="text-primary-400/30">{formatTimeAgo(char.last_updated)}</span>
							{/if}
						</div>
					{/each}
				</div>
			</Tooltip.Content>
		</Tooltip.Positioner>
	</Portal>
</Tooltip>
