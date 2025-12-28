<script lang="ts">
	import { onMount } from "svelte";
	import "./layout.css";
	import favicon from "$lib/assets/favicon.svg";
	import Navbar from "$lib/components/Navbar.svelte";
	import { apiClient } from "$lib/client/client";
	import { user } from "$lib/stores/user";

	let { children } = $props();

	onMount(async () => {
		const { data } = await apiClient.GET("/auth/me");
		user.set(data ?? null);
	});
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>
<Navbar />
{@render children?.()}
