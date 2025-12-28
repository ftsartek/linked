<script lang="ts">
	import { goto } from "$app/navigation";
	import { apiClient } from "$lib/client/client";
	import { user } from "$lib/stores/user";
	import { resolve } from "$app/paths";

	async function logout() {
		await apiClient.POST("/auth/logout");
		user.set(null);
		await goto(resolve("/"));
	}
</script>

{#if $user !== undefined && $user !== null}
	<nav class="flex items-center justify-between p-4 bg-surface-800">
		<a href="{resolve('/maps')}" class="text-xl font-bold">Linked</a>
		<div class="flex items-center gap-4">
			<span class="text-surface-300">
				{$user.characters[0]?.name ?? "Unknown"}
			</span>
			<button onclick={logout} class="btn preset-filled-primary-500">
				Logout
			</button>
		</div>
	</nav>
{/if}
