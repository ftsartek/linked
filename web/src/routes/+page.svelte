<script lang="ts">
	import { goto, replaceState } from '$app/navigation';
	import { page } from '$app/stores';

	import { user } from '$lib/stores/user';
	import { toaster } from '$lib/stores/toaster';
	import { resolve } from '$app/paths';

	$effect(() => {
		if ($user) {
			goto(resolve('/maps'));
		}
	});

	$effect(() => {
		const error = $page.url.searchParams.get('error');
		if (error === 'acl_denied') {
			toaster.create({
				title: 'Access Denied',
				description: 'This instance is private. Contact an administrator for access.',
				type: 'error',
				duration: 10000
			});
			// Clear the error from URL without triggering navigation
			replaceState(resolve('/'), {});
		}
	});
</script>

<main class="flex min-h-screen flex-col items-center justify-center gap-8">
	<h1 class="text-4xl font-bold">Linked</h1>
	<p class="text-surface-400">EVE Online Wormhole Mapping</p>
</main>
