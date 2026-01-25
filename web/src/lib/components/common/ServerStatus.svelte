<script lang="ts">
	import { serverStatus } from '$lib/stores/serverStatus';
	import { Portal, Tooltip } from '@skeletonlabs/skeleton-svelte';

	function formatPlayerCount(count: number): string {
		return count.toLocaleString();
	}

	const tooltipText = $derived.by(() => {
		if ($serverStatus === null) {
			return 'Loading server status...';
		}
		if (!$serverStatus.online) {
			return 'Tranquility is offline';
		}
		if ($serverStatus.vip) {
			return 'Tranquility is in VIP mode (restricted access)';
		}
		return 'Tranquility is online';
	});
</script>

<Tooltip positioning={{ placement: 'bottom' }}>
	<Tooltip.Trigger>
		<div class="flex cursor-default items-center gap-2 text-sm text-surface-400">
			{#if $serverStatus === null}
				<span class="text-surface-400">TQ</span><span>0</span>
			{:else if !$serverStatus.online}
				<span class="text-error-500">TQ</span>|<span>0</span>
			{:else if $serverStatus.vip}
				<span class="text-warning-500">TQ</span>
				{#if $serverStatus.players !== null && $serverStatus.players !== undefined}
					|<span class="text-surface-400">{formatPlayerCount($serverStatus.players)}</span>
				{/if}
			{:else}
				<span class="text-success-400">TQ</span>
				{#if $serverStatus.players !== null && $serverStatus.players !== undefined}
					|<span class="text-surface-400">{formatPlayerCount($serverStatus.players)}</span>
				{/if}
			{/if}
		</div>
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
				<span class="text-white">{tooltipText}</span>
			</Tooltip.Content>
		</Tooltip.Positioner>
	</Portal>
</Tooltip>
