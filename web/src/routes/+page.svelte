<script lang="ts">
	import { goto } from "$app/navigation";
	import { getApiUrl } from "$lib/client/client";
	import { user } from "$lib/stores/user";
	import { resolve } from "$app/paths";

	$effect(() => {
		if ($user) {
			goto(resolve("/maps"));
		}
	});
</script>

<main class="flex flex-col items-center justify-center min-h-screen gap-8">
	<h1 class="text-4xl font-bold">Linked</h1>
	<p class="text-surface-400">EVE Online Wormhole Mapping</p>
	<a href="{getApiUrl('/auth/login')}" class="btn preset-filled-primary-500 text-lg px-8 py-3">
		Login with EVE
	</a>
</main>
