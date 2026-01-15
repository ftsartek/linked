<script lang="ts">
	import SystemSearch from '../search/SystemSearch.svelte';
	import WormholeSearch from '../search/WormholeSearch.svelte';
	import UnidentifiedSystemList from './UnidentifiedSystemList.svelte';
	import type { ContextMenuState } from '$lib/helpers/mapContextMenu';
	import { MASS_STATUS_OPTIONS, LIFETIME_STATUS_OPTIONS } from '$lib/helpers/mapContextMenu';
	import type { LifetimeStatus } from '$lib/helpers/mapTypes';
	import type { components } from '$lib/client/schema';

	type WormholeSearchResult =
		components['schemas']['SearchWormholesWormholeSearchResultResponseBody'];

	interface Props {
		menu: ContextMenuState;
		isOwner: boolean;
		onAddSystem: () => void;
		onAddUnidentifiedSystem: () => void;
		onReplaceSystem: () => void;
		onRemoveNode: () => void;
		onToggleLock: () => void;
		onAddConnection: () => void;
		onUpdateMassStatus: () => void;
		onUpdateLifetimeStatus: () => void;
		onReverseConnection: () => void;
		onRemoveEdge: () => void;
		onSetWormholeType: () => void;
		onMassStatusSelect: (value: number) => void;
		onLifetimeStatusSelect: (value: LifetimeStatus) => void;
		onWormholeTypeSelect: (wormhole: WormholeSearchResult) => void;
		onConnectionWormholeSelect: (wormhole: WormholeSearchResult) => void;
		onConnectionSystemSelect: (system: {
			id: number;
			name: string;
			class_name?: string | null;
		}) => void;
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
		onAddConnection,
		onUpdateMassStatus,
		onUpdateLifetimeStatus,
		onReverseConnection,
		onRemoveEdge,
		onSetWormholeType,
		onMassStatusSelect,
		onLifetimeStatusSelect,
		onWormholeTypeSelect,
		onConnectionWormholeSelect,
		onConnectionSystemSelect,
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
				onclick={onAddConnection}
			>
				Add Connection
			</button>
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
			<button
				class="w-full px-4 py-2 text-left text-sm text-white hover:bg-primary-950/60"
				onclick={onReverseConnection}
			>
				Flip Connection
			</button>
			<button
				class="w-full px-4 py-2 text-left text-sm text-white hover:bg-primary-950/60"
				onclick={onSetWormholeType}
			>
				Set Wormhole Type
			</button>
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
	{:else if menu.mode === 'wormhole-type'}
		<div class="p-2">
			<WormholeSearch
				placeholder="Search wormhole type..."
				source_class={menu.sourceSystemClass}
				target_class={menu.targetSystemClass}
				autoSearch={true}
				onselect={onWormholeTypeSelect}
			/>
		</div>
	{:else if menu.mode === 'add-connection-type'}
		<div class="p-2">
			<WormholeSearch
				placeholder="Select wormhole type..."
				source_class={menu.sourceSystemClass}
				autoSearch={true}
				onselect={onConnectionWormholeSelect}
			/>
		</div>
	{:else if menu.mode === 'add-connection-system'}
		<div class="p-2">
			<SystemSearch autofocus onselect={onConnectionSystemSelect} oncancel={onCancel} />
		</div>
	{/if}
</div>
