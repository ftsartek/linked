<script lang="ts">
	import { onMount } from 'svelte';
	import './layout.css';
	import favicon from '$lib/assets/favicon.png';
	import Navbar from '$lib/components/common/Navbar.svelte';
	import { apiClient } from '$lib/client/client';
	import { user } from '$lib/stores/user';
	import { toaster } from '$lib/stores/toaster';
	import { Toast } from '@skeletonlabs/skeleton-svelte';

	let { children } = $props();

	onMount(async () => {
		const { data } = await apiClient.GET('/auth/me');
		user.set(data ?? null);
	});
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>
<main class="min-h-screen bg-[url('/eve.jpg')] bg-cover bg-fixed bg-center">
	<Toast.Group {toaster}>
		{#snippet children(toast)}
			<Toast {toast}>
				<Toast.Message>
					<Toast.Title>{toast.title}</Toast.Title>
					<Toast.Description>{toast.description}</Toast.Description>
				</Toast.Message>
				<Toast.CloseTrigger />
			</Toast>
		{/snippet}
	</Toast.Group>
	<Navbar />
	{@render children?.()}
</main>
