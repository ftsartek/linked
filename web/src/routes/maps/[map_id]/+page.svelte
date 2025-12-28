<script lang="ts">
	import { page } from '$app/state';
	import Map from '$lib/components/Map.svelte';

	let mapId = $derived(page.params.map_id!);
</script>

<div class="w-[70vw] h-[70vh]">
	{#key mapId}
		<Map map_id={mapId} />
	{/key}
</div>
