<script lang="ts">
	import { goto } from '$app/navigation';
	import { getApiUrl } from '$lib/client/client';
	import { user } from '$lib/stores/user';
	import { resolve } from '$app/paths';

	$effect(() => {
		if ($user) {
			goto(resolve('/maps'));
		}
	});
</script>

<main class="flex min-h-screen flex-col items-center justify-center gap-8">
	<h1 class="text-4xl font-bold">Linked</h1>
	<p class="text-surface-400">EVE Online Wormhole Mapping</p>
	<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- External API URL, not a SvelteKit route -->
	<a href={getApiUrl('/auth/login')}>
		<img src="/eve-sso-login.png" alt="Login with EVE Online" />
	</a>
</main>
