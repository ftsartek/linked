<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { setContext } from 'svelte';
	import {
		SvelteFlow,
		SvelteFlowProvider,
		Background,
		Controls,
		ControlButton,
		MiniMap,
		useSvelteFlow,
		type Node,
		type Edge,
		BackgroundVariant
	} from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import { Progress, useDialog } from '@skeletonlabs/skeleton-svelte';
	import { Lock, LockOpen, Settings, Share2, RefreshCw } from 'lucide-svelte';
	import { apiClient } from '$lib/client/client';
	import { user } from '$lib/stores/user';
	import { toaster } from '$lib/stores/toaster';
	import {
		setMapContext,
		selectNode,
		clearSelection,
		triggerSignatureRefresh,
		triggerNoteRefresh,
		type EnrichedNodeInfo
	} from '$lib/stores/mapSelection';
	import {
		transformNodes,
		transformEdges,
		getSystemClassId,
		type LinkInfo
	} from '$lib/helpers/mapHelpers';
	import type { MapInfo, Rankdir, LifetimeStatus } from '$lib/helpers/mapTypes';
	import { type EdgeType } from '$lib/helpers/mapTypes';
	import type { ContextMenuState } from '$lib/helpers/mapContextMenu';

	// Extracted modules
	import { createMapSSE } from '$lib/helpers/mapSSE';
	import {
		removeNode,
		toggleNodeLock,
		updateNodePosition,
		updateNodeSystem,
		createNode,
		removeEdge,
		updateEdgeMassStatus,
		updateEdgeLifetimeStatus,
		reverseEdge,
		createEdge,
		setEdgeWormholeType,
		createNodeWithConnection
	} from '$lib/helpers/mapContextActions';
	import type { components } from '$lib/client/schema';

	type WormholeSearchResult =
		components['schemas']['SearchWormholesWormholeSearchResultResponseBody'];
	import { loadViewport, setSelectedMap, createViewportPersister } from '$lib/helpers/mapViewport';

	// Components
	import SystemNode from './Node.svelte';
	import FloatingEdge from './FloatingEdge.svelte';
	import ConnectionLine from './ConnectionLine.svelte';
	import MapSettingsDialog from './MapSettingsDialog.svelte';
	import MapSharingDialog from './MapSharingDialog.svelte';
	import MapContextMenu from './MapContextMenu.svelte';

	const nodeTypes = {
		default: SystemNode
	};

	const edgeTypes = {
		default: FloatingEdge
	};

	interface Props {
		map_id: string;
	}

	let { map_id }: Props = $props();

	// Core map state
	let nodes = $state.raw<Node[]>([]);
	let edges = $state.raw<Edge[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// SSE connection state
	let lastEventId = $state<string | null>(null);

	// Map metadata state
	let mapInfo = $state<MapInfo | null>(null);
	let edgeType = $state<EdgeType>('default');
	// eslint-disable-next-line @typescript-eslint/no-unused-vars -- Used for future layout functionality
	let rankdir = $state<Rankdir>('LR');
	const isOwner = $derived($user?.id === mapInfo?.owner_id);
	const isReadOnly = $derived(mapInfo?.edit_access === false);

	// Lock state for interactivity toggle (read-only maps are always locked)
	let locked = $state(false);
	const isLocked = $derived(isReadOnly || locked);

	// Provide edge type to child components via context
	setContext('edgeType', () => edgeType);

	// Dialog instances and open state tracking
	const settingsDialog = useDialog({ id: 'settings-dialog' });
	const sharingDialog = useDialog({ id: 'sharing-dialog' });
	let settingsOpen = $state(false);
	let sharingOpen = $state(false);

	// Context menu state
	let contextMenu = $state<ContextMenuState | null>(null);

	// SvelteFlow utilities - will be set after flow mounts
	let screenToFlowPosition: ReturnType<typeof useSvelteFlow>['screenToFlowPosition'] | null =
		$state(null);
	let getViewport: ReturnType<typeof useSvelteFlow>['getViewport'] | null = $state(null);
	let setViewport: ReturnType<typeof useSvelteFlow>['setViewport'] | null = $state(null);

	// Initial viewport from session (loaded before map init)
	let initialViewport: { x: number; y: number; zoom: number } | null = $state(null);

	// Viewport persister instance
	let viewportPersister: ReturnType<typeof createViewportPersister> | null = null;

	// ============================================
	// SvelteFlow Handlers
	// ============================================

	async function handleFlowInit() {
		const flow = useSvelteFlow();
		screenToFlowPosition = flow.screenToFlowPosition;
		getViewport = flow.getViewport;
		setViewport = flow.setViewport;

		if (initialViewport && setViewport) {
			await setViewport(initialViewport);
		}
	}

	function handleMoveEnd() {
		if (!getViewport || !viewportPersister) return;
		const viewport = getViewport();
		viewportPersister.persist(viewport);
	}

	async function loadMap() {
		loading = true;
		error = null;

		const { data, error: apiError } = await apiClient.GET('/maps/{map_id}', {
			params: { path: { map_id } }
		});

		if (apiError) {
			error = 'detail' in apiError ? apiError.detail : 'Failed to load map';
			loading = false;
			return;
		}

		if (data) {
			mapInfo = data.map;
			edgeType = (data.map.edge_type as EdgeType) ?? 'default';
			rankdir = (data.map.rankdir as Rankdir) ?? 'LR';
			nodes = transformNodes(data.nodes, locked || data.map.edit_access === false);
			edges = transformEdges(data.links);
			lastEventId = data.last_event_id ?? null;

			// Update map selection context
			setMapContext(map_id, data.map.edit_access === false);
		}

		loading = false;
	}

	async function handleNodeDragStop({ targetNode }: { targetNode: Node | null }) {
		if (!targetNode) return;
		await updateNodePosition(map_id, targetNode.id, targetNode.position.x, targetNode.position.y);
	}

	async function handleSelectionDragStop(_event: MouseEvent, draggedNodes: Node[]) {
		for (const node of draggedNodes) {
			await updateNodePosition(map_id, node.id, node.position.x, node.position.y);
		}
	}

	async function handleBeforeDelete({
		nodes: deletedNodes,
		edges: deletedEdges
	}: {
		nodes: Node[];
		edges: Edge[];
	}): Promise<boolean> {
		// Filter out locked nodes - they cannot be deleted via hotkey
		const unlocked = deletedNodes.filter((node) => !node.data.locked);
		// If all selected nodes are locked, prevent deletion entirely
		if (deletedNodes.length > 0 && unlocked.length === 0) return false;

		// Attempt all deletions and only allow local removal if all succeed
		for (const node of unlocked) {
			const result = await removeNode(map_id, node.id);
			if (!result.success) return false;
		}
		for (const edge of deletedEdges) {
			const result = await removeEdge(map_id, edge.id);
			if (!result.success) return false;
		}
		return true;
	}

	const handleBeforeConnect = (connection: { source: string; target: string }) => {
		createEdge(map_id, connection.source, connection.target);
		return null;
	};

	// ============================================
	// Context Menu Event Handlers
	// ============================================

	function handlePaneContextMenu({ event }: { event: MouseEvent }) {
		event.preventDefault();
		if (!screenToFlowPosition || isLocked) return;
		const flowPosition = screenToFlowPosition({ x: event.clientX, y: event.clientY });
		contextMenu = {
			x: event.clientX,
			y: event.clientY,
			flowX: flowPosition.x,
			flowY: flowPosition.y,
			mode: 'pane-menu'
		};
	}

	function handleNodeContextMenu({ event, node }: { event: MouseEvent; node: Node }) {
		event.preventDefault();
		if (!screenToFlowPosition || isLocked) return;
		const flowPosition = screenToFlowPosition({ x: event.clientX, y: event.clientY });
		const nodeData = node.data as EnrichedNodeInfo | undefined;
		contextMenu = {
			x: event.clientX,
			y: event.clientY,
			flowX: flowPosition.x,
			flowY: flowPosition.y,
			mode: 'node-menu',
			nodeId: node.id,
			isNodeLocked: nodeData?.locked ?? false
		};
	}

	function handleEdgeContextMenu({ event, edge }: { event: MouseEvent; edge: Edge }) {
		event.preventDefault();
		if (!screenToFlowPosition || isLocked) return;
		const flowPosition = screenToFlowPosition({ x: event.clientX, y: event.clientY });
		contextMenu = {
			x: event.clientX,
			y: event.clientY,
			flowX: flowPosition.x,
			flowY: flowPosition.y,
			mode: 'edge-menu',
			edgeId: edge.id
		};
	}

	function handlePaneClick() {
		contextMenu = null;
	}

	function handleSelectionChange({ nodes: selectedNodes }: { nodes: Node[] }) {
		if (selectedNodes.length === 1 && selectedNodes[0]) {
			const node = selectedNodes[0];
			selectNode(node.data as EnrichedNodeInfo);
		} else {
			clearSelection();
		}
	}

	// ============================================
	// Context Menu Mode Handlers
	// ============================================

	function handleAddSystem() {
		if (contextMenu) {
			contextMenu = { ...contextMenu, mode: 'search' };
		}
	}

	function handleAddUnidentifiedSystem() {
		if (contextMenu) {
			contextMenu = { ...contextMenu, mode: 'unidentified' };
		}
	}

	function handleReplaceSystem() {
		if (contextMenu) {
			contextMenu = { ...contextMenu, mode: 'search' };
		}
	}

	function handleUpdateMassStatus() {
		if (contextMenu) {
			contextMenu = { ...contextMenu, mode: 'mass-status' };
		}
	}

	function handleUpdateLifetimeStatus() {
		if (contextMenu) {
			contextMenu = { ...contextMenu, mode: 'lifetime-status' };
		}
	}

	function handleSearchCancel() {
		contextMenu = null;
	}

	// ============================================
	// Context Menu Action Handlers
	// ============================================

	async function handleRemoveNode() {
		if (!contextMenu?.nodeId) return;
		await removeNode(map_id, contextMenu.nodeId);
		contextMenu = null;
	}

	async function handleToggleLock() {
		if (!contextMenu?.nodeId) return;
		await toggleNodeLock(map_id, contextMenu.nodeId, !contextMenu.isNodeLocked);
		contextMenu = null;
	}

	async function handleRemoveEdge() {
		if (!contextMenu?.edgeId) return;
		await removeEdge(map_id, contextMenu.edgeId);
		contextMenu = null;
	}

	async function handleMassStatusSelect(massUsage: number) {
		if (!contextMenu?.edgeId) return;
		await updateEdgeMassStatus(map_id, contextMenu.edgeId, massUsage);
		contextMenu = null;
	}

	async function handleLifetimeStatusSelect(lifetimeStatus: LifetimeStatus) {
		if (!contextMenu?.edgeId) return;
		await updateEdgeLifetimeStatus(map_id, contextMenu.edgeId, lifetimeStatus);
		contextMenu = null;
	}

	async function handleReverseConnection() {
		if (!contextMenu?.edgeId) return;
		await reverseEdge(map_id, contextMenu.edgeId);
		contextMenu = null;
	}

	function handleSetWormholeType() {
		if (!contextMenu?.edgeId) return;
		const edgeId = contextMenu.edgeId;
		const edge = edges.find((e) => e.id === edgeId);
		if (!edge) return;
		const sourceNode = nodes.find((n) => n.id === edge.source);
		const targetNode = nodes.find((n) => n.id === edge.target);
		const sourceNodeData = sourceNode?.data as EnrichedNodeInfo | undefined;
		const targetNodeData = targetNode?.data as EnrichedNodeInfo | undefined;
		contextMenu = {
			...contextMenu,
			mode: 'wormhole-type',
			sourceSystemClass: getSystemClassId(sourceNodeData?.class_name) ?? undefined,
			targetSystemClass: getSystemClassId(targetNodeData?.class_name) ?? undefined
		};
	}

	async function handleWormholeTypeSelect(wormhole: WormholeSearchResult) {
		if (!contextMenu?.edgeId) return;
		await setEdgeWormholeType(map_id, contextMenu.edgeId, wormhole.id);
		contextMenu = null;
	}

	// ============================================
	// Add Connection Flow Handlers
	// ============================================

	function handleAddConnection() {
		if (!contextMenu?.nodeId) return;
		const nodeId = contextMenu.nodeId;
		const node = nodes.find((n) => n.id === nodeId);
		const nodeData = node?.data as EnrichedNodeInfo | undefined;
		contextMenu = {
			...contextMenu,
			mode: 'add-connection-type',
			sourceNodeId: nodeId,
			sourceSystemClass: getSystemClassId(nodeData?.class_name) ?? undefined
		};
	}

	function handleConnectionWormholeSelect(wormhole: WormholeSearchResult) {
		if (!contextMenu) return;
		contextMenu = {
			...contextMenu,
			mode: 'add-connection-system',
			pendingWormholeId: wormhole.id,
			pendingWormholeTargetClass: wormhole.target?.id
		};
	}

	async function handleConnectionSystemSelect(system: {
		id: number;
		name: string;
		class_name?: string | null;
	}) {
		if (!contextMenu?.sourceNodeId) return;
		await createNodeWithConnection(
			map_id,
			contextMenu.sourceNodeId,
			system.id,
			contextMenu.flowX + 200,
			contextMenu.flowY,
			contextMenu.pendingWormholeId
		);
		contextMenu = null;
	}

	async function handleSystemSelect(system: {
		id: number;
		name: string;
		class_name?: string | null;
	}) {
		if (!contextMenu) return;

		if (contextMenu.nodeId) {
			await updateNodeSystem(map_id, contextMenu.nodeId, system.id);
		} else {
			await createNode(map_id, system.id, contextMenu.flowX, contextMenu.flowY);
		}

		contextMenu = null;
	}

	// ============================================
	// SSE Connection & Lifecycle
	// ============================================

	$effect(() => {
		let sseCleanup: (() => void) | null = null;

		const init = async () => {
			// Load saved viewport
			const savedViewport = await loadViewport(map_id);
			if (savedViewport) {
				initialViewport = savedViewport;
			}

			// Set selected map preference
			await setSelectedMap(map_id);

			// Create viewport persister
			viewportPersister = createViewportPersister(map_id);

			// Load map data
			await loadMap();
		};

		init().then(() => {
			// Create SSE connection with callbacks
			sseCleanup = createMapSSE({
				mapId: map_id,
				lastEventId,
				callbacks: {
					onConnected: () => {
						toaster.create({
							title: 'Connected',
							description: 'Real-time events connected',
							type: 'success'
						});
					},
					onError: () => {
						toaster.create({
							title: 'Connection Error',
							description: 'Lost connection to real-time events. Changes may not sync.',
							type: 'error'
						});
					},
					onNodeCreated: (newNode) => {
						if (nodes.some((n) => n.id === newNode.id)) return;
						nodes = [...nodes, newNode];
					},
					onNodeUpdated: (nodeData) => {
						nodes = nodes.map((n) =>
							n.id === nodeData.id
								? {
										...n,
										position: { x: nodeData.pos_x, y: nodeData.pos_y },
										data: nodeData,
										draggable: !isLocked && !nodeData.locked
									}
								: n
						);
					},
					onNodeDeleted: (nodeId) => {
						nodes = nodes.filter((n) => n.id !== nodeId);
					},
					onEdgeCreated: (newEdge) => {
						if (edges.some((e) => e.id === newEdge.id)) return;
						edges = [...edges, newEdge];
					},
					onEdgeUpdated: (linkData: LinkInfo) => {
						edges = edges.map((e) =>
							e.id === linkData.id
								? {
										...e,
										source: linkData.source_node_id,
										target: linkData.target_node_id,
										data: {
											wormhole_id: linkData.wormhole_code,
											mass_remaining: linkData.mass_usage,
											status: linkData.lifetime_status
										}
									}
								: e
						);
					},
					onEdgeDeleted: (edgeId) => {
						edges = edges.filter((e) => e.id !== edgeId);
					},
					onMapUpdated: (changes, newEdgeType, newRankdir) => {
						mapInfo = changes;
						edgeType = newEdgeType;
						rankdir = newRankdir;
					},
					onMapDeleted: () => {
						toaster.create({
							title: 'Map Deleted',
							description: 'This map has been deleted',
							type: 'warning'
						});
						goto(resolve('/maps'));
					},
					onAccessRevoked: () => {
						toaster.create({
							title: 'Access Revoked',
							description: 'Your access to this map has been revoked',
							type: 'warning'
						});
						goto(resolve('/maps'));
					},
					onSyncError: (message) => {
						toaster.create({
							title: 'Sync Error',
							description: message,
							type: 'error'
						});
						loadMap();
					},
					onSignatureChange: () => {
						triggerSignatureRefresh();
					},
					onNoteChange: () => {
						triggerNoteRefresh();
					}
				}
			});
		});

		return () => {
			if (sseCleanup) {
				sseCleanup();
			}
			if (viewportPersister) {
				viewportPersister.cleanup();
			}
		};
	});
</script>

<SvelteFlowProvider>
	<div class="relative h-full min-h-100 w-full overflow-hidden rounded-xl">
		{#if loading}
			<div class="absolute top-0 right-0 left-0 z-10">
				<Progress value={null} class="h-0.5 w-full rounded-none">
					<Progress.Track class="h-0.5 rounded-none bg-transparent">
						<Progress.Range class="h-0.5 rounded-none bg-primary-300-700" />
					</Progress.Track>
				</Progress>
			</div>
			<div class="h-full min-h-100 bg-black/75 backdrop-blur-2xl"></div>
		{:else if error}
			<div class="flex h-full min-h-100 items-center justify-center">
				<div class="rounded-lg bg-error-500/20 p-4 text-error-500">
					{error}
				</div>
			</div>
		{:else}
			<SvelteFlow
				bind:nodes
				bind:edges
				{nodeTypes}
				{edgeTypes}
				colorMode="dark"
				snapGrid={[20, 20]}
				elevateEdgesOnSelect={false}
				proOptions={{ hideAttribution: true }}
				elementsSelectable={true}
				nodesDraggable={!isLocked}
				nodesConnectable={!isLocked}
				deleteKey={isLocked ? null : ['Backspace', 'Delete']}
				connectionLineComponent={ConnectionLine}
				oninit={handleFlowInit}
				onmoveend={handleMoveEnd}
				onpanecontextmenu={handlePaneContextMenu}
				onpaneclick={handlePaneClick}
				onbeforeconnect={handleBeforeConnect}
				onnodedragstop={handleNodeDragStop}
				onselectiondragstop={handleSelectionDragStop}
				onnodecontextmenu={handleNodeContextMenu}
				onedgecontextmenu={handleEdgeContextMenu}
				onselectionchange={handleSelectionChange}
				onbeforedelete={handleBeforeDelete}
				style="background-color: rgba(0, 0, 0, 0.75);"
				class="backdrop-blur-2xl"
			>
				<Background
					bgColor="rgba(0, 0, 0, 0)"
					variant={BackgroundVariant.Cross}
					patternColor="#123"
				/>
				<Controls showLock={false}>
					<ControlButton
						class="lucide-btn"
						onclick={() => {
							locked = !locked;
							loadMap();
						}}
						disabled={isReadOnly}
						title={isReadOnly ? 'Map is read-only' : isLocked ? 'Unlock' : 'Lock'}
					>
						{#if isLocked}
							<Lock size={18} strokeWidth={3} />
						{:else}
							<LockOpen size={18} strokeWidth={3} />
						{/if}
					</ControlButton>
					<ControlButton
						class="lucide-btn"
						onclick={() => {
							settingsOpen = true;
							settingsDialog().setOpen(true);
						}}
						disabled={!isOwner}
						title={isOwner ? 'Map Settings' : 'Only the owner can edit settings'}
					>
						<Settings size={18} strokeWidth={3} />
					</ControlButton>
					<ControlButton
						class="lucide-btn"
						onclick={() => {
							sharingOpen = true;
							sharingDialog().setOpen(true);
						}}
						disabled={!isOwner}
						title={isOwner ? 'Share Map' : 'Only the owner can manage sharing'}
					>
						<Share2 size={18} strokeWidth={3} />
					</ControlButton>
					<ControlButton class="lucide-btn" onclick={loadMap} title="Reload Map">
						<RefreshCw size={18} strokeWidth={3} />
					</ControlButton>
				</Controls>
				<MiniMap
					class="minimap-responsive"
					style="border-radius: 6px; overflow: hidden;"
					position="bottom-right"
					pannable
					zoomable
					bgColor="rgba(0, 5, 15, 0.6)"
					maskColor="rgba(22, 30, 35, 0.7)"
					nodeColor="rgba(95, 102, 115, 0.8)"
					nodeBorderRadius={4}
				/>
			</SvelteFlow>

			{#if contextMenu}
				<MapContextMenu
					menu={contextMenu}
					{isOwner}
					onAddSystem={handleAddSystem}
					onAddUnidentifiedSystem={handleAddUnidentifiedSystem}
					onReplaceSystem={handleReplaceSystem}
					onRemoveNode={handleRemoveNode}
					onToggleLock={handleToggleLock}
					onUpdateMassStatus={handleUpdateMassStatus}
					onUpdateLifetimeStatus={handleUpdateLifetimeStatus}
					onReverseConnection={handleReverseConnection}
					onRemoveEdge={handleRemoveEdge}
					onSetWormholeType={handleSetWormholeType}
					onAddConnection={handleAddConnection}
					onMassStatusSelect={handleMassStatusSelect}
					onLifetimeStatusSelect={handleLifetimeStatusSelect}
					onWormholeTypeSelect={handleWormholeTypeSelect}
					onConnectionWormholeSelect={handleConnectionWormholeSelect}
					onConnectionSystemSelect={handleConnectionSystemSelect}
					onSystemSelect={handleSystemSelect}
					onCancel={handleSearchCancel}
				/>
			{/if}
		{/if}
	</div>
</SvelteFlowProvider>

<MapSettingsDialog
	dialog={settingsDialog}
	{map_id}
	{mapInfo}
	open={settingsOpen}
	onsaved={() => {
		settingsOpen = false;
		loadMap();
	}}
/>

<MapSharingDialog dialog={sharingDialog} {map_id} open={sharingOpen} />
