<script lang="ts">
	import { goto } from '$app/navigation';
	import { apiClient, getApiUrl } from '$lib/client/client';
	import { user } from '$lib/stores/user';
	import { resolve } from '$app/paths';
	import { Settings, LogOut } from 'lucide-svelte';
	import { getCharacterPortrait } from '$lib/helpers/images';
	import ServerStatus from './ServerStatus.svelte';

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

<nav class="relative flex min-h-16 items-center justify-between bg-black/75 p-4 backdrop-blur-2xl">
	<div class="flex items-center gap-4">
		<a href={resolve('/maps')} class="text-xl font-bold">Linked</a>
		{#if $user}
			<a href={resolve('/maps')} class="text-surface-400 hover:text-white">Maps</a>
		{/if}
		<a href={resolve('/reference/wormholes')} class="text-surface-400 hover:text-white">
			Wormholes
		</a>
		<a href={resolve('/reference/systems')} class="text-surface-400 hover:text-white"> Systems </a>
	</div>
	<div class="absolute left-1/2 -translate-x-1/2">
		<ServerStatus />
	</div>
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
	{:else if $user === null}
		<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- External API URL, not a SvelteKit route -->
		<a href={getApiUrl('/auth/login')}>
			<img src="/eve-login-dark-sm.png" alt="Login with EVE Online" class="h-8" />
		</a>
	{/if}
</nav>
