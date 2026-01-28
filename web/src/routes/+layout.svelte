<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import './layout.css';
	import favicon from '$lib/assets/favicon.png';
	import Navbar from '$lib/components/common/Navbar.svelte';
	import Footer from '$lib/components/common/Footer.svelte';
	import { apiClient } from '$lib/client/client';
	import { user } from '$lib/stores/user';
	import { serverStatus } from '$lib/stores/serverStatus';
	import { toaster } from '$lib/stores/toaster';
	import { Toast } from '@skeletonlabs/skeleton-svelte';

	let { children } = $props();

	let statusInterval: ReturnType<typeof setInterval> | null = null;

	async function fetchServerStatus() {
		const { data } = await apiClient.GET('/status/eve');
		if (data) {
			serverStatus.set(data);
		}
	}

	onMount(async () => {
		const { data } = await apiClient.GET('/auth/me');
		user.set(data ?? null);

		// Fetch server status immediately and then poll every 60 seconds
		fetchServerStatus();
		statusInterval = setInterval(fetchServerStatus, 60000);
	});

	onDestroy(() => {
		if (statusInterval) {
			clearInterval(statusInterval);
		}
	});
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>
<main class="flex min-h-screen flex-col bg-[url('/eve.jpg')] bg-cover bg-fixed bg-center">
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
	<div class="flex flex-1 flex-col">
		{@render children?.()}
	</div>
	<Footer />
</main>
