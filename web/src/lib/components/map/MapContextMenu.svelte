<script lang="ts">
	import SystemSearch from '../search/SystemSearch.svelte';
	import UnidentifiedSystemList from './UnidentifiedSystemList.svelte';
	import type { ContextMenuState } from '$lib/helpers/mapContextMenu';
	import { MASS_STATUS_OPTIONS, LIFETIME_STATUS_OPTIONS } from '$lib/helpers/mapContextMenu';
	import type { LifetimeStatus } from '$lib/helpers/mapTypes';

	interface Props {
		menu: ContextMenuState;
		isOwner: boolean;
		onAddSystem: () => void;
		onAddUnidentifiedSystem: () => void;
		onReplaceSystem: () => void;
		onRemoveNode: () => void;
		onToggleLock: () => void;
		onUpdateMassStatus: () => void;
		onUpdateLifetimeStatus: () => void;
		onReverseConnection: () => void;
		onRemoveEdge: () => void;
		onMassStatusSelect: (value: number) => void;
		onLifetimeStatusSelect: (value: LifetimeStatus) => void;
		onSystemSelect: (system: { id: number; name: string; class_name?: string | null }) => void;
		onCancel: () => void;
	}

	let {
		menu,
		isOwner,
		onAddSystem,
		onAddUnidentifiedSystem,
		onReplaceSystem,
		onRemoveNode,
		onToggleLock,
		onUpdateMassStatus,
		onUpdateLifetimeStatus,
		// eslint-disable-next-line @typescript-eslint/no-unused-vars
		onReverseConnection,
		onRemoveEdge,
		onMassStatusSelect,
		onLifetimeStatusSelect,
		onSystemSelect,
		onCancel
	}: Props = $props();
</script>

<div
	class="fixed z-50 min-w-48 rounded-lg bg-black/50 shadow-xl backdrop-blur-sm"
	style="left: {menu.x}px; top: {menu.y}px;"
>
	{#if menu.mode === 'pane-menu'}
		<div class="py-1">
			<button
				class="w-full px-4 py-2 text-left text-sm text-surface-100 hover:bg-primary-950/60"
				onclick={onAddSystem}
			>
				Add System
			</button>
			<button
				class="w-full px-4 py-2 text-left text-sm text-surface-100 hover:bg-primary-950/60"
				onclick={onAddUnidentifiedSystem}
			>
				Add Unidentified System
			</button>
		</div>
	{:else if menu.mode === 'node-menu'}
		<div class="py-1">
			<button
				class="w-full px-4 py-2 text-left text-sm text-white hover:bg-primary-950/60"
				onclick={onReplaceSystem}
			>
				Replace System
			</button>
			<button
				class="w-full px-4 py-2 text-left text-sm text-white hover:bg-primary-950/60"
				onclick={onRemoveNode}
			>
				Remove Node
			</button>
			{#if isOwner}
				<button
					class="w-full px-4 py-2 text-left text-sm text-white hover:bg-primary-950/60"
					onclick={onToggleLock}
				>
					{menu.isNodeLocked ? 'Unlock Node' : 'Lock Node'}
				</button>
			{/if}
		</div>
	{:else if menu.mode === 'edge-menu'}
		<div class="py-1">
			<button
				class="w-full px-4 py-2 text-left text-sm text-white hover:bg-primary-950/60"
				onclick={onUpdateMassStatus}
			>
				Update Mass Status
			</button>
			<button
				class="w-full px-4 py-2 text-left text-sm text-white hover:bg-primary-950/60"
				onclick={onUpdateLifetimeStatus}
			>
				Update Lifetime Status
			</button>
			<!-- TODO: Reverse Connection option hidden for now
			<button
				class="w-full px-4 py-2 text-left text-sm text-white hover:bg-primary-950/60"
				onclick={_onReverseConnection}
			>
				Reverse Connection
			</button>
			-->
			<button
				class="w-full px-4 py-2 text-left text-sm text-white hover:bg-primary-950/60"
				onclick={onRemoveEdge}
			>
				Remove Connection
			</button>
		</div>
	{:else if menu.mode === 'mass-status'}
		<div class="py-1">
			{#each MASS_STATUS_OPTIONS as option (option.value)}
				<button
					class="w-full px-4 py-2 text-left text-sm text-white hover:bg-primary-950/60"
					onclick={() => onMassStatusSelect(option.value)}
				>
					{option.label}
				</button>
			{/each}
		</div>
	{:else if menu.mode === 'lifetime-status'}
		<div class="py-1">
			{#each LIFETIME_STATUS_OPTIONS as option (option.value)}
				<button
					class="w-full px-4 py-2 text-left text-sm text-white hover:bg-primary-950/60"
					onclick={() => onLifetimeStatusSelect(option.value)}
				>
					{option.label}
				</button>
			{/each}
		</div>
	{:else if menu.mode === 'search'}
		<div class="p-2">
			<SystemSearch autofocus onselect={onSystemSelect} oncancel={onCancel} />
		</div>
	{:else if menu.mode === 'unidentified'}
		<div class="p-2">
			<UnidentifiedSystemList onselect={onSystemSelect} oncancel={onCancel} />
		</div>
	{/if}
</div>
