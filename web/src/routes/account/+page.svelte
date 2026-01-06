<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { user } from '$lib/stores/user';
	import CharactersCard from '$lib/components/account/CharactersCard.svelte';
	import PublicMapSubscriptionsCard from '$lib/components/account/PublicMapSubscriptionsCard.svelte';

	$effect(() => {
		if ($user === null) {
			goto(resolve('/'));
		}
	});
</script>

<div class="mx-auto max-w-6xl p-6">
	<div class="grid grid-cols-5 items-stretch gap-6">
		<div class="col-span-3">
			<CharactersCard />
		</div>
		<div class="col-span-2">
			<PublicMapSubscriptionsCard />
		</div>
	</div>
</div>
