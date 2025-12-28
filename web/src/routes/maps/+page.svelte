<script lang="ts">
	import { goto } from "$app/navigation";
	import { user } from "$lib/stores/user";
	import { resolve } from "$app/paths";

	$effect(() => {
		if ($user === null) {
			goto(resolve("/"));
		}
	});
</script>

<main class="p-8">
	<h1 class="text-3xl font-bold mb-4">Maps</h1>
	<p class="text-surface-400">Maps will go here.</p>
</main>
