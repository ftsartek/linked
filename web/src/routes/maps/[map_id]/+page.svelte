<script lang="ts">
	import { page } from '$app/state';
	import Map from '$lib/components/map/Map.svelte';

	let mapId = $derived(page.params.map_id!);
</script>

<div class="h-full w-full">
	{#key mapId}
		<Map map_id={mapId} />
	{/key}
</div>
