<script lang="ts">
	import { goto } from '$app/navigation';
	import { apiClient } from '$lib/client/client';
	import { user } from '$lib/stores/user';
	import { resolve } from '$app/paths';
	import { Settings, LogOut } from 'lucide-svelte';
	import { getCharacterPortrait } from '$lib/helpers/images';

	// Get primary character, falling back to first character if no primary set
	const primaryCharacter = $derived(
		$user?.characters.find((c) => c.id === $user?.primary_character_id) ?? $user?.characters[0]
	);

	async function logout() {
		await apiClient.POST('/auth/logout');
		user.set(null);
		await goto(resolve('/'));
	}
</script>

<nav class="flex items-center justify-between bg-black/75 p-4 backdrop-blur-2xl">
	<a href={resolve('/maps')} class="text-xl font-bold">Linked</a>
	{#if $user !== undefined && $user !== null}
		<div class="flex items-center gap-3">
			{#if primaryCharacter}
				<img
					src={getCharacterPortrait(primaryCharacter.id, 32)}
					alt={primaryCharacter.name}
					class="mr-1 h-8 w-8 rounded-full"
				/>
			{/if}
			<a
				href={resolve('/account')}
				class="preset-ghost-primary-500 btn-icon btn btn-sm"
				title="Account Settings"
			>
				<Settings size={16} />
			</a>
			<button onclick={logout} class="btn-icon btn preset-tonal-warning btn-sm" title="Logout">
				<LogOut size={16} />
			</button>
		</div>
	{/if}
</nav>
