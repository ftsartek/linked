<script lang="ts">
	import {
		SvelteFlow,
		SvelteFlowProvider,
		Background,
		Controls,
		useSvelteFlow,
		type Node,
		type Edge,
		type OnConnect
	} from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import { Progress } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import type { components } from '$lib/client/schema';
	import SystemNode from './Node.svelte';

	type NodeInfo = components['schemas']['EnrichedNodeInfoResponse'];
	type LinkInfo = components['schemas']['EnrichedLinkInfo'];
	type SystemSearchResult = components['schemas']['SystemSearchResult'];

	const nodeTypes = {
		default: SystemNode
	};

	interface Props {
		map_id: string;
	}

	let { map_id }: Props = $props();

	let nodes = $state.raw<Node[]>([]);
	let edges = $state.raw<Edge[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Context menu state
	let contextMenu = $state<{
		x: number;
		y: number;
		flowX: number;
		flowY: number;
		mode: 'menu' | 'search';
	} | null>(null);

	// Search state
	let searchQuery = $state('');
	let searchResults = $state<SystemSearchResult[]>([]);
	let searchLoading = $state(false);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let searchInputRef: HTMLInputElement | null = $state(null);

	// SvelteFlow utilities - will be set after flow mounts
	let screenToFlowPosition: ReturnType<typeof useSvelteFlow>['screenToFlowPosition'] | null =
		$state(null);

	function handleFlowInit() {
		const flow = useSvelteFlow();
		screenToFlowPosition = flow.screenToFlowPosition;
	}

	function transformNodes(apiNodes: NodeInfo[]): Node[] {
		return apiNodes.map((node) => ({
			id: node.id,
			position: { x: node.pos_x, y: node.pos_y },
			data: {
				system_name: node.system_name ?? `System ${node.system_id}`,
				system_id: node.system_id,
				wh_class: node.wh_class,
				security_class: node.security_class,
				wh_effect_name: node.wh_effect_name,
				wh_effect_buffs: node.wh_effect_buffs,
				wh_effect_debuffs: node.wh_effect_debuffs
			}
		}));
	}

	function transformEdges(apiLinks: LinkInfo[]): Edge[] {
		return apiLinks.map((link) => ({
			id: link.id,
			source: link.source_node_id,
			target: link.target_node_id,
			data: {
				wormhole_id: link.wormhole_code,
				mass_remaining: link.mass_usage,
				status: link.lifetime_status,
				static: link.wormhole_is_static
			}
		}));
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
			nodes = transformNodes(data.nodes);
			edges = transformEdges(data.links);
		}

		loading = false;
	}

	function handlePaneContextMenu({ event }: { event: MouseEvent }) {
		event.preventDefault();
		if (!screenToFlowPosition) return;
		const flowPosition = screenToFlowPosition({ x: event.clientX, y: event.clientY });
		searchQuery = '';
		searchResults = [];
		contextMenu = {
			x: event.clientX,
			y: event.clientY,
			flowX: flowPosition.x,
			flowY: flowPosition.y,
			mode: 'menu'
		};
	}

	function handlePaneClick() {
		contextMenu = null;
	}

	function handleAddSystem() {
		if (contextMenu) {
			contextMenu = { ...contextMenu, mode: 'search' };
			// Focus the input after the DOM updates
			setTimeout(() => searchInputRef?.focus(), 0);
		}
	}

	async function searchSystems(query: string) {
		if (query.length < 2) {
			searchResults = [];
			return;
		}

		searchLoading = true;
		const { data } = await apiClient.GET('/universe/systems', {
			params: { query: { q: query } }
		});
		searchResults = data?.systems ?? [];
		searchLoading = false;
	}

	function handleSearchInput(event: Event) {
		const value = (event.target as HTMLInputElement).value;
		searchQuery = value;

		if (debounceTimer) {
			clearTimeout(debounceTimer);
		}
		debounceTimer = setTimeout(() => {
			searchSystems(value);
		}, 300);
	}

	function formatSystemLabel(system: SystemSearchResult): string {
		if (system.wh_class !== null && system.wh_class !== undefined) {
			return `${system.name} [C${system.wh_class}]`;
		}
		return system.name;
	}

	async function handleSystemSelect(system: SystemSearchResult) {
		if (!contextMenu) return;

		const { data, error: apiError } = await apiClient.POST('/maps/{map_id}/nodes', {
			params: { path: { map_id } },
			body: {
				system_id: system.id,
				pos_x: contextMenu.flowX,
				pos_y: contextMenu.flowY
			}
		});

		if (apiError) {
			console.error('Failed to create node:', apiError);
			return;
		}

		if (data) {
			const newNode: Node = {
				id: data.id,
				position: { x: data.pos_x, y: data.pos_y },
				data: {
					system_name: data.system_name ?? `System ${data.system_id}`,
					system_id: data.system_id,
					wh_class: data.wh_class,
					security_class: data.security_class,
					wh_effect_name: data.wh_effect_name,
					wh_effect_buffs: data.wh_effect_buffs,
					wh_effect_debuffs: data.wh_effect_debuffs
				}
			};
			nodes = [...nodes, newNode];
		}

		contextMenu = null;
	}

	const handleConnect: OnConnect = async (connection) => {
		const { data, error: apiError } = await apiClient.POST('/maps/{map_id}/links', {
			params: { path: { map_id } },
			body: {
				source_node_id: connection.source,
				target_node_id: connection.target
			}
		});

		if (apiError) {
			console.error('Failed to create link:', apiError);
			return;
		}

		if (data) {
			const newEdge: Edge = {
				id: data.id,
				source: data.source_node_id,
				target: data.target_node_id,
				data: {
					wormhole_id: data.wormhole_code,
					mass_remaining: data.mass_usage,
					status: data.lifetime_status,
					static: data.wormhole_is_static
				}
			};
			edges = [...edges, newEdge];
		}
	};

	$effect(() => {
		loadMap();
	});
</script>

<SvelteFlowProvider>
	<div class="relative h-full min-h-100 w-full">
		{#if loading}
			<div class="flex h-full min-h-100 items-center justify-center">
				<Progress value={null} class="w-fit items-center">
					<Progress.Circle>
						<Progress.CircleTrack />
						<Progress.CircleRange />
					</Progress.Circle>
				</Progress>
			</div>
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
				fitView
				colorMode="dark"
				snapGrid={[20, 20]}
				proOptions={{ hideAttribution: true }}
				oninit={handleFlowInit}
				onpanecontextmenu={handlePaneContextMenu}
				onpaneclick={handlePaneClick}
				onconnect={handleConnect}
			>
				<Background />
				<Controls />
			</SvelteFlow>

			{#if contextMenu}
				<div
					class="fixed z-50 min-w-48 rounded-lg border border-surface-600 bg-surface-800 shadow-xl"
					style="left: {contextMenu.x}px; top: {contextMenu.y}px;"
				>
					{#if contextMenu.mode === 'menu'}
						<div class="py-1">
							<button
								class="w-full px-4 py-2 text-left text-sm text-white hover:bg-surface-700"
								onclick={handleAddSystem}
							>
								Add System
							</button>
						</div>
					{:else}
						<div class="p-2">
							<input
								bind:this={searchInputRef}
								type="text"
								value={searchQuery}
								oninput={handleSearchInput}
								placeholder="Search systems..."
								class="w-full rounded border border-surface-600 bg-surface-700 px-3 py-2 text-sm text-white placeholder-surface-400 focus:border-primary-500 focus:outline-none"
							/>
						</div>
						<div class="max-h-60 overflow-auto">
							{#if searchLoading}
								<div class="px-4 py-2 text-sm text-surface-400">Searching...</div>
							{:else if searchResults.length === 0 && searchQuery.length >= 2}
								<div class="px-4 py-2 text-sm text-surface-400">No systems found</div>
							{:else if searchResults.length === 0}
								<div class="px-4 py-2 text-sm text-surface-400">Type to search</div>
							{:else}
								{#each searchResults as system (system.id)}
									<button
										class="w-full px-4 py-2 text-left text-sm text-white hover:bg-surface-700"
										onclick={() => handleSystemSelect(system)}
									>
										{formatSystemLabel(system)}
									</button>
								{/each}
							{/if}
						</div>
					{/if}
				</div>
			{/if}
		{/if}
	</div>
</SvelteFlowProvider>
