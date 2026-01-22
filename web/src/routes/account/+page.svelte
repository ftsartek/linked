<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { user } from '$lib/stores/user';
	import CharactersCard from '$lib/components/account/CharactersCard.svelte';
	import PublicMapSubscriptionsCard from '$lib/components/account/PublicMapSubscriptionsCard.svelte';
	import InstanceACLCard from '$lib/components/account/InstanceACLCard.svelte';
	import InstanceAdminsCard from '$lib/components/account/InstanceAdminsCard.svelte';
	import DefaultSubscriptionsCard from '$lib/components/account/DefaultSubscriptionsCard.svelte';

	$effect(() => {
		if ($user === null) {
			goto(resolve('/'));
		}
	});

	let isAdminOrOwner = $derived($user?.is_admin || $user?.is_owner);
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

	{#if isAdminOrOwner}
		<div class="mt-6 grid grid-cols-5 items-stretch gap-6">
			<div class="col-span-3">
				<InstanceACLCard />
			</div>
			<div class="col-span-2">
				<InstanceAdminsCard />
			</div>
		</div>
		<div class="mt-6 grid grid-cols-5 items-stretch gap-6">
			<div class="col-span-2">
				<DefaultSubscriptionsCard />
			</div>
		</div>
	{/if}
</div>
