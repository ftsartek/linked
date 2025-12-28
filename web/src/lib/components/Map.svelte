<script lang="ts">
	import { SvelteFlow, Background, Controls, type Node, type Edge } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import { Progress } from '@skeletonlabs/skeleton-svelte';
	import { apiClient } from '$lib/client/client';
	import type { components } from '$lib/client/schema';

	type NodeInfo = components['schemas']['EnrichedNodeInfo'];
	type LinkInfo = components['schemas']['EnrichedLinkInfo'];

	interface Props {
		map_id: string;
	}

	let { map_id }: Props = $props();

	let nodes = $state.raw<Node[]>([]);
	let edges = $state.raw<Edge[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	function transformNodes(apiNodes: NodeInfo[]): Node[] {
		return apiNodes.map((node) => ({
			id: node.id,
			position: { x: node.pos_x, y: node.pos_y },
			data: {
				label: node.system_name ?? `System ${node.system_id}`,
				system_id: node.system_id
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

	$effect(() => {
		loadMap();
	});
</script>

<div class="h-full min-h-100 w-full">
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
		<SvelteFlow bind:nodes bind:edges fitView colorMode="dark" snapGrid={[1, 1]}>
			<Background />
			<Controls />
		</SvelteFlow>
	{/if}
</div>
