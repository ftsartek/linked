<script lang="ts">
	import { Progress } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import { mapSelection } from '$lib/stores/mapSelection';
	import type { components } from '$lib/client/schema';
	import WormholeSearch from '../search/WormholeSearch.svelte';
	import SystemSearch from '../search/SystemSearch.svelte';
	import { getSystemClassId } from '$lib/helpers/mapHelpers';

	type EnrichedSignatureInfo = components['schemas']['EnrichedSignatureInfo'];
	type BulkSignatureItem = components['schemas']['BulkSignatureItem'];
	type NodeConnectionInfo = components['schemas']['NodeConnectionInfo'];
	type WormholeSearchResult =
		components['schemas']['SearchWormholesWormholeSearchResultResponseBody'];
	type UnidentifiedSystem =
		components['schemas']['ListUnidentifiedSystemsSystemSearchResponse_0SystemSearchResultResponseBody'];

	// Available subgroups for signatures
	const SUBGROUPS = [
		{ value: '', label: 'Unknown' },
		{ value: 'wormhole', label: 'Wormhole' },
		{ value: 'combat', label: 'Combat' },
		{ value: 'data', label: 'Data' },
		{ value: 'relic', label: 'Relic' },
		{ value: 'gas', label: 'Gas' },
		{ value: 'ore', label: 'Ore' }
	];

	let signatures = $state<EnrichedSignatureInfo[]>([]);
	let connections = $state<NodeConnectionInfo[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);

	// Track expanded signatures for editing
	let expandedSigId = $state<string | null>(null);
	let creatingConnection = $state<string | null>(null); // signature ID being connected
	let connectionStep = $state<'type' | 'system' | null>(null);
	let pendingConnectionWormhole = $state<WormholeSearchResult | null>(null);

	// Unidentified systems for creating connections to unknown destinations
	let unidentifiedSystems = $state<UnidentifiedSystem[]>([]);

	// Track the last loaded state to avoid duplicate fetches
	let lastLoadedNodeId: string | null = null;
	let lastRefreshTrigger: number = 0;

	// Load unidentified systems once on mount
	$effect(() => {
		loadUnidentifiedSystems();
	});

	async function loadUnidentifiedSystems() {
		const { data } = await apiClient.GET('/universe/systems/unidentified');
		unidentifiedSystems = data?.systems ?? [];
	}

	function getUnidentifiedSystemForClass(
		targetClass: number | null | undefined
	): UnidentifiedSystem | undefined {
		if (targetClass == null) {
			// Return the "unknown" unidentified system (class 0)
			return unidentifiedSystems.find((s) => s.system_class === 0);
		}
		return unidentifiedSystems.find((s) => s.system_class === targetClass);
	}

	// Reactive: fetch signatures and connections when selected node changes or refresh triggered
	$effect(() => {
		const state = $mapSelection;
		const nodeId = state.selectedNode?.id;
		const mapId = state.mapId;
		const refreshTrigger = state.signatureRefreshTrigger;

		if (nodeId && mapId) {
			// Fetch if node changed or refresh triggered
			if (nodeId !== lastLoadedNodeId || refreshTrigger !== lastRefreshTrigger) {
				lastLoadedNodeId = nodeId;
				lastRefreshTrigger = refreshTrigger;
				loadSignatures(mapId, nodeId);
				loadConnections(mapId, nodeId);
			}
		} else if (!nodeId) {
			lastLoadedNodeId = null;
			signatures = [];
			connections = [];
			expandedSigId = null;
			creatingConnection = null;
			connectionStep = null;
			pendingConnectionWormhole = null;
		}
	});

	async function loadSignatures(mapId: string, nodeId: string) {
		loading = true;
		error = null;

		const { data, error: apiError } = await apiClient.GET(
			'/maps/{map_id}/nodes/{node_id}/signatures',
			{
				params: { path: { map_id: mapId, node_id: nodeId } }
			}
		);

		if (apiError) {
			error = 'Failed to load signatures';
			loading = false;
			return;
		}

		if (data) {
			signatures = data.signatures;
		}

		loading = false;
	}

	async function loadConnections(mapId: string, nodeId: string) {
		const { data } = await apiClient.GET('/maps/{map_id}/nodes/{node_id}/connections', {
			params: { path: { map_id: mapId, node_id: nodeId } }
		});

		if (data) {
			connections = data.connections;
		}
	}

	function formatSubgroup(subgroup: string | null | undefined): string {
		if (!subgroup) return '-';
		return subgroup.charAt(0).toUpperCase() + subgroup.slice(1);
	}

	function getGroupClass(groupType: string): string {
		return groupType === 'anomaly' ? 'text-green-400' : 'text-red-400';
	}

	function getSubgroupClass(subgroup: string | null | undefined): string {
		if (!subgroup) return 'text-surface-400';
		switch (subgroup) {
			case 'wormhole':
				return 'text-purple-400';
			case 'combat':
				return 'text-red-400';
			case 'data':
				return 'text-blue-400';
			case 'relic':
				return 'text-yellow-400';
			case 'gas':
				return 'text-green-400';
			case 'ore':
				return 'text-orange-400';
			default:
				return 'text-surface-300';
		}
	}

	function mapSubgroup(raw: string): string | null {
		const mapping: Record<string, string> = {
			'Combat Site': 'combat',
			'Data Site': 'data',
			'Gas Site': 'gas',
			'Ore Site': 'ore',
			'Relic Site': 'relic',
			Wormhole: 'wormhole'
		};
		return mapping[raw] || null;
	}

	function parseEveSignatures(text: string): BulkSignatureItem[] {
		const lines = text.trim().split(/\r?\n/);
		const results: BulkSignatureItem[] = [];

		for (const line of lines) {
			const parts = line.split('\t');
			if (parts.length < 2) continue;

			const code = parts[0]?.trim().toUpperCase();
			if (!code || !/^[A-Z]{3}-\d{3}$/.test(code)) continue;

			const groupRaw = parts[1]?.trim() || '';
			const subgroupRaw = parts[2]?.trim() || '';
			const typeRaw = parts[3]?.trim() || '';

			results.push({
				code,
				group_type: groupRaw === 'Cosmic Anomaly' ? 'anomaly' : 'signature',
				subgroup: mapSubgroup(subgroupRaw),
				type: typeRaw || null
			});
		}

		return results;
	}

	async function handlePaste(event: ClipboardEvent) {
		const state = $mapSelection;
		if (!state.selectedNode || !state.mapId || state.isReadOnly) return;

		const text = event.clipboardData?.getData('text/plain');
		if (!text) return;

		const signatures = parseEveSignatures(text);
		if (signatures.length === 0) return;

		event.preventDefault();

		await apiClient.POST('/maps/{map_id}/nodes/{node_id}/signatures/bulk', {
			params: {
				path: { map_id: state.mapId, node_id: state.selectedNode.id },
				query: { delete_missing: true }
			},
			body: { signatures }
		});
		// SSE event will trigger refresh automatically
	}

	function toggleExpanded(sigId: string) {
		if (expandedSigId === sigId) {
			expandedSigId = null;
			creatingConnection = null;
			connectionStep = null;
			pendingConnectionWormhole = null;
		} else {
			expandedSigId = sigId;
			creatingConnection = null;
			connectionStep = null;
			pendingConnectionWormhole = null;
		}
	}

	// Get the display name for the "other" system in a connection relative to current node
	function getConnectionDisplay(conn: NodeConnectionInfo): {
		label: string;
		isSource: boolean;
		wormholeCode: string;
	} {
		const currentNodeId = $mapSelection.selectedNode?.id;
		const isSource = conn.source_node_id === currentNodeId;
		const otherSystem = isSource ? conn.target_system_name : conn.source_system_name;
		// If current node is source, show the link's wormhole code; if target, show K162
		const wormholeCode = isSource ? conn.wormhole_code || 'K162' : 'K162';
		const arrow = isSource ? '→' : '←';
		return {
			label: `${arrow} ${otherSystem} (${wormholeCode})`,
			isSource,
			wormholeCode
		};
	}

	// Handle subgroup change
	async function handleSubgroupChange(sig: EnrichedSignatureInfo, newSubgroup: string) {
		const state = $mapSelection;
		if (!state.mapId) return;

		await apiClient.PATCH('/maps/{map_id}/signatures/{signature_id}', {
			params: { path: { map_id: state.mapId, signature_id: sig.id } },
			body: { subgroup: newSubgroup || null }
		});
		// SSE will trigger refresh
	}

	// Handle connection selection for a signature
	async function handleConnectionSelect(sig: EnrichedSignatureInfo, connectionId: string) {
		const state = $mapSelection;
		if (!state.mapId) return;

		await apiClient.PATCH('/maps/{map_id}/signatures/{signature_id}', {
			params: { path: { map_id: state.mapId, signature_id: sig.id } },
			body: { link_id: connectionId || null }
		});
		// SSE will trigger refresh
	}

	// Handle wormhole type selection - updates the link
	async function handleWormholeTypeSelect(
		sig: EnrichedSignatureInfo,
		wormhole: WormholeSearchResult
	) {
		const state = $mapSelection;
		if (!state.mapId || !state.selectedNode || !sig.link_id) return;

		await apiClient.PATCH('/maps/{map_id}/links/{link_id}/set-type', {
			params: { path: { map_id: state.mapId, link_id: sig.link_id } },
			body: { wormhole_id: wormhole.id, from_node_id: state.selectedNode.id }
		});
		// SSE will trigger refresh
	}

	// Start creating a new connection - now starts with wormhole type selection
	function startCreateConnection(sigId: string) {
		creatingConnection = sigId;
		connectionStep = 'type';
		pendingConnectionWormhole = null;
	}

	// Handle wormhole type selection in the connection flow
	function handleConnectionWormholeSelect(wormhole: WormholeSearchResult) {
		pendingConnectionWormhole = wormhole;
		connectionStep = 'system';
	}

	// Handle system selection for new connection
	async function handleCreateConnection(
		sig: EnrichedSignatureInfo,
		system: { id: number; name: string }
	) {
		const state = $mapSelection;
		if (!state.mapId || !state.selectedNode) return;

		// Calculate position offset from current node
		const posX = state.selectedNode.pos_x + 200;
		const posY = state.selectedNode.pos_y;

		await apiClient.POST('/maps/{map_id}/signatures/{signature_id}/connect', {
			params: { path: { map_id: state.mapId, signature_id: sig.id } },
			body: {
				system_id: system.id,
				pos_x: posX,
				pos_y: posY,
				wormhole_id: pendingConnectionWormhole?.id
			}
		});

		creatingConnection = null;
		connectionStep = null;
		pendingConnectionWormhole = null;
		// SSE will trigger refresh
	}

	// Handle creating connection to an unidentified system
	async function handleCreateConnectionUnidentified(sig: EnrichedSignatureInfo) {
		const state = $mapSelection;
		if (!state.mapId || !state.selectedNode) return;

		const unidentifiedSystem = getUnidentifiedSystemForClass(pendingConnectionWormhole?.target?.id);
		if (!unidentifiedSystem) {
			// Fallback to unknown if target class not found
			const fallback = unidentifiedSystems.find((s) => s.system_class === 0);
			if (!fallback) return;
			await doCreateConnection(sig, fallback.id);
		} else {
			await doCreateConnection(sig, unidentifiedSystem.id);
		}
	}

	async function doCreateConnection(sig: EnrichedSignatureInfo, systemId: number) {
		const state = $mapSelection;
		if (!state.mapId || !state.selectedNode) return;

		const posX = state.selectedNode.pos_x + 200;
		const posY = state.selectedNode.pos_y;

		await apiClient.POST('/maps/{map_id}/signatures/{signature_id}/connect', {
			params: { path: { map_id: state.mapId, signature_id: sig.id } },
			body: {
				system_id: systemId,
				pos_x: posX,
				pos_y: posY,
				wormhole_id: pendingConnectionWormhole?.id
			}
		});

		creatingConnection = null;
		connectionStep = null;
		pendingConnectionWormhole = null;
	}

	function cancelCreateConnection() {
		creatingConnection = null;
		connectionStep = null;
		pendingConnectionWormhole = null;
	}

	// Handle setting wormhole type directly on signature (when no link)
	async function handleSetSignatureWormholeType(
		sig: EnrichedSignatureInfo,
		wormhole: WormholeSearchResult
	) {
		const state = $mapSelection;
		if (!state.mapId) return;

		await apiClient.PATCH('/maps/{map_id}/signatures/{signature_id}', {
			params: { path: { map_id: state.mapId, signature_id: sig.id } },
			body: { wormhole_id: wormhole.id }
		});
		// SSE will trigger refresh
	}

	// Get wormhole display for a signature based on its link
	function getSignatureWormholeDisplay(sig: EnrichedSignatureInfo): string | null {
		if (!sig.link_id) return null;

		const conn = connections.find((c) => c.id === sig.link_id);
		if (!conn) return sig.wormhole_code || null;

		const currentNodeId = $mapSelection.selectedNode?.id;
		const isSource = conn.source_node_id === currentNodeId;

		// If we're on the source side, show the connection's wormhole type
		// If we're on the target side, it's always K162
		return isSource ? conn.wormhole_code || 'K162' : 'K162';
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<div
	class="flex h-full min-h-80 flex-col rounded-xl border-0 bg-black/75 backdrop-blur-2xl focus:ring-2 focus:ring-primary-800 focus:outline-none"
	tabindex="0"
	onpaste={handlePaste}
>
	<!-- Header -->
	<div
		class="flex w-full flex-row items-center justify-between border-b-2 border-primary-950/50 px-3 py-2"
	>
		<h3 class="text-sm font-semibold text-white">Signatures</h3>
		{#if $mapSelection.selectedNode}
			<p class="text-sm font-semibold text-surface-400">{$mapSelection.selectedNode.system_name}</p>
		{/if}
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-auto p-2">
		{#if !$mapSelection.selectedNode}
			<div class="flex h-full items-center justify-center">
				<p class="text-sm text-surface-400">Select a node to view signatures</p>
			</div>
		{:else if loading}
			<div class="flex h-full items-center justify-center">
				<Progress value={null} class="w-fit items-center">
					<Progress.Circle>
						<Progress.CircleTrack />
						<Progress.CircleRange />
					</Progress.Circle>
				</Progress>
			</div>
		{:else if error}
			<div class="flex h-full items-center justify-center">
				<p class="text-sm text-error-500">{error}</p>
			</div>
		{:else if signatures.length === 0}
			<div class="flex h-full items-center justify-center">
				<p class="text-sm text-surface-400">No signatures associated</p>
			</div>
		{:else}
			<div class="space-y-1">
				{#each signatures as sig (sig.id)}
					{@const isWormhole = sig.subgroup === 'wormhole'}
					{@const isExpanded = expandedSigId === sig.id}
					{@const isCreating = creatingConnection === sig.id}
					{@const whDisplay = getSignatureWormholeDisplay(sig)}
					{@const canExpand = !$mapSelection.isReadOnly}

					<div class="rounded border border-none bg-primary-950/30">
						<!-- Main row -->
						<button
							type="button"
							class="flex w-full items-center gap-2 px-2 py-1.5 text-left text-xs {canExpand
								? 'cursor-pointer hover:bg-black'
								: ''}"
							onclick={() => canExpand && toggleExpanded(sig.id)}
							disabled={!canExpand}
						>
							<span class="w-16 font-mono font-bold text-surface-200">{sig.code}</span>
							<span class="w-16 {getGroupClass(sig.group_type)}">
								{sig.group_type === 'anomaly' ? 'Anomaly' : 'Signature'}
							</span>
							<span class="w-16 {getSubgroupClass(sig.subgroup)}">
								{formatSubgroup(sig.subgroup)}
							</span>
							<span class="flex-1 truncate text-surface-300" title={sig.type || ''}>
								{#if isWormhole && whDisplay}
									<span class="w-12 font-mono text-purple-300">{whDisplay}</span>
								{:else}
									{sig.type || '-'}
								{/if}
							</span>

							{#if canExpand}
								<span class="text-[8px] text-surface-600">{isExpanded ? '▼' : '▶'}</span>
							{/if}
						</button>

						<!-- Expanded controls -->
						{#if isExpanded && !$mapSelection.isReadOnly}
							<div class="space-y-2 border-t border-surface-700 bg-surface-950 px-3 py-2">
								<!-- Subgroup selector -->
								<div class="flex items-center gap-2">
									<span class="w-20 text-xs text-surface-400">Subgroup:</span>
									<select
										class="flex-1 rounded border border-surface-600 bg-surface-800 px-2 py-1 text-xs text-white"
										value={sig.subgroup || ''}
										onchange={(e) => handleSubgroupChange(sig, e.currentTarget.value)}
									>
										{#each SUBGROUPS as subgroup (subgroup.value)}
											<option value={subgroup.value}>{subgroup.label}</option>
										{/each}
									</select>
								</div>

								<!-- Wormhole-specific controls -->
								{#if isWormhole}
									<!-- Wormhole type selector for unconnected signatures -->
									{#if !sig.link_id}
										<div class="flex items-center gap-2">
											<span class="w-20 text-xs text-surface-400">Type:</span>
											<div class="flex-1">
												<WormholeSearch
													source_class={getSystemClassId($mapSelection.selectedNode?.class_name)}
													placeholder={sig.wormhole_code || 'Set type...'}
													onselect={(wh) => handleSetSignatureWormholeType(sig, wh)}
												/>
											</div>
										</div>
									{/if}

									<!-- Connection selector -->
									<div class="flex items-center gap-2">
										<span class="w-20 text-xs text-surface-400">Connection:</span>
										{#if connections.length > 0}
											<select
												class="flex-1 rounded border border-surface-600 bg-surface-800 px-2 py-1 text-xs text-white"
												value={sig.link_id || ''}
												onchange={(e) => handleConnectionSelect(sig, e.currentTarget.value)}
											>
												<option value="">-- None --</option>
												{#each connections as conn (conn.id)}
													{@const display = getConnectionDisplay(conn)}
													<option value={conn.id}>{display.label}</option>
												{/each}
											</select>
										{:else}
											<span class="text-xs text-surface-500">No connections available</span>
										{/if}
									</div>

									<!-- Wormhole type selector (only if connected and on source side) -->
									{#if sig.link_id}
										{@const conn = connections.find((c) => c.id === sig.link_id)}
										{@const isSource = conn?.source_node_id === $mapSelection.selectedNode?.id}
										{#if isSource}
											<div class="flex items-center gap-2">
												<span class="w-20 text-xs text-surface-400">Type:</span>
												<div class="flex-1">
													<WormholeSearch
														source_class={getSystemClassId($mapSelection.selectedNode?.class_name)}
														placeholder={conn?.wormhole_code || 'Search type...'}
														onselect={(wh) => handleWormholeTypeSelect(sig, wh)}
													/>
												</div>
											</div>
										{:else}
											<div class="flex items-center gap-2">
												<span class="w-20 text-xs text-surface-400">Type:</span>
												<span class="text-xs text-surface-500">K162 (set from other side)</span>
											</div>
										{/if}
									{/if}

									<!-- Create new connection -->
									{#if !isCreating}
										<button
											type="button"
											class="flex items-center gap-1 text-xs text-primary-400 hover:text-primary-300"
											onclick={() => startCreateConnection(sig.id)}
										>
											<span>+</span>
											<span>Create New Connection</span>
										</button>
									{:else if connectionStep === 'type'}
										<div class="space-y-2">
											<div class="flex items-center gap-2">
												<span class="w-20 text-xs text-surface-400">Type:</span>
												<div class="flex-1">
													<WormholeSearch
														source_class={getSystemClassId($mapSelection.selectedNode?.class_name)}
														placeholder="Select wormhole type..."
														onselect={handleConnectionWormholeSelect}
													/>
												</div>
											</div>
											<button
												type="button"
												class="text-xs text-surface-500 hover:text-surface-400"
												onclick={cancelCreateConnection}
											>
												Cancel
											</button>
										</div>
									{:else if connectionStep === 'system'}
										<div class="space-y-2">
											<div class="flex items-center gap-2">
												<span class="w-20 text-xs text-surface-400">Type:</span>
												<span class="font-mono text-xs text-purple-300"
													>{pendingConnectionWormhole?.code}</span
												>
											</div>
											<div class="flex items-center gap-2">
												<span class="w-20 text-xs text-surface-400">Destination:</span>
												<div class="flex-1">
													<SystemSearch
														placeholder="Search system..."
														autofocus={true}
														onselect={(system) => handleCreateConnection(sig, system)}
														oncancel={cancelCreateConnection}
													/>
												</div>
											</div>
											<button
												type="button"
												class="flex items-center gap-1 text-xs text-primary-400 hover:text-primary-300"
												onclick={() => handleCreateConnectionUnidentified(sig)}
											>
												<span>+</span>
												<span>Create as Unidentified System</span>
											</button>
											<button
												type="button"
												class="text-xs text-surface-500 hover:text-surface-400"
												onclick={cancelCreateConnection}
											>
												Cancel
											</button>
										</div>
									{/if}
								{/if}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
